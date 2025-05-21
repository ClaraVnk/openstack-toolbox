import getpass
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys
import configparser
try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version, PackageNotFoundError
from rich import print
from notification import generate_report
from cron_notification import setup_cron

CONFIG_PATH = os.path.expanduser("~/.openstack_toolbox_config.ini")

def get_version():
    try:
        return version("openstack-toolbox")
    except PackageNotFoundError:
        return "unknown"

def create_config_interactive():
    print("[bold cyan]🛠️ Configuration initiale SMTP nécessaire.[/]")
    print("Merci de saisir les informations demandées pour configurer l'envoi d'e-mails.\n")

    smtp_server = input("SMTP server (ex: smtp.gmail.com): ").strip()
    if smtp_server.lower() == "smtp.gmail.com":
        print("[bold yellow]⚠️ Pour Gmail, vous devez activer la validation en 2 étapes et créer un mot de passe d’application.[/]")
        print("Voici la page d’aide Google : https://support.google.com/accounts/answer/185833")
        print("[bold yellow]⚠️ Pour Gmail, utilisez un mot de passe d’application, pas votre mot de passe habituel.[/]")
    smtp_port = input("SMTP port (ex: 587): ").strip()
    smtp_username = input("SMTP username (votre login email): ").strip()
    smtp_password = getpass.getpass("SMTP password (mot de passe email ou mot de passe d’application Gmail) : ").strip()
    from_email = smtp_username  # l'adresse expéditeur = login SMTP
    to_email = input("Adresse e-mail destinataire : ").strip()

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

    print(f"\n[bold green]✅ Configuration sauvegardée dans[/] [underline]{config_path}[/]\n")

def load_config():
    config_path = os.path.expanduser("~/.openstack_toolbox_config.ini")
    if not os.path.exists(config_path):
        create_config_interactive()

    config = configparser.ConfigParser()
    config.read(config_path)
    if 'SMTP' not in config:
        print("[bold red]❌ Section [SMTP] manquante dans le fichier de configuration.[/]")
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
        print("[bold red]❌ La configuration SMTP est incomplète dans le fichier de configuration.[/]")
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
    version = get_version()
    # Afficher le message d'accueil
    print(f"\n[bold yellow]🎉 Bienvenue dans OpenStack Toolbox v{version} 🎉[/]")
    print("[cyan]Commandes disponibles :[/]")
    print("  • [bold]openstack_summary[/]        → Génère un résumé global du projet")
    print("  • [bold]openstack_optimization[/]   → Identifie les ressources sous-utilisées et propose un résumé de la semaine")
    print("  • [bold]openstack_weekly_notification[/]   → Paramètre l'envoi d'un e-mail avec le résumé de la semaine")

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
        print("[bold green]✅ Email envoyé avec succès.[/]")
    except FileNotFoundError:
        print("[bold red]❌ Le fichier de rapport est introuvable.[/]")
    except Exception as e:
        print(f"[bold red]❌ Erreur lors de l'envoi de l'email :[/] {e}")
        print("[bold yellow]💡 Vérifiez que votre configuration SMTP est correcte.[/]")
        print("Souhaitez-vous reconfigurer maintenant et envoyer un e-mail test ? (o/n)")
        retry = input().strip().lower()
        if retry == 'o':
            create_config_interactive()
            try:
                send_email("Test SMTP - OpenStack Toolbox", "✅ Ceci est un e-mail test de la configuration SMTP.")
                print("[bold green]📬 E-mail test envoyé avec succès.[/]")
            except Exception as e:
                print(f"[bold red]❌ L'envoi de l'e-mail test a échoué :[/] {e}")
                print("[bold cyan]ℹ️ Veuillez vérifier vos identifiants ou paramètres SMTP.[/]")
        else:
            print("[bold cyan]ℹ️ Vous pouvez relancer ce script plus tard après correction de la configuration.[/]")

    print("\n💌 Voulez-vous paramétrer l'envoi hebdomadaire d'un e-mail avec le résumé de la semaine ? (o/n)")
    choice = input().strip().lower()
    if choice == 'o':
        setup_cron()
        print("[bold green]✅ Configuration terminée. Vous pouvez maintenant envoyer des e-mails.[/]")
    else:
        print("[bold yellow]❌ Configuration annulée.[/]")

if __name__ == '__main__':
    main()