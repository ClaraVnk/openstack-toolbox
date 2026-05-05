#!/usr/bin/env python3

import os
import smtplib
import subprocess
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from rich import print

from .config import (
    create_smtp_config_interactive,
    get_language_preference,
    load_smtp_config,
)
from .utils import get_version, print_header

# Dictionnaire des traductions
TRANSLATIONS = {
    "fr": {
        "welcome": "🎉 Bienvenue dans OpenStack Toolbox 🧰 v{} 🎉",
        "config_needed": "🛠️ Configuration initiale SMTP nécessaire.",
        "enter_info": "Merci de saisir les informations demandées pour configurer l'envoi d'e-mails.\n",
        "gmail_warning": "⚠️ Pour Gmail, vous devez activer la validation en 2 étapes et créer un mot de passe d'application.",
        "gmail_help": "Voici la page d'aide Google : https://support.google.com/accounts/answer/185833",
        "gmail_app_password": "⚠️ Pour Gmail, utilisez un mot de passe d'application, pas votre mot de passe habituel.",
        "smtp_server": "SMTP server (ex: smtp.gmail.com): ",
        "smtp_port": "SMTP port (ex: 587): ",
        "smtp_username": "SMTP username (votre login email): ",
        "smtp_password": "SMTP password (mot de passe email ou mot de passe d'application Gmail) : ",
        "to_email": "Adresse e-mail destinataire : ",
        "config_saved": "✅ Configuration sauvegardée dans",
        "smtp_missing": "❌ Section [SMTP] manquante dans le fichier de configuration.",
        "report_not_found": "❌ Le fichier openstack_optimization_report.txt est introuvable.",
        "smtp_incomplete": "❌ La configuration SMTP est incomplète dans le fichier de configuration.",
        "generating_report": "📝 Génération du rapport hebdomadaire...",
        "email_sent": "✅ Email envoyé avec succès.",
        "report_missing": "❌ Le fichier de rapport est introuvable.",
        "email_error": "❌ Erreur lors de l'envoi de l'email : {}",
        "check_smtp": "💡 Vérifiez que votre configuration SMTP est correcte.",
        "reconfigure": "Souhaitez-vous reconfigurer maintenant et envoyer un e-mail test ? (o/n)",
        "test_email_sent": "📬 E-mail test envoyé avec succès.",
        "test_email_failed": "❌ L'envoi de l'e-mail test a échoué : {}",
        "check_credentials": "ℹ️ Veuillez vérifier vos identifiants ou paramètres SMTP.",
        "retry_later": "ℹ️ Vous pouvez relancer ce script plus tard après correction de la configuration.",
        "setup_weekly": "💌 Voulez-vous paramétrer l'envoi hebdomadaire automatique par email ? (o/n)",
        "cron_exists": "ℹ️ La tâche cron existe déjà.",
        "cron_added": "✅ Tâche cron ajoutée : vous recevrez un email tous les lundis à 8h.",
        "cron_cancelled": "❌ Configuration de la tâche cron annulée.",
        "cron_exception": "❌ Erreur lors de la configuration de la tâche cron : {}",
        "email_subject": "Rapport hebdomadaire : Infomaniak Openstack Optimisation",
        "test_email_subject": "Test SMTP - OpenStack Toolbox",
        "test_email_body": "✅ Ceci est un e-mail test de la configuration SMTP.",
    },
    "en": {
        "welcome": "🎉 Welcome to OpenStack Toolbox 🧰 v{} 🎉",
        "config_needed": "🛠️ Initial SMTP configuration needed.",
        "enter_info": "Please enter the requested information to configure email sending.\n",
        "gmail_warning": "⚠️ For Gmail, you need to enable 2-step verification and create an app password.",
        "gmail_help": "Here's the Google help page: https://support.google.com/accounts/answer/185833",
        "gmail_app_password": "⚠️ For Gmail, use an app password, not your regular password.",
        "smtp_server": "SMTP server (e.g., smtp.gmail.com): ",
        "smtp_port": "SMTP port (e.g., 587): ",
        "smtp_username": "SMTP username (your email login): ",
        "smtp_password": "SMTP password (email password or Gmail app password): ",
        "to_email": "Recipient email address: ",
        "config_saved": "✅ Configuration saved in",
        "smtp_missing": "❌ [SMTP] section missing in configuration file.",
        "report_not_found": "❌ The file openstack_optimization_report.txt was not found.",
        "smtp_incomplete": "❌ SMTP configuration is incomplete in the configuration file.",
        "generating_report": "📝 Generating weekly report...",
        "email_sent": "✅ Email sent successfully.",
        "report_missing": "❌ Report file not found.",
        "email_error": "❌ Error sending email: {}",
        "check_smtp": "💡 Please check your SMTP configuration.",
        "reconfigure": "Would you like to reconfigure now and send a test email? (y/n)",
        "test_email_sent": "📬 Test email sent successfully.",
        "test_email_failed": "❌ Test email sending failed: {}",
        "check_credentials": "ℹ️ Please verify your SMTP credentials and settings.",
        "retry_later": "ℹ️ You can run this script again later after fixing the configuration.",
        "setup_weekly": "💌 Would you like to set up automatic weekly email sending? (y/n)",
        "cron_exists": "ℹ️ Cron task already exists.",
        "cron_added": "✅ Cron task added: you will receive an email every Monday at 8 AM.",
        "cron_cancelled": "❌ Cron task configuration cancelled.",
        "cron_exception": "❌ Error configuring cron task: {}",
        "email_subject": "Weekly Report: Infomaniak Openstack Optimization",
        "test_email_subject": "SMTP Test - OpenStack Toolbox",
        "test_email_body": "✅ This is a test email from the SMTP configuration.",
    },
}


