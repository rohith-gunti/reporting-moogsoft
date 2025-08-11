import time
from datetime import datetime, timedelta, timezone
from apis import (
    statistics, inbound_integrations, inbound_errors,
    outbound_integrations, outbound_errors, catalogs,
    maintenance, audits, alerts, incidents
)
from email_report import generate_html_report, send_email

IST = timezone(timedelta(hours=5, minutes=30))

inbound_integrations_list = []
outbound_integrations_list = []

def main():
    global inbound_integrations_list, outbound_integrations_list

    overall_start = time.perf_counter()
    now = datetime.now(IST)
    start_dt = now - timedelta(days=1)
    end_dt = now

    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    epoch_now_sec = int(now.timestamp())
    last_24h_sec = epoch_now_sec - (24 * 60 * 60)
    month_start_sec = int(datetime(now.year, now.month, 1, tzinfo=IST).timestamp())

    # Timing each block
    t0 = time.perf_counter()
    try:
        stats = statistics.fetch_statistics(start_ms, end_ms)
    except Exception as e:
        print(f"Failed to fetch statistics: {e}")
        return
    print(f"Fetch statistics: {time.perf_counter() - t0:.2f} seconds")

    t0 = time.perf_counter()
    try:
        inbound_data = inbound_integrations.fetch_inbound_integrations()
        inbound_integrations_count = inbound_data.get("total", 0)
        inbound_integrations_list = inbound_data.get("integrations", [])
    except Exception as e:
        print(f"Failed to fetch inbound integrations: {e}")
        inbound_integrations_count = 0
        inbound_integrations_list = []
    print(f"Fetch inbound integrations: {time.perf_counter() - t0:.2f} seconds")

    t0 = time.perf_counter()
    try:
        outbound_data = outbound_integrations.fetch_outbound_integrations()
        outbound_integrations_count = outbound_data.get("total", 0)
        outbound_integrations_list = outbound_data.get("integrations", [])
    except Exception as e:
        print(f"Failed to fetch outbound integrations: {e}")
        outbound_integrations_count = 0
        outbound_integrations_list = []
    print(f"Fetch outbound integrations: {time.perf_counter() - t0:.2f} seconds")

    t0 = time.perf_counter()
    try:
        inbound_error_summary = inbound_errors.fetch_inbound_errors(
            inbound_integrations_list,
            end_ms
        )
    except Exception as e:
        print(f"Failed to fetch inbound integration errors: {e}")
        inbound_error_summary = {"recent_errors": {}, "older_errors": {}}
    print(f"Fetch inbound errors: {time.perf_counter() - t0:.2f} seconds")

    t0 = time.perf_counter()
    try:
        outbound_error_summary = outbound_errors.fetch_outbound_errors(
            outbound_integrations_list,
            end_ms
        )
    except Exception as e:
        print(f"Failed to fetch outbound integration errors: {e}")
        outbound_error_summary = {"recent_errors": {}, "older_errors": {}}
    print(f"Fetch outbound errors: {time.perf_counter() - t0:.2f} seconds")

    t0 = time.perf_counter()
    catalog_summary = catalogs.fetch_recent_catalog_updates(end_ms)
    print(f"Fetch catalog updates: {time.perf_counter() - t0:.2f} seconds")

    t0 = time.perf_counter()
    try:
        maintenance_data = maintenance.fetch_maintenance_and_alerts(end_ms)
    except Exception as e:
        print(f"Failed to fetch maintenance data: {e}")
        maintenance_data = {
            "maintenance_summary": {
                "active_last_24h": 0,
                "config_items_in_24h": 0,
                "total_this_month": 0
            },
            "alerts_by_maintenance": {
                "last_24h": {},
                "this_week": {},
                "last_week": {},
                "this_month": {}
            }
        }
    print(f"Fetch maintenance data: {time.perf_counter() - t0:.2f} seconds")

    t0 = time.perf_counter()
    try:
        audit_summary = audits.fetch_audit_counts(start_ms, end_ms)
    except Exception as e:
        print(f"Failed to fetch audit summary: {e}")
        audit_summary = {}
    print(f"Fetch audit summary: {time.perf_counter() - t0:.2f} seconds")

    t0 = time.perf_counter()
    try:
        alerts_summary = alerts.aggregate_alerts(
            this_month_epoch=month_start_sec,
            last_24h_epoch=last_24h_sec
        )
    except Exception as e:
        print(f"Failed to fetch alerts summary: {e}")
        alerts_summary = {
            "per_manager": {"this_month": {}, "last_24h": {}},
            "nagios": {"this_month": {}, "last_24h": {}}
        }
    print(f"Fetch alerts summary: {time.perf_counter() - t0:.2f} seconds")

    t0 = time.perf_counter()
    try:
        incidents_summary = incidents.aggregate_incidents(
            this_month_epoch=month_start_sec,
            last_24h_epoch=last_24h_sec
        )
    except Exception as e:
        print(f"Failed to fetch incidents summary: {e}")
        incidents_summary = {
            "this_month": {},
            "last_24h": {}
        }
    print(f"Fetch incidents summary: {time.perf_counter() - t0:.2f} seconds")

    data = {
        "report_date": now.strftime("%B %d, %Y %I:%M %p IST"),
        "report_start": start_dt.strftime("%B %d, %Y %I:%M %p IST"),
        "report_end": end_dt.strftime("%B %d, %Y %I:%M %p IST"),
        "events_count": stats.get("event_count", 0),
        "alerts_count": stats.get("alert_count", 0),
        "incidents_count": stats.get("incident_count", 0),
        "noise_reduction": stats.get("noise_reduction", 0.0),
        "inbound_integrations_count": inbound_integrations_count,
        "outbound_integrations_count": outbound_integrations_count,
        "recent_inbound_errors": inbound_error_summary.get("recent_errors", {}),
        "older_inbound_errors": inbound_error_summary.get("older_errors", {}),
        "recent_outbound_errors": outbound_error_summary.get("recent_errors", {}),
        "older_outbound_errors": outbound_error_summary.get("older_errors", {}),
        "recent_catalogs": catalog_summary.get("recent_catalogs", []),
        "catalog_sync_status": catalog_summary.get("sync_status", "Failed"),
        "maintenance_summary": maintenance_data.get("maintenance_summary", {}),
        "alerts_by_maintenance": maintenance_data.get("alerts_by_maintenance", {}),
        "audit_summary": audit_summary,
        "alerts_summary": alerts_summary,
        "incidents_summary": incidents_summary
    }

    t0 = time.perf_counter()
    html_report = generate_html_report(data)
    print(f"Generate HTML report: {time.perf_counter() - t0:.2f} seconds")

    try:
        subject_date = now.strftime("%d %B %Y")
        email_subject = f"Moogsoft Daily Health Report – {subject_date}"
        send_email(email_subject, html_report)
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

    print(f"Total execution time: {time.perf_counter() - overall_start:.2f} seconds")


if __name__ == "__main__":
    main()
