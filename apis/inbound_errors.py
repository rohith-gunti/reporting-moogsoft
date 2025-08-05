import requests
from config import MOOGSOFT_API_KEY
from datetime import datetime, timedelta

ERROR_API_TEMPLATE = "https://api.moogsoft.ai/v1/integrations/byoapi/{id}/errors"

HEADERS = {
    "apikey": MOOGSOFT_API_KEY,
    "Content-Type": "application/json"
}

def fetch_inbound_errors(integrations: list[dict], epoch_now: int) -> dict:
    """
    Fetch error details for inbound integrations and separate last 24h and older.

    Args:
        integrations: List of dicts -> { "id": str, "name": str }
        epoch_now: current epoch in ms

    Returns:
        dict {
            "recent_errors": { manager_name: { "count": int, "reasons": set[str] }},
            "older_errors": { manager_name: { "count": int }}
        }
    """
    recent_threshold = epoch_now - (24 * 60 * 60 * 1000)
    recent_errors = {}
    older_errors = {}

    for integration in integrations:
        id_ = integration["id"]
        manager = integration["name"]

        url = ERROR_API_TEMPLATE.format(id=id_)

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Error fetching from {url}: {e}")
            continue

        if data.get("status") != "success":
            continue

        errors = data.get("data", [])

        for error in errors:
            timestamp = error.get("timestamp")
            reasons = error.get("errors", [])

            if timestamp is None:
                continue

            if timestamp >= recent_threshold:
                if manager not in recent_errors:
                    recent_errors[manager] = {
                        "count": 0,
                        "reasons": set()
                    }
                recent_errors[manager]["count"] += 1
                recent_errors[manager]["reasons"].update(reasons)
            else:
                if manager not in older_errors:
                    older_errors[manager] = {
                        "count": 0
                    }
                older_errors[manager]["count"] += 1

    # Convert reason sets to list
    for manager in recent_errors:
        recent_errors[manager]["reasons"] = list(recent_errors[manager]["reasons"])

    return {
        "recent_errors": recent_errors,
        "older_errors": older_errors
    }
