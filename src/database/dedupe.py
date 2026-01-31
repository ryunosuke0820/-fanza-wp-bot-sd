"""
SQLite重複防止ストア
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from contextlib import contextmanager

logger = logging.getLogger(__name__)

Status = Literal["drafted", "failed", "dry_run", "processing", "published"]

class DedupeStore:
    """投稿済み商品の管理"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self) -> None:
        """データベースとテーブルを初期化"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posted_items (
                    product_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    wp_post_id INTEGER,
                    created_at TEXT NOT NULL,
                    error_message TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()
            logger.debug(f"データベース初期化完了: {self.db_path}")
    
    @contextmanager
    def _connect(self):
        """データベース接続のコンテキストマネージャ"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def is_posted(self, product_id: str, processing_ttl_hours: int = 6, failed_retry_hours: int = 24) -> bool:
        """既に投稿済みかどうかを確認（処理中は一定時間だけ重複扱い）"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT status, created_at FROM posted_items WHERE product_id = ?",
                (product_id,),
            ).fetchone()
            if row is None:
                return False

            status = str(row["status"])
            if status in ("drafted", "published"):
                logger.debug(f"重複検出 (投稿済み): {product_id}")
                return True

            if status == "processing":
                try:
                    started_at = datetime.fromisoformat(str(row["created_at"]))
                except Exception:
                    # created_at が壊れている場合は保守的に「処理中」とみなす
                    return True
                if datetime.now() - started_at < timedelta(hours=processing_ttl_hours):
                    return True


            if status == "failed":
                try:
                    failed_at = datetime.fromisoformat(str(row["created_at"]))
                except Exception:
                    return True
                if datetime.now() - failed_at < timedelta(hours=failed_retry_hours):
                    return True

            return False

    def try_start(self, product_id: str, processing_ttl_hours: int = 6) -> bool:
        """
        処理開始を原子的に確保する。
        - drafted/published: 開始不可（重複防止）
        - processing: TTL内は開始不可（同時実行/重複防止）
        - failed/dry_run/TTL超過processing: 再試行可
        """
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status, created_at FROM posted_items WHERE product_id = ?",
                (product_id,),
            ).fetchone()

            if row is not None:
                status = str(row["status"])
                if status in ("drafted", "published"):
                    conn.rollback()
                    return False
                if status == "processing":
                    try:
                        started_at = datetime.fromisoformat(str(row["created_at"]))
                    except Exception:
                        conn.rollback()
                        return False
                    if datetime.now() - started_at < timedelta(hours=processing_ttl_hours):
                        conn.rollback()
                        return False

            conn.execute(
                """
                INSERT OR REPLACE INTO posted_items
                (product_id, status, wp_post_id, created_at, error_message)
                VALUES (?, 'processing', NULL, ?, NULL)
                """,
                (product_id, datetime.now().isoformat()),
            )
            conn.commit()
            logger.info(f"処理開始記録: {product_id}")
            return True
    
    def record_start(self, product_id: str) -> None:
        """処理開始を記録"""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO posted_items
                (product_id, status, wp_post_id, created_at, error_message)
                VALUES (?, 'processing', NULL, ?, NULL)
                """,
                (product_id, datetime.now().isoformat())
            )
            conn.commit()
            logger.info(f"処理開始記録: {product_id}")
    
    def record_success(self, product_id: str, wp_post_id: int | None = None, status: Status = "drafted") -> None:
        """投稿成功を記録"""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO posted_items
                (product_id, status, wp_post_id, created_at, error_message)
                VALUES (?, ?, ?, ?, NULL)
                """,
                (product_id, status, wp_post_id, datetime.now().isoformat())
            )
            conn.commit()
            logger.info(f"成功記録: {product_id}, status={status}, wp_post_id={wp_post_id}")

    def bulk_mark_posted(self, items: list[tuple[str, int | None]], status: Status = "published") -> int:
        """WP既存投稿を一括で記録（重複は上書きしない）"""
        if not items:
            return 0
        now = datetime.now().isoformat()
        rows = [(pid, status, wp_id, now) for pid, wp_id in items]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO posted_items
                (product_id, status, wp_post_id, created_at, error_message)
                VALUES (?, ?, ?, ?, NULL)
                ON CONFLICT(product_id) DO UPDATE SET
                    status = CASE
                        WHEN posted_items.status IN ('drafted', 'published') THEN posted_items.status
                        ELSE excluded.status
                    END,
                    wp_post_id = CASE
                        WHEN posted_items.wp_post_id IS NOT NULL THEN posted_items.wp_post_id
                        ELSE excluded.wp_post_id
                    END,
                    created_at = CASE
                        WHEN posted_items.status IN ('drafted', 'published') THEN posted_items.created_at
                        ELSE excluded.created_at
                    END,
                    error_message = NULL
                """,
                rows,
            )
            conn.commit()
        return len(rows)
    
    def record_failure(self, product_id: str, error_message: str) -> None:
        """投稿失敗を記録"""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO posted_items
                (product_id, status, wp_post_id, created_at, error_message)
                VALUES (?, 'failed', NULL, ?, ?)
                """,
                (product_id, datetime.now().isoformat(), error_message)
            )
            conn.commit()
            logger.warning(f"失敗記録: {product_id}, error={error_message}")
    
    def get_stats(self) -> dict[str, int]:
        """統計情報を取得"""
        with self._connect() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'drafted' THEN 1 ELSE 0 END) as drafted,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'dry_run' THEN 1 ELSE 0 END) as dry_run
                FROM posted_items
            """)
            row = cursor.fetchone()
            return {
                "total": row["total"] or 0,
                "drafted": row["drafted"] or 0,
                "failed": row["failed"] or 0,
                "dry_run": row["dry_run"] or 0,
            }

    def get_meta(self, key: str) -> str | None:
        """メタ情報の取得"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM metadata WHERE key = ?",
                (key,),
            ).fetchone()
            return str(row["value"]) if row else None

    def set_meta(self, key: str, value: str) -> None:
        """メタ情報の保存"""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
    
    def clear_failed(self) -> int:
        """失敗した項目をクリア"""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM posted_items WHERE status = 'failed'")
            conn.commit()
            deleted = cursor.rowcount
            logger.info(f"失敗項目をクリア: {deleted}件")
            return deleted
