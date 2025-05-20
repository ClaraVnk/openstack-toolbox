import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys
import configparser
from notification import generate_report

CONFIG_PATH = os.path.expanduser("~/.openstack_toolbox_config.ini")

def create_config_interactive():
    print("🛠️ Configuration initiale SMTP nécessaire.")
    print("Merci de saisir les informations demandées pour configurer l'envoi d'e-mails.\n")

    smtp_server = input("SMTP server (ex: smtp.gmail.com): ").strip()
    smtp_port = input("SMTP port (ex: 587): ").strip()
    smtp_username = input("SMTP username (votre login email): ").strip()
    smtp_password = input("SMTP password (votre mot de passe email): ").strip()
    from_email = input("From email (adresse expéditeur): ").strip()
    to_email = input("To email (adresse destinataire): ").strip()

    config = configparser.ConfigParser()
    config['SMTP'] = {
        'smtp_server': smtp_server,
        'smtp_port': smtp_port,
        'smtp_username': smtp_username,
        'smtp_password': smtp_password,
        'from_email': from_email,
        'to_email': to_email,
    }

    config_path = os.path.expanduser("~/.openstack_toolbox_config.ini")
    with open(config_path, 'w') as configfile:
        config.write(configfile)

    print(f"\n✅ Configuration sauvegardée dans {config_path}\n")

def load_config():
    config_path = os.path.expanduser("~/.openstack_toolbox_config.ini")
    if not os.path.exists(config_path):
        create_config_interactive()

    config = configparser.ConfigParser()
    config.read(config_path)
    if 'SMTP' not in config:
        print("❌ Section [SMTP] manquante dans le fichier de configuration.")
        sys.exit(1)
    return config['SMTP']

def send_email(subject, body):
    smtp_config = load_config()
    smtp_server = smtp_config.get('smtp_server')
    smtp_port = int(smtp_config.get('smtp_port', 587))
    smtp_username = smtp_config.get('smtp_username')
    smtp_password = smtp_config.get('smtp_password')
    from_email = smtp_config.get('from_email')
    to_email = smtp_config.get('to_email')

    if not all([smtp_server, smtp_port, smtp_username, smtp_password, from_email, to_email]):
        print("❌ La configuration SMTP est incomplète dans le fichier de configuration.")
        sys.exit(1)

    # Créer le message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    # Ajouter le corps du message
    msg.attach(MIMEText(body, 'plain'))

    # Envoyer l'e-mail
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)

def main():
    try:
        email_body = generate_report()
        send_email(
            "Rapport hebdomadaire : Infomaniak Openstack Optimisation",
            email_body
        )
        print("✅ Email envoyé avec succès.")
    except FileNotFoundError:
        print("❌ Le fichier de rapport est introuvable.")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'email : {e}")

if __name__ == '__main__':
    main()