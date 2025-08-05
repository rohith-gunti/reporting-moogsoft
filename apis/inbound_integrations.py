import requests
from config import MOOGSOFT_API_KEY

BASE_URLS = [
    "https://api.moogsoft.ai/v1/integrations/byoapi",
    "https://api.moogsoft.ai/v1/integrations/byoapi?integration=DYNATRACE",
    "https://api.moogsoft.ai/v1/integrations/byoapi?integration=NAGIOS",
    "https://api.moogsoft.ai/v1/integrations/byoapi?integration=PROMETHEUS"
]

def fetch_inbound_integrations() -> dict:
    """
    Fetch all BYOAPI integrations from multiple Moogsoft endpoints.

    Returns:
        dict:
            {
                "total": int,
                "integrations": List[{"name": str, "id": str}]
            }
    """
    headers = {
        "apikey": MOOGSOFT_API_KEY,
        "Content-Type": "application/json"
    }

    seen_ids = set()
    integrations = []

    for url in BASE_URLS:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Error fetching from {url}: {e}")
            continue

        if data.get("status") != "success":
            print(f"API returned error from {url}: {data}")
            continue

        for item in data.get("data", []):
            integration_id = item.get("id")
            if integration_id and integration_id not in seen_ids:
                seen_ids.add(integration_id)
                integrations.append({
                    "name": item.get("endpointName", "Unknown"),
                    "id": integration_id
                })

    return {
        "total": len(integrations),
        "integrations": integrations
    }