def generate_report():
    """
    Génère un rapport hebdomadaire des ressources OpenStack.

    Le rapport inclut :
    - Liste des instances
    - Utilisation des ressources
    - Coûts estimés
    - Recommandations d'optimisation

    Returns:
        str: Contenu du rapport au format HTML

    Examples:
        >>> report = generate_report()
        >>> print(report[:100])  # Affiche le début du rapport
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rapport hebdomadaire OpenStack</title>
    """
    # Exécuter openstack_summary.py pour générer le rapport
    try:
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "openstack_summary.py"),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            return f"Erreur lors de la génération du rapport (code {result.returncode}) : {result.stderr.strip()}"
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Erreur : délai dépassé lors de la génération du rapport."
    except Exception as e:
        return f"Erreur lors de la génération du rapport : {str(e)}"


def send_email(smtp_config, subject, body):
    """
    Envoie un email via SMTP avec le rapport hebdomadaire.

    Args:
        smtp_config (dict): Configuration SMTP avec les clés :
            - server: Serveur SMTP
            - port: Port SMTP
            - username: Nom d'utilisateur
            - password: Mot de passe
            - from_email: Email expéditeur
            - to_email: Email destinataire
        subject (str): Sujet de l'email
        body (str): Corps de l'email (HTML)

    Returns:
        bool: True si l'email a été envoyé avec succès, False sinon

    Examples:
        >>> config = load_smtp_config()
        >>> if config:
        ...     success = send_email(
        ...         config,
        ...         "Test SMTP",
        ...         "<h1>Test</h1><p>Ceci est un test.</p>"
        ...     )
        ...     print("Email envoyé" if success else "Échec")
    """
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_config["from_email"]
        msg["To"] = smtp_config["to_email"]
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(smtp_config["server"], smtp_config["port"]) as server:
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[bold red]❌ Erreur lors de l'envoi de l'email : {str(e)}[/]")
        return False


def setup_cron():
    """
    Configure une tâche cron pour l'envoi hebdomadaire du rapport.

    La tâche est configurée pour s'exécuter tous les lundis à 8h00.

    Returns:
        bool: True si la tâche cron a été configurée avec succès, False sinon

    Examples:
        >>> if setup_cron():
        ...     print("Tâche cron configurée")
        ... else:
        ...     print("Échec de la configuration")
    """
    lang = get_language_preference()
    try:
        script_path = os.path.abspath(__file__)
        cron_cmd = f"0 8 * * 1 {sys.executable} {script_path}"

        # Lire le crontab actuel
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            current_crontab = result.stdout
        else:
            current_crontab = ""

        # Vérifier si la tâche existe déjà
        if script_path in current_crontab:
            print(f"[yellow]{TRANSLATIONS[lang]['cron_exists']}[/]")
            return True

        # Ajouter la nouvelle tâche
        new_crontab = current_crontab.strip() + f"\n{cron_cmd}\n"

        # Écrire le nouveau crontab
        process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
        process.communicate(input=new_crontab.encode())

        if process.returncode == 0:
            print(f"[green]{TRANSLATIONS[lang]['cron_added']}[/]")
            return True
        else:
            print(f"[red]{TRANSLATIONS[lang]['cron_cancelled']}[/]")
            return False

    except Exception as e:
        print(f"[red]{TRANSLATIONS[lang]['cron_exception'].format(str(e))}[/]")
        return False


def main():
    """
    Fonction principale du script de notification hebdomadaire.

    Cette fonction :
    1. Vérifie la configuration SMTP
    2. Génère le rapport hebdomadaire
    3. Envoie le rapport par email
    4. Configure la tâche cron si nécessaire

    Examples:
        >>> if __name__ == "__main__":
        ...     main()
    """
    lang = get_language_preference()
    version = get_version()

    print(f"\n[yellow bold]{TRANSLATIONS[lang]['welcome'].format(version)}[/yellow bold]")
    print_header("WEEKLY NOTIFICATION")

    # Vérifier/créer la configuration SMTP
    smtp_config = load_smtp_config()
    if not smtp_config:
        if not create_smtp_config_interactive():
            return
        smtp_config = load_smtp_config()
        if not smtp_config:
            return

    # Générer et envoyer le rapport
    print(f"[bold cyan]{TRANSLATIONS[lang]['generating_report']}[/]")
    email_body = generate_report()
    print(email_body)

    # Envoyer l'email
    if send_email(smtp_config, TRANSLATIONS[lang]["test_email_subject"], email_body):
        print(f"[bold green]{TRANSLATIONS[lang]['email_sent']}[/]")
    else:
        print(f"[bold red]{TRANSLATIONS[lang]['check_smtp']}[/]")
        return

    # Configurer la tâche cron
    setup_cron()


if __name__ == "__main__":
    main()
