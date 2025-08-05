import requests
from collections import defaultdict
from datetime import datetime, timedelta
from config import MOOGSOFT_API_KEY

# === CONSTANTS ===
MAINT_WINDOWS_URL = "https://api.moogsoft.ai/v1/maintenance/windows?limit=5000"
EXPIRED_OCCURRENCES_URL = "https://api.moogsoft.ai/v1/maintenance/occurrences/expired?limit=5000"
ALERTS_URL = "https://api.moogsoft.ai/v1/alerts"
UTC_OFFSET = "+05:30"

HEADERS = {
    "apikey": MOOGSOFT_API_KEY,
    "Content-Type": "application/json"
}

# === HELPERS ===

def fetch_active_maintenance_windows():
    resp = requests.get(MAINT_WINDOWS_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", {}).get("result", []) if isinstance(data, dict) else []

def fetch_expired_occurrences():
    resp = requests.get(EXPIRED_OCCURRENCES_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", {}).get("result", []) if isinstance(data, dict) else []

def fetch_alerts_with_maintenance():
    all_alerts = []
    start = 0
    limit = 5000
    while True:
        payload = {
            "limit": limit,
            "start": start,
            "utcOffset": f"GMT{UTC_OFFSET}",
            "jsonSort": [{"sort": "desc", "colId": "last_event_time"}],
            "fields": ["incidents", "maintenance", "manager", "alert_id", "created_at", "tags"],
            "jsonFilter": {
                "maintenance": {
                    "filterType": "text",
                    "type": "notBlank"
                }
            }
        }
        resp = requests.post(ALERTS_URL, json=payload, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        result = resp.json()
        if result.get("status") != "success":
            raise RuntimeError(f"Unexpected alert API response: {result}")
        alerts = result.get("data", {}).get("result", [])
        if not alerts:
            break
        all_alerts.extend(alerts)
        if len(alerts) < limit:
            break
        start += limit
    return all_alerts

def epoch_seconds_to_local_dt(epoch_sec, offset_hours=5, offset_mins=30):
    dt_utc = datetime.utcfromtimestamp(epoch_sec)
    delta = timedelta(hours=offset_hours, minutes=offset_mins)
    return dt_utc + delta

def month_year_str(dt):
    return dt.strftime("%B %Y")

# === PUBLIC FUNCTION ===

def get_report_section():
    try:
        active = fetch_active_maintenance_windows()
        expired = fetch_expired_occurrences()
        maint_lookup = {}

        for m in active + expired:
            mid = m.get("id")
            if not mid:
                continue
            existing = maint_lookup.get(mid, {})
            maint_lookup[mid] = {
                "name": m.get("name") or existing.get("name") or "(no name)",
                "description": m.get("description") or existing.get("description") or "(no description)",
                "status": m.get("status") or existing.get("status"),
                "start": m.get("start") or existing.get("start"),
                "duration": m.get("duration") or existing.get("duration")
            }

        alerts = fetch_alerts_with_maintenance()
        monthly_manager_counts = defaultdict(lambda: defaultdict(int))
        enriched_alerts = []

        for alert in alerts:
            alert_id = alert.get("alert_id", "<missing_alert_id>")
            manager = alert.get("manager", "Unknown")
            created_at = alert.get("created_at")
            created_dt = epoch_seconds_to_local_dt(created_at) if isinstance(created_at, (int, float)) else None
            month_str = month_year_str(created_dt) if created_dt else "Unknown"
            monthly_manager_counts[month_str][manager] += 1

            maintenance_id = str(alert.get("maintenance")) if alert.get("maintenance") is not None else None
            entry = maint_lookup.get(maintenance_id, {})
            ci = alert.get("tags", {}).get("configurationItem", "(none)")

            enriched_alerts.append({
                "alert_id": alert_id,
                "manager": manager,
                "created_dt": created_dt,
                "maintenance_id": maintenance_id,
                "maintenance_name": entry.get("name", "(unknown)"),
                "maintenance_description": entry.get("description", ""),
                "maintenance_status": entry.get("status"),
                "ci": ci,
            })

        def month_sort_key(m):
            try:
                return datetime.strptime(m, "%B %Y")
            except:
                return datetime.min

        sorted_months = sorted(monthly_manager_counts.keys(), key=month_sort_key, reverse=True)

        report_lines = []
        report_lines.append("=== Maintenance Report ===\n")

        for month in sorted_months:
            report_lines.append(f"{month}")
            for manager, count in sorted(monthly_manager_counts[month].items()):
                report_lines.append(f"  {manager}: {count}")
            report_lines.append("")

        alerts_with_date = [e for e in enriched_alerts if e["created_dt"]]
        alerts_with_date.sort(key=lambda x: x["created_dt"], reverse=True)

        for ea in alerts_with_date[:10]:  # only include top 10 recent
            dtstr = ea["created_dt"].strftime("%Y-%m-%d %H:%M:%S")
            report_lines.append(f"{dtstr} | Alert ID: {ea['alert_id']} | Manager: {ea['manager']} | CI: {ea['ci']}")
            report_lines.append(f"    Maintenance: {ea['maintenance_name']} ({ea['maintenance_status']})")
            report_lines.append(f"    Description: {ea['maintenance_description']}")
            report_lines.append("")

        return "\n".join(report_lines)

    except Exception as e:
        return f"❌ Maintenance report failed: {e}"
