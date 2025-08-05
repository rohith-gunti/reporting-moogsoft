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
        noise_reduction=data.get("noise_reduction")
        inbound_total=data.get("inbound_total", 0),
        outbound_total=data.get("outbound_total", 0)
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

