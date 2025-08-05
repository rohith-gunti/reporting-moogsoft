import requests
from config import MOOGSOFT_API_KEY

ERROR_API_TEMPLATE = "https://api.moogsoft.ai/v2/integrations/webhooks/logs/{id}?errors=true&successes=false"

HEADERS = {
    "apikey": MOOGSOFT_API_KEY,
    "Content-Type": "application/json"
}

def fetch_outbound_errors(integrations: list[dict], epoch_now: int) -> dict:
    """
    Fetch error details for outbound (webhook) integrations and separate last 24h and older.

    Args:
        integrations: List of dicts -> { "id": str, "name": str }
        epoch_now: current epoch in ms

    Returns:
        dict {
            "recent_errors": { name: { "count": int, "messages": list[str] }},
            "older_errors": { name: { "count": int }}
        }
    """
    recent_threshold = epoch_now - (24 * 60 * 60 * 1000)
    recent_errors = {}
    older_errors = {}

    for integration in integrations:
        id_ = integration["id"]
        name = integration["name"]

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

        logs = data.get("data", [])

        for log in logs:
            timestamp = log.get("timestamp")
            message = log.get("message", "No message")

            if timestamp is None:
                continue

            if timestamp >= recent_threshold:
                if name not in recent_errors:
                    recent_errors[name] = {
                        "count": 0,
                        "messages": []
                    }
                recent_errors[name]["count"] += 1
                recent_errors[name]["messages"].append(message)
            else:
                if name not in older_errors:
                    older_errors[name] = {
                        "count": 0
                    }
                older_errors[name]["count"] += 1

    return {
        "recent_errors": recent_errors,
        "older_errors": older_errors
    }
