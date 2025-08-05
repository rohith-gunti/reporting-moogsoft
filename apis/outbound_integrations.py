import requests
from config import MOOGSOFT_API_KEY

WEBHOOKS_URL = "https://api.moogsoft.ai/v2/integrations/webhooks/items"

def fetch_outbound_integrations() -> dict:
    """
    Fetch all outbound webhook integrations from Moogsoft.

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

    try:
        response = requests.get(WEBHOOKS_URL, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching outbound integrations: {e}")
        return {"total": 0, "integrations": []}

    if data.get("status") != "success":
        print(f"API returned error: {data}")
        return {"total": 0, "integrations": []}

    integrations = []
    seen_ids = set()

    for item in data.get("data", []):
        integration_id = item.get("id")
        name = item.get("name", "Unknown")

        if integration_id and integration_id not in seen_ids:
            seen_ids.add(integration_id)
            integrations.append({
                "name": name,
                "id": integration_id
            })

    return {
        "total": len(integrations),
        "integrations": integrations
    }
