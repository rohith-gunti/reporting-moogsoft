from apis import maintenance
from email_report import send_email

def main():
    sections = []
    for module in [maintenance]:  # Add more modules here as you create them
        try:
            section = module.get_report_section()
            sections.append(section)
        except Exception as e:
            sections.append(f"Error in {module.__name__}: {e}")

    report_body = "\n\n".join(sections)
    send_email("Moogsoft Daily Consolidated Report", report_body)

if __name__ == "__main__":
    main()
