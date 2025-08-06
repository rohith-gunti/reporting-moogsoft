import requests
from config import MOOGSOFT_API_KEY
from datetime import datetime, timezone, timedelta

CATALOG_API_URL = "https://api.moogsoft.ai/v2/catalogs"
HEADERS = {
    "apikey": MOOGSOFT_API_KEY,
    "Content-Type": "application/json"
}

# Define IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def fetch_recent_catalog_updates(epoch_now: int, limit: int = 5) -> dict:
    """
    Fetch recent catalog updates and check sync status.

    Args:
        epoch_now (int): Current epoch time in ms
        limit (int): Number of recent catalogs to return

    Returns:
        dict: {
            "recent_catalogs": List[{
                "name": str,
                "entries": int,
                "last_updated": str (IST format)
            }],
            "sync_status": "Success" or "Failed"
        }
    """
    try:
        response = requests.get(CATALOG_API_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching catalogs: {e}")
        return {"recent_catalogs": [], "sync_status": "Failed"}

    if data.get("status") != "success":
        print(f"API returned error: {data}")
        return {"recent_catalogs": [], "sync_status": "Failed"}

    catalogs = data.get("data", [])
    if not catalogs:
        return {"recent_catalogs": [], "sync_status": "Failed"}

    # Sort by last_updated descending
    catalogs.sort(key=lambda x: x.get("last_updated", 0), reverse=True)

    # Pick top 'limit' catalogs
    recent_catalogs = []
    sync_success = True
    recent_threshold = epoch_now - (24 * 60 * 60 * 1000)  # 24 hours in ms

    for catalog in catalogs[:limit]:
        last_updated = catalog.get("last_updated", 0)
        last_updated_dt = datetime.fromtimestamp(last_updated / 1000, IST)
        recent_catalogs.append({
            "name": catalog.get("name", "Unknown"),
            "entries": catalog.get("entries", 0),
            "last_updated": last_updated_dt.strftime("%B %d, %Y %I:%M %p IST")
        })

        # Check if any catalog is older than 24 hours
        if last_updated < recent_threshold:
            sync_success = False

    return {
        "recent_catalogs": recent_catalogs,
        "sync_status": "Success" if sync_success else "Failed"
    }
