import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


SMTP_SERVER = 'smtp.gmail.com'  # Replace with your email provider's SMTP server
SMTP_PORT = 587    # Common port for TLS

def send_email(email_subject, email_body, 
               attach_html_str=None,
               attach_html_path=None,
               attach_filename=None):
    
    """
    Send an email with HTML body and (optionally) attach an .html file.

    - email_body_html: HTML shown inline in the email body.
    - attach_html_str: If provided, attaches this HTML as a file.
    - attach_html_path: If provided, reads this file and attaches it.
    - attach_filename: File name to show for the attachment (default .html).
    """

    if attach_html_str and attach_html_path:
        raise ValueError("Provide either attach_html_str OR attach_html_path, not both.")

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = ", ".join(RECIPIENT_EMAIL) 
    msg['Subject'] = email_subject

    # Attach the text result
    # msg.attach(MIMEText(email_body, 'html'))

    # Inline HTML body (what appears in the email)
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(email_body, "html", "utf-8"))
    msg.attach(alt)

    if attach_html_str is not None:
        attach_part = MIMEText(attach_html_str, 'html', 'utf-8')
        attach_part.add_header('Content-Disposition', f'attachment; filename="{attach_filename}"')
        msg.attach(attach_part)

    # Send the email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
            print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

