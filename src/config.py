#!/usr/bin/env python3

import configparser
import getpass
import json
import os

from dotenv import load_dotenv
from rich import print
from rich.prompt import Prompt

CONFIG_DIR = os.path.expanduser("~/.config/openstack-toolbox")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SMTP_CONFIG_FILE = os.path.join(CONFIG_DIR, "smtp_config.ini")

# Assurez-vous que le répertoire de configuration existe
os.makedirs(CONFIG_DIR, exist_ok=True)


def get_language_preference():
    """
    Récupère la préférence de langue depuis le fichier de configuration.

    La langue est stockée dans le fichier ~/.config/openstack-toolbox/config.json.
    Si le fichier n'existe pas ou si la langue n'est pas définie, retourne 'fr' par défaut.

    Returns:
        str: Code de langue ('fr' ou 'en')

    Examples:
        >>> get_language_preference()
        'fr'
        >>> # Après avoir défini la langue en anglais
        >>> get_language_preference()
        'en'
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return config.get("language", "fr")
    except Exception:
        pass
    return "fr"


def set_language_preference(lang):
    """
    Définit la préférence de langue dans le fichier de configuration.

    Args:
        lang (str): Code de langue à définir ('fr' ou 'en')

    Returns:
        bool: True si la langue a été définie avec succès, False sinon

    Examples:
        >>> set_language_preference('en')
        True
        >>> set_language_preference('invalid')
        False
    """
    if lang not in ["fr", "en"]:
        return False

    try:
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)

        config["language"] = lang

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception:
        return False


def create_smtp_config_interactive():
    """
    Crée interactivement la configuration SMTP pour l'envoi d'emails.

    Cette fonction guide l'utilisateur pour configurer:
    - Le serveur SMTP
    - Le port
    - L'utilisateur
    - Le mot de passe
    - L'adresse email d'envoi
    - L'adresse email de réception

    La configuration est sauvegardée dans ~/.config/openstack-toolbox/smtp_config.ini

    Returns:
        bool: True si la configuration a été créée avec succès, False sinon

    Examples:
        >>> create_smtp_config_interactive()
        📧 Configuration SMTP
        Serveur SMTP [smtp.gmail.com]:
        Port SMTP [587]:
        Utilisateur SMTP: user@gmail.com
        Mot de passe SMTP: ****
        Email expéditeur [user@gmail.com]:
        Email destinataire: admin@company.com
        True
    """
    config = configparser.ConfigParser()
    config["SMTP"] = {
        "server": input("Serveur SMTP [smtp.gmail.com]: ").strip() or "smtp.gmail.com",
        "port": input("Port SMTP [587]: ").strip() or "587",
        "username": input("Utilisateur SMTP: ").strip(),
        "password": getpass.getpass("Mot de passe SMTP: ").strip(),
    }

    config["Email"] = {
        "from": input(f"Email expéditeur [{config['SMTP']['username']}]: ").strip()
        or config["SMTP"]["username"],
        "to": input("Email destinataire: ").strip(),
    }

    try:
        with open(SMTP_CONFIG_FILE, "w") as f:
            config.write(f)
        return True
    except Exception:
        return False


def load_smtp_config():
    """
    Charge la configuration SMTP depuis le fichier de configuration.

    Returns:
        dict: Configuration SMTP avec les clés suivantes:
            - server: Serveur SMTP
            - port: Port SMTP
            - username: Nom d'utilisateur
            - password: Mot de passe
            - from_email: Email expéditeur
            - to_email: Email destinataire
        None: Si la configuration n'existe pas ou est invalide

    Examples:
        >>> config = load_smtp_config()
        >>> if config:
        ...     print(f"Serveur: {config['server']}")
        ...     print(f"Port: {config['port']}")
        Serveur: smtp.gmail.com
        Port: 587
    """
    if not os.path.exists(SMTP_CONFIG_FILE):
        return None

    try:
        config = configparser.ConfigParser()
        config.read(SMTP_CONFIG_FILE)

        return {
            "server": config["SMTP"]["server"],
            "port": int(config["SMTP"]["port"]),
            "username": config["SMTP"]["username"],
            "password": config["SMTP"]["password"],
            "from_email": config["Email"]["from"],
            "to_email": config["Email"]["to"],
        }
    except Exception:
        return None


def load_openstack_credentials():
    """
    Charge les identifiants OpenStack depuis les variables d'environnement.
    """
    expected_vars = [
        "OS_AUTH_URL",
        "OS_PROJECT_NAME",
        "OS_USERNAME",
        "OS_PASSWORD",
        "OS_USER_DOMAIN_NAME",
    ]

    creds = {}
    missing_vars = []

    for var in expected_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            key = var.lower().replace("os_", "")
            creds[key] = value

    project_domain_name = os.getenv("OS_PROJECT_DOMAIN_NAME")
    project_domain_id = os.getenv("OS_PROJECT_DOMAIN_ID")

    if project_domain_name:
        creds["project_domain_name"] = project_domain_name
    elif project_domain_id:
        creds["project_domain_id"] = project_domain_id
    else:
        missing_vars.append("OS_PROJECT_DOMAIN_NAME/OS_PROJECT_DOMAIN_ID")

    if missing_vars:
        return None, missing_vars

    return creds, []
