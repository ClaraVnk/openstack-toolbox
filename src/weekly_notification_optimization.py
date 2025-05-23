#!/usr/bin/env python3

import getpass
import smtplib
import os
import sys
import configparser
import subprocess
import shutil
try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version, PackageNotFoundError
from rich import print
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
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

def generate_report():
    try:
        with open('openstack_optimization_report.txt', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "❌ Le fichier openstack_optimization_report.txt est introuvable."

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

    print(f"\n[bold yellow]🎉 Bienvenue dans OpenStack Toolbox 🧰 v{version} 🎉[/]")
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

    # Générer le rapport
    print("[bold cyan]📝 Génération du rapport hebdomadaire...[/]")
    email_body = generate_report()
    print(email_body)

    try:
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

    # Proposer d'ajouter une tâche cron pour envoi hebdomadaire
    print("💌 Voulez-vous paramétrer l'envoi hebdomadaire automatique par email ? (o/n)")
    reponse = input().strip().lower()
    if reponse == 'o':
        script_path = os.path.abspath(__file__)
        cron_line = f"0 8 * * 1 python3 {script_path}"

        # Vérifier si la tâche cron existe déjà
        try:
            current_crontab = subprocess.check_output(['crontab', '-l'], stderr=subprocess.DEVNULL, text=True)
        except subprocess.CalledProcessError:
            current_crontab = ''

        if cron_line in current_crontab:
            print("ℹ️ La tâche cron existe déjà.")
        else:
            updated_crontab = current_crontab + f"\n{cron_line}\n"
            subprocess.run(['crontab', '-'], input=updated_crontab, text=True)
            print("✅ Tâche cron ajoutée : vous recevrez un email tous les lundis à 8h.")
    else:
        print("❌ Configuration de la tâche cron annulée.")


if __name__ == '__main__':
    main()