import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
import ssl
import certifi

load_dotenv()

# Forcer Python à utiliser le bundle de certificats de certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())

def send_email(to_email, subject, content):
    message = Mail(
        from_email='roudayna.kouka@etudiant-fst.utm.tn',  # Doit être validé dans SendGrid
        to_emails=to_email,
        subject=subject,
        plain_text_content=content
    )
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        # Passer le contexte SSL
        response = sg.client.mail.send.post(
            request_body=message.get(),
            _request_options={'ssl_context': ssl_context}
        )
        return response.status_code
    except Exception as e:
        print(e)
        return None

if __name__ == "__main__":
    status = send_email("roudaynakouka2003@gmail.com", "Test", "Hello from AI Agent!")
    print("Status:", status)
