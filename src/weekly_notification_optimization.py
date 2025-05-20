import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys
import configparser
from notification import generate_report
import argparse
import subprocess

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

def setup_cron():
    """Ajoute ce script à la crontab pour une exécution automatique chaque lundi à 8h."""
    python_exe = sys.executable
    script_path = os.path.abspath(__file__)
    cron_line = f"0 8 * * 1 {python_exe} {script_path} > /dev/null 2>&1\n"

    result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
    existing_cron = result.stdout if result.returncode == 0 else ""

    if cron_line.strip() in existing_cron:
        print("✅ La tâche cron est déjà configurée.")
        return

    new_cron = existing_cron + cron_line
    proc = subprocess.run(['crontab', '-'], input=new_cron, text=True)
    if proc.returncode == 0:
        print("✅ Tâche cron ajoutée : le script s'exécutera tous les lundis à 8h.")
    else:
        print("❌ Échec lors de l'ajout à la crontab.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup-cron', action='store_true', help="Ajoute une tâche cron pour lancer ce script chaque lundi à 8h.")
    args = parser.parse_args()

    if args.setup_cron:
        setup_cron()
        return

    # Afficher le message d'accueil
    print("\n🎉 Bienvenue dans OpenStack Toolbox v1.3 🎉")
    print("Commandes disponibles :")
    print("  • openstack_summary        → Génère un résumé global du projet")
    print("  • openstack_optimization   → Identifie les ressources sous-utilisées et propose un résumé de la semaine")
    print("  • openstack_weekly_notification   → Paramètre l'envoi d'un e-mail avec le résumé de la semaine")

    header = r"""
  ___                       _             _          
 / _ \ _ __   ___ _ __  ___| |_ __ _  ___| | __      
| | | | '_ \ / _ \ '_ \/ __| __/ _` |/ __| |/ /      
| |_| | |_) |  __/ | | \__ \ || (_| | (__|   <       
_\___/| .__/ \___|_|_|_|___/\__\__,_|\___|_|\_\      
\ \   |_|/ /__  ___| | _| |_   _                     
 \ \ /\ / / _ \/ _ \ |/ / | | | |                    
  \ V  V /  __/  __/   <| | |_| |                    
 _ \_/\_/ \___|\___|_|\_\_|\__, |  _   _             
| \ | | ___ | |_(_)/ _(_) _|___/ _| |_(_) ___  _ __  
|  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \ 
| |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | |
|_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|                                                
         By Loutre

"""
    print(header)

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