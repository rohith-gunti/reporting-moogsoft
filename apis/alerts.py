import requests
import json
from datetime import datetime, timezone
from config import MOOGSOFT_API_KEY

ALERTS_API_URL = "https://api.moogsoft.ai/v1/alerts"

def epoch_to_moogsoft_format(epoch_time: int) -> str:
    """
    Convert epoch seconds to Moogsoft time format: YYYY/MM/DD HH:MM:SS AM/PM
    """
    return datetime.fromtimestamp(epoch_time, tz=timezone.utc).strftime("%Y/%m/%d %I:%M:%S %p")

def fetch_alerts_since(start_epoch: int) -> list:
    """
    Fetch all alerts from Moogsoft API starting from start_epoch.
    Handles pagination until no results are returned.
    """
    alerts = []
    headers = {
        "apikey": MOOGSOFT_API_KEY,
        "Content-Type": "application/json"
    }

    alerts_payload = {
        "filter": f"first_event_time >= \"{epoch_to_moogsoft_format(start_epoch)}\"",
        "limit": 5000,
        "fields": [
            "manager",
            "event_count",
            "incidents",
            "tags",
            "check",
            "first_event_time"
        ]
    }

    while True:
        response = requests.post(ALERTS_API_URL, headers=headers, data=json.dumps(alerts_payload), timeout=30)
        response.raise_for_status()
        data = response.json()

        results = data.get("data", {}).get("result", [])
        if not results:
            break

        alerts.extend(results)

        search_after = data.get("data", {}).get("search_after")
        if not search_after:
            break

        alerts_payload["search_after"] = search_after

    return alerts

def aggregate_alerts(this_month_epoch: int, last_24h_epoch: int) -> dict:
    """
    Aggregate alert data per manager and return summary stats.
    Includes special case for Nagios tag instance breakdown.
    """
    # Fetch alerts for this month and last 24h
    month_alerts = fetch_alerts_since(this_month_epoch)
    day_alerts = fetch_alerts_since(last_24h_epoch)

    def summarize(alerts_list):
        per_manager = {}
        nagios_tags = {}

        for alert in alerts_list:
            manager = alert.get("manager", "Unknown")
            event_count = alert.get("event_count", 0)
            incidents = alert.get("incidents", [])
            tags = alert.get("tags", {})

            # Manager aggregation
            mgr_data = per_manager.setdefault(manager, {"alerts": 0, "events": 0, "no_incident_events": 0})
            mgr_data["alerts"] += 1
            mgr_data["events"] += event_count
            if not incidents:
                mgr_data["no_incident_events"] += event_count

            # Special case: Nagios tags.instance breakdown
            if manager == "Nagios" and "instance" in tags:
                instance = tags["instance"]
                nagios_tags[instance] = nagios_tags.get(instance, 0) + event_count

        return per_manager, nagios_tags

    month_summary, month_nagios = summarize(month_alerts)
    day_summary, day_nagios = summarize(day_alerts)

    return {
        "per_manager": {
            "this_month": month_summary,
            "last_24h": day_summary
        },
        "nagios": {
            "this_month": month_nagios,
            "last_24h": day_nagios
        }
    }
