#!/usr/bin/env python3

import configparser
import getpass
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import SMTPConfigError
from .security import SecureConfig

CONFIG_DIR = os.path.expanduser("~/.config/openstack-toolbox")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SMTP_CONFIG_FILE = os.path.join(CONFIG_DIR, "smtp_config.ini")

# Assurez-vous que le répertoire de configuration existe
os.makedirs(CONFIG_DIR, exist_ok=True)


def get_language_preference() -> str:
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
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("language", "fr")
    except (OSError, IOError, json.JSONDecodeError):
        # Log error but return default
        pass
    return "fr"


def set_language_preference(lang: str) -> bool:
    """
    Définit la préférence de langue dans le fichier de configuration.

    Args:
        lang: Code de langue à définir ('fr' ou 'en')

    Returns:
        True si la langue a été définie avec succès, False sinon

    Examples:
        >>> set_language_preference('en')
        True
        >>> set_language_preference('invalid')
        False
    """
    if lang not in ["fr", "en"]:
        return False

    try:
        config: Dict[str, str] = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)

        config["language"] = lang

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        return True
    except (OSError, IOError, json.JSONDecodeError):
        return False


def create_smtp_config_interactive() -> bool:
    """
    Crée interactivement la configuration SMTP pour l'envoi d'emails.

    Cette fonction guide l'utilisateur pour configurer:
    - Le serveur SMTP
    - Le port
    - L'utilisateur
    - Le mot de passe (chiffré)
    - L'adresse email d'envoi
    - L'adresse email de réception

    La configuration est sauvegardée dans ~/.config/openstack-toolbox/smtp_config.ini
    Le mot de passe est chiffré pour plus de sécurité.

    Returns:
        True si la configuration a été créée avec succès, False sinon

    Raises:
        SMTPConfigError: Si la configuration ne peut pas être sauvegardée

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

    server = input("Serveur SMTP [smtp.gmail.com]: ").strip() or "smtp.gmail.com"
    while True:
        port_input = input("Port SMTP [587]: ").strip() or "587"
        try:
            port_val = int(port_input)
            if 1 <= port_val <= 65535:
                port = port_input
                break
        except ValueError:
            pass
        print("Port invalide. Entrez un nombre entre 1 et 65535.")
    username = input("Utilisateur SMTP: ").strip()
    password = getpass.getpass("Mot de passe SMTP: ").strip()

    # Encrypt password for security
    secure = SecureConfig(Path(CONFIG_DIR))
    encrypted_password = secure.encrypt(password)

    config["SMTP"] = {
        "server": server,
        "port": port,
        "username": username,
        "password": encrypted_password,
        "encrypted": "true",  # Flag to indicate password is encrypted
    }

    from_email = input(f"Email expéditeur [{username}]: ").strip() or username
    to_email = input("Email destinataire: ").strip()

    config["Email"] = {
        "from": from_email,
        "to": to_email,
    }

    try:
        fd = os.open(SMTP_CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            config.write(f)
        return True
    except (OSError, IOError) as e:
        raise SMTPConfigError(f"Failed to save SMTP configuration: {e}") from e


def load_smtp_config() -> Optional[Dict[str, Any]]:
    """
    Charge la configuration SMTP depuis le fichier de configuration.

    Returns:
        Configuration SMTP avec les clés suivantes:
            - server: Serveur SMTP
            - port: Port SMTP
            - username: Nom d'utilisateur
            - password: Mot de passe (déchiffré)
            - from_email: Email expéditeur
            - to_email: Email destinataire
        None si la configuration n'existe pas ou est invalide

    Raises:
        SMTPConfigError: Si la configuration existe mais est invalide

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
        config.read(SMTP_CONFIG_FILE, encoding="utf-8")

        password = config["SMTP"]["password"]
        is_encrypted = config["SMTP"].get("encrypted", "false") == "true"

        # Decrypt password if it's encrypted
        if is_encrypted:
            secure = SecureConfig(Path(CONFIG_DIR))
            password = secure.decrypt(password)

        return {
            "server": config["SMTP"]["server"],
            "port": int(config["SMTP"]["port"]),
            "username": config["SMTP"]["username"],
            "password": password,
            "from_email": config["Email"]["from"],
            "to_email": config["Email"]["to"],
        }
    except (KeyError, ValueError, configparser.Error) as e:
        raise SMTPConfigError(f"Invalid SMTP configuration file: {e}") from e
    except Exception as e:
        raise SMTPConfigError(f"Failed to load SMTP configuration: {e}") from e


def load_openstack_credentials() -> Tuple[Optional[Dict[str, str]], List[str]]:
    """
    Charge les identifiants OpenStack depuis les variables d'environnement.

    Returns:
        Tuple contenant:
            - Dict des credentials si toutes les variables sont présentes, None sinon
            - Liste des variables manquantes

    Raises:
        CredentialsError: Si les variables critiques sont manquantes

    Examples:
        >>> creds, missing = load_openstack_credentials()
        >>> if creds:
        ...     print(f"Auth URL: {creds['auth_url']}")
    """
    expected_vars: List[str] = [
        "OS_AUTH_URL",
        "OS_PROJECT_NAME",
        "OS_USERNAME",
        "OS_PASSWORD",
        "OS_USER_DOMAIN_NAME",
    ]

    creds: Dict[str, str] = {}
    missing_vars: List[str] = []

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
