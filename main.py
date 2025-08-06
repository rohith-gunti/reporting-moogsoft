from datetime import datetime, timedelta, timezone
from apis import statistics, inbound_integrations, inbound_errors, outbound_integrations, outbound_errors
from email_report import generate_html_report, send_email

# Define IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

# Global variables to store integration lists for reuse
inbound_integrations_list = []
outbound_integrations_list = []

def main():
    global inbound_integrations_list, outbound_integrations_list

    now = datetime.now(IST)
    start_dt = now - timedelta(days=1)
    end_dt = now

    # Convert to epoch in milliseconds
    start = int(start_dt.timestamp() * 1000)
    end = int(end_dt.timestamp() * 1000)

    # ✅ Fetch Moogsoft statistics
    try:
        stats = statistics.fetch_statistics(start, end)
    except Exception as e:
        print(f"Failed to fetch statistics: {e}")
        return

    # ✅ Fetch inbound integrations
    try:
        inbound_data = inbound_integrations.fetch_inbound_integrations()
        inbound_integrations_count = inbound_data.get("total", 0)
        inbound_integrations_list = inbound_data.get("integrations", [])
    except Exception as e:
        print(f"Failed to fetch inbound integrations: {e}")
        inbound_integrations_count = 0
        inbound_integrations_list = []

    # ✅ Fetch outbound integrations
    try:
        outbound_data = outbound_integrations.fetch_outbound_integrations()
        outbound_integrations_count = outbound_data.get("total", 0)
        outbound_integrations_list = outbound_data.get("integrations", [])
    except Exception as e:
        print(f"Failed to fetch outbound integrations: {e}")
        outbound_integrations_count = 0
        outbound_integrations_list = []

    # ✅ Fetch inbound errors summary
    try:
        inbound_error_summary = inbound_errors.fetch_inbound_errors(
            inbound_integrations_list,
            end
        )
    except Exception as e:
        print(f"Failed to fetch inbound integration errors: {e}")
        inbound_error_summary = {"recent_errors": {}, "older_errors": {}}

    # ✅ Fetch outbound errors summary
    try:
        outbound_error_summary = outbound_errors.fetch_outbound_errors(
            outbound_integrations_list,
            end
        )
    except Exception as e:
        print(f"Failed to fetch outbound integration errors: {e}")
        outbound_error_summary = {"recent_errors": {}, "older_errors": {}}

    # ✅ Prepare email content
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
        "older_outbound_errors": outbound_error_summary.get("older_errors", {})
    }

    # Debug (optional)
    # print("Recent Inbound Errors:", data["recent_inbound_errors"])
    # print("Older Inbound Errors:", data["older_inbound_errors"])
    # print("Recent Outbound Errors:", data["recent_outbound_errors"])
    # print("Older Outbound Errors:", data["older_outbound_errors"])

    # ✅ Generate HTML report
    html_report = generate_html_report(data)

    # ✅ Send email
    try:
        subject_date = now.strftime("%d %B %Y")
        email_subject = f"Moogsoft Daily Health Report – {subject_date}"
        send_email(email_subject, html_report)
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


if __name__ == "__main__":
    main()
