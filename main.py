from datetime import datetime, timedelta
from apis import statistics
from email_report import generate_html_report, send_email

def main():
    now = datetime.utcnow()
    start = int((now - timedelta(days=1)).timestamp())  # epoch seconds, 24 hours ago
    end = int(now.timestamp())

    # Fetch stats from Moogsoft API
    try:
        stats = statistics.fetch_statistics(start, end)
    except Exception as e:
        print(f"Failed to fetch statistics: {e}")
        return

    # Prepare data dict for the email template
    data = {
        "report_date": now.strftime("%B %d, %Y %I:%M %p UTC"),
        "report_start": datetime.utcfromtimestamp(start).strftime("%B %d, %Y %I:%M %p UTC"),
        "report_end": datetime.utcfromtimestamp(end).strftime("%B %d, %Y %I:%M %p UTC"),
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
