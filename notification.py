import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration de l'envoi d'e-mails
smtp_server = '<your-smtp-server>'
smtp_port = 587
smtp_username = '<your-smtp-username>'
smtp_password = '<your-smtp-password>'
from_email = '<your-email>'
to_email = '<recipient-email>'

def send_email(subject, body):
    # Créer le message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    # Ajouter le corps du message
    msg.attach(MIMEText(body, 'plain'))

    # Ajouter les pièces jointes
    with open('cpu_usage.png', 'rb') as f:
        msg.attach(MIMEText(f.read(), 'png'))
    with open('ram_usage.png', 'rb') as f:
        msg.attach(MIMEText(f.read(), 'png'))
    with open('disk_usage.png', 'rb') as f:
        msg.attach(MIMEText(f.read(), 'png'))

    # Envoyer l'e-mail
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)

if __name__ == '__main__':
    try:
        with open('/tmp/openstack_report.txt', 'r') as f:
            email_body = f.read()
        send_email("Récapitulatif des ressources sous-utilisées et analyse de l'utilisation des ressources", email_body)
    except FileNotFoundError:
        print("❌ Le fichier /tmp/openstack_report.txt est introuvable.")
