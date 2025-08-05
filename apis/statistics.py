import requests
from config import MOOGSOFT_API_KEY

API_URL_TEMPLATE = "https://api.moogsoft.ai/v2/stats/overview?start={start}&end={end}"

def fetch_statistics(start: int, end: int) -> dict:
    """
    Fetch statistics overview from Moogsoft API.

    Args:
        start (int): Start timestamp in epoch seconds.
        end (int): End timestamp in epoch seconds.

    Returns:
        dict: {
            "incident_count": int,
            "alert_count": int,
            "event_count": int,
            "noise_reduction": float (percentage, rounded to 2 decimals)
        }
    """
    url = API_URL_TEMPLATE.format(start=start, end=end)
    headers = {
        "apikey": MOOGSOFT_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "success":
        raise RuntimeError(f"API returned error status: {data}")

    stats = data.get("data", {})
    incident_count = stats.get("incident_count", 0)
    alert_count = stats.get("alert_count", 0)
    event_count = stats.get("event_count", 0)

    noise_reduction = 0.0
    if event_count > 0:
        noise_reduction = (1 - (incident_count / event_count)) * 100

    return {
        "incident_count": incident_count,
        "alert_count": alert_count,
        "event_count": event_count,
        "noise_reduction": round(noise_reduction, 2)
    }
