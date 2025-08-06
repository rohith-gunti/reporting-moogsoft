from jinja2 import Environment, FileSystemLoader
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import GMAIL_USER, GMAIL_PASS, RECIPIENT_EMAIL

def generate_html_report(data):
    # Load the template from the templates folder
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("health_check.html")  # your template file

    # Render the HTML with your data dictionary
    html = template.render(
        report_date=data.get("report_date"),
        report_start=data.get("report_start"),
        report_end=data.get("report_end"),
        events_count=data.get("events_count"),
        alerts_count=data.get("alerts_count"),
        incidents_count=data.get("incidents_count"),
        noise_reduction=data.get("noise_reduction"),
        inbound_integrations_count=data.get("inbound_integrations_count"),
        outbound_integrations_count=data.get("outbound_integrations_count"),
        recent_inbound_errors=data.get("recent_inbound_errors", {}),
        older_inbound_errors=data.get("older_inbound_errors", {}),
        recent_outbound_errors=data.get("recent_outbound_errors", {}),
        older_outbound_errors=data.get("older_outbound_errors", {})
    )
    return html

def send_email(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL

    # Attach the HTML content as the email body
    part = MIMEText(html_body, "html")
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())





