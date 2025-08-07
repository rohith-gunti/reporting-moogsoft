import requests
from config import MOOGSOFT_API_KEY

AUDIT_API_URL = "https://api.moogsoft.ai/v1/audits"
AUDIT_SERVICES = [
    "ums-apikey", "ums-sso", "ums-role", "maintenance-windows",
    "catalogs", "workflows", "correlation-engine", "correlation-engine-webserver",
    "webhooks", "notification-policies", "byoapi"
]

def fetch_audit_counts(start: int, end: int) -> dict:
    """
    Fetch audit change counts for specified services from Moogsoft API
    in the given time range (epoch milliseconds).

    Args:
        start (int): Start time in epoch milliseconds.
        end (int): End time in epoch milliseconds.

    Returns:
        dict: {
            "ums-apikey": int,
            "ums-sso": int,
            ...
        }
    """
    headers = {
        "apikey": MOOGSOFT_API_KEY,
        "Content-Type": "application/json"
    }

    result = {}

    for service in AUDIT_SERVICES:
        try:
            response = requests.get(
                AUDIT_API_URL,
                headers=headers,
                params={
                    "serviceName": service,
                    "startTime": start,
                    "endTime": end
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                result[service] = 0
                continue

            count = data.get("data", {}).get("count", 0)
            result[service] = count

        except Exception:
            result[service] = 0

    return result
