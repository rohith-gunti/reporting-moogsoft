import requests
from config import MOOGSOFT_API_KEY
from datetime import datetime
import re

MAINTENANCE_WINDOWS_API = "https://api.moogsoft.ai/v1/maintenance/windows?limit=5000"
EXPIRED_OCCURRENCES_API = "https://api.moogsoft.ai/v1/maintenance/occurrences/expired?limit=5000"
ALERTS_API = "https://api.moogsoft.ai/v1/alerts"

HEADERS = {
    "apikey": MOOGSOFT_API_KEY,
    "Content-Type": "application/json"
}


def parse_config_items(filter_str: str) -> list:
    """
    Extract configuration items from the filter string.
    """
    match = re.search(r"tags\.configurationItem\s+in\s+\((.*?)\)", filter_str)
    if match:
        return [item.strip(" '\"") for item in match.group(1).split(",")]
    return []


def fetch_maintenance_and_alerts(epoch_now: int) -> dict:
    """
    Fetch maintenance stats and alerts affected by maintenance.

    Args:
        epoch_now: Current time in epoch ms.

    Returns:
        dict: A dictionary with maintenance and alert stats.
    """
    one_day_ms = 24 * 60 * 60 * 1000
    now = epoch_now
    last_24h = now - one_day_ms

    dt_now = datetime.utcfromtimestamp(epoch_now / 1000.0)

    start_of_week = int(datetime(dt_now.year, dt_now.month, dt_now.day).timestamp() * 1000)
    start_of_month = int(datetime(dt_now.year, dt_now.month, 1).timestamp() * 1000)

    # Last week range (Mon to Sun)
    from datetime import timedelta
    weekday = dt_now.weekday()  # 0 = Monday
    start_last_week = int((dt_now - timedelta(days=weekday + 7)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    end_last_week = int((dt_now - timedelta(days=weekday + 1)).replace(hour=23, minute=59, second=59, microsecond=999999).timestamp() * 1000)

    # Maintenance Windows
    try:
        windows_res = requests.get(MAINTENANCE_WINDOWS_API, headers=HEADERS, timeout=10)
        windows_res.raise_for_status()
        windows_data = windows_res.json().get("data", {}).get("result", [])
    except Exception as e:
        print("Error fetching maintenance windows:", e)
        windows_data = []

    active_24h = 0
    config_items_count = 0
    total_this_month = 0

    for window in windows_data:
        start = window.get("start")
        duration = window.get("duration", 0)
        end = start + duration if start else 0

        if start and end >= last_24h:
            active_24h += 1
            config_items = parse_config_items(window.get("filter", ""))
            config_items_count += len(config_items)

        if start and start >= start_of_month:
            total_this_month += 1

    # Affected Alerts
    try:
        alerts_res = requests.post(ALERTS_API, headers=HEADERS, json={
            "limit": 5000,
            "start": 0,
            "utcOffset": "GMT+05:30",
            "jsonSort": [{"sort": "desc", "colId": "last_event_time"}],
            "fields": ["incidents", "maintenance", "manager", "alert_id", "created_at"],
            "jsonFilter": {
                "maintenance": {"filterType": "text", "type": "notBlank"}
            }
        }, timeout=15)
        alerts_res.raise_for_status()
        alerts = alerts_res.json().get("data", {}).get("alerts", [])
    except Exception as e:
        print("Error fetching maintenance alerts:", e)
        alerts = []

    def group_alerts(alerts, time_filter_start=None, time_filter_end=None):
        counts = {}
        for alert in alerts:
            created = alert.get("created_at", 0)
            if time_filter_start and created < time_filter_start:
                continue
            if time_filter_end and created > time_filter_end:
                continue
            manager = alert.get("manager", "Unknown")
            counts[manager] = counts.get(manager, 0) + 1
        return counts

    return {
        "maintenance_summary": {
            "active_last_24h": active_24h,
            "config_items_in_24h": config_items_count,
            "total_this_month": total_this_month
        },
        "alerts_by_maintenance": {
            "last_24h": group_alerts(alerts, time_filter_start=last_24h),
            "this_week": group_alerts(alerts, time_filter_start=start_of_week),
            "last_week": group_alerts(alerts, time_filter_start=start_last_week, time_filter_end=end_last_week),
            "this_month": group_alerts(alerts, time_filter_start=start_of_month)
        }
    }
