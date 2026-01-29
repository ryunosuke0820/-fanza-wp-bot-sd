import subprocess

# サブドメイン、データベース、ディレクトリを全削除するスクリプト
# サーバー（Linux）上で実行されることを想定

DOMAIN = "av-kantei.com"
HOME_DIR = "/home/aoxacgmk"
SITES = [
    "sd01-chichi",
    "sd02-shirouto",
    "sd03-gyaru",
    "sd04-chijo",
    "sd05-seiso",
    "sd06-hitozuma",
    "sd07-oneesan",
    "sd08-jukujo",
    "sd09-iyashi",
    "sd10-otona",
]

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

def main():
    print("=== サブドメイン・DB一括削除スクリプト (Python版) ===")
    
    confirm = input("本当に全てのサブドメインとデータベースを削除しますか？ (y/n): ")
    if confirm.lower() != 'y':
        print("中止しました。")
        return

    for site in SITES:
        subdomain = f"{site}.{DOMAIN}"
        doc_root = f"{HOME_DIR}/public_html/{subdomain}"
        db_suffix = site.replace('-', '_')
        db_name = f"aoxacgmk_{db_suffix}"
        
        print(f"\n--- Deleting: {subdomain} ---")
        
        # 1. サブドメイン削除 (uapi)
        print(f"Deleting subdomain: {subdomain}...")
        res1 = run_command(f"uapi SubDomain deletesubdomain domain='{site}' rootdomain='{DOMAIN}'")
        print(res1)
        
        # 2. データベース削除 (uapi)
        print(f"Deleting database: {db_name}...")
        res2 = run_command(f"uapi Mysql delete_database name='{db_name}'")
        print(res2)
        
        # 3. ディレクトリ削除
        print(f"Removing directory: {doc_root}...")
        res3 = run_command(f"rm -rf {doc_root}")
        print("Done.")

    print("\n=== 全削除完了 ===")

if __name__ == "__main__":
    main()
