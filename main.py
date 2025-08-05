from datetime import datetime, timedelta, timezone
from apis import statistics, inbound_integrations
from email_report import generate_html_report, send_email

# Define IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

# Global variable to store integration list for reuse
inbound_integrations_list = []

def main():
    global inbound_integrations_list

    now = datetime.now(IST)
    start_dt = now - timedelta(days=1)
    end_dt = now

    # Convert to epoch in milliseconds
    start = int(start_dt.timestamp() * 1000)
    end = int(end_dt.timestamp() * 1000)

    # Fetch Moogsoft statistics
    try:
        stats = statistics.fetch_statistics(start, end)
    except Exception as e:
        print(f"Failed to fetch statistics: {e}")
        return

    # Fetch inbound integrations
    try:
        inbound_data = inbound_integrations.fetch_inbound_integrations()
        inbound_integrations_count = inbound_data.get("total", 0)
        inbound_integrations_list = inbound_data.get("integrations", [])
    except Exception as e:
        print(f"Failed to fetch inbound integrations: {e}")
        inbound_integrations_count = 0
        inbound_integrations_list = []

    # Placeholder for outbound integrations (can be added later)
    outbound_integrations_count = 0

    # Prepare email content
    data = {
        "report_date": now.strftime("%B %d, %Y %I:%M %p IST"),
        "report_start": start_dt.strftime("%B %d, %Y %I:%M %p IST"),
        "report_end": end_dt.strftime("%B %d, %Y %I:%M %p IST"),
        "events_count": stats.get("event_count", 0),
        "alerts_count": stats.get("alert_count", 0),
        "incidents_count": stats.get("incident_count", 0),
        "noise_reduction": stats.get("noise_reduction", 0.0),
        "inbound_integrations_count": inbound_integrations_count,
        "outbound_integrations_count": outbound_integrations_count
    }

    # Generate HTML report
    html_report = generate_html_report(data)

    # Send email
    try:
        subject_date = now.strftime("%d %B %Y")
        email_subject = f"Moogsoft Daily Health Report – {subject_date}"
        send_email(email_subject, html_report)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    main()
