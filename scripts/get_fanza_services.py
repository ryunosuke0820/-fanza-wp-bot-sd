import os
import requests
import json
import sys
import io
from dotenv import load_dotenv

# Set encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_service_list():
    load_dotenv()
    
    api_key = os.getenv("FANZA_API_KEY")
    affiliate_id = os.getenv("FANZA_AFFILIATE_ID")
    
    if not api_key or not affiliate_id:
        print("Error: FANZA_API_KEY or FANZA_AFFILIATE_ID not found in .env")
        return

    url = "https://api.dmm.com/affiliate/v3/FloorList"
    params = {
        "api_id": api_key,
        "affiliate_id": affiliate_id,
        "output": "json"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        result = data.get("result", {})
        site_list = result.get("site", [])
        
        print(f"{'Site':<15} | {'Service Name':<20} | {'Floor Name':<30} | {'Service Code':<15} | {'Floor Code':<15}")
        print("-" * 105)
        
        for site in site_list:
            site_name = site.get("name", "Unknown")
            for service in site.get("service", []):
                service_name = service.get("name", "Unknown")
                service_code = service.get("code", "")
                for floor in service.get("floor", []):
                    floor_name = floor.get("name", "Unknown")
                    floor_code = floor.get("code", "")
                    print(f"{site_name:<15} | {service_name:<20} | {floor_name:<30} | {service_code:<15} | {floor_code:<15}")

    except Exception as e:
        print(f"Error fetching service list: {e}")

if __name__ == "__main__":
    get_service_list()
