from datetime import datetime, timedelta, timezone
from apis import statistics
from email_report import generate_html_report, send_email

# Define IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def main():
    now = datetime.now(IST)
    start_dt = now - timedelta(days=1)
    end_dt = now

    # Convert to epoch in milliseconds
    start = int(start_dt.timestamp() * 1000)
    end = int(end_dt.timestamp() * 1000)

    # Fetch stats from Moogsoft API
    try:
        stats = statistics.fetch_statistics(start, end)
    except Exception as e:
        print(f"Failed to fetch statistics: {e}")
        return

    # Prepare data dict for the email template
    data = {
        "report_date": now.strftime("%B %d, %Y %I:%M %p IST"),
        "report_start": start_dt.strftime("%B %d, %Y %I:%M %p IST"),
        "report_end": end_dt.strftime("%B %d, %Y %I:%M %p IST"),
        "events_count": stats.get("event_count", 0),
        "alerts_count": stats.get("alert_count", 0),
        "incidents_count": stats.get("incident_count", 0),
        "noise_reduction": stats.get("noise_reduction", 0.0),
    }

    # Generate HTML report from the template and data
    html_report = generate_html_report(data)

    # Send the email
    try:
        send_email("Moogsoft Daily Health Report", html_report)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    main()
