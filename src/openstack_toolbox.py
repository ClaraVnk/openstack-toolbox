#!/usr/bin/env python3

import argparse
import os

import tomli
from rich import print
from rich.prompt import Prompt

from .config import get_language_preference, set_language_preference

TRANSLATIONS = {
    "fr": {
        "welcome": "🎉 Bienvenue dans OpenStack Toolbox 🧰 v{}",
        "current_lang": "Langue actuelle : {}",
        "select_lang": "Sélectionnez une langue :",
        "invalid_choice": "❌ Choix invalide. Veuillez sélectionner 'fr' ou 'en'.",
        "lang_updated": "✅ Langue mise à jour avec succès : {}",
        "available_langs": "Langues disponibles :",
        "french": "Français",
        "english": "English",
        "available_commands": "🧰 Commandes disponibles (version {}) :",
        "config_option": "Configurer la langue (fr/en)",
        "usage": "Utilisation : openstack-toolbox [--config]",
    },
    "en": {
        "welcome": "🎉 Welcome to OpenStack Toolbox 🧰 v{}",
        "current_lang": "Current language: {}",
        "select_lang": "Select a language:",
        "invalid_choice": "❌ Invalid choice. Please select 'fr' or 'en'.",
        "lang_updated": "✅ Language successfully updated: {}",
        "available_langs": "Available languages:",
        "french": "French",
        "english": "English",
        "available_commands": "🧰 Available commands (version {}) :",
        "config_option": "Configure language (fr/en)",
        "usage": "Usage: openstack-toolbox [--config]",
    },
}


def get_version():
    pyproject_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
    pyproject_path = os.path.abspath(pyproject_path)

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)
        version = pyproject_data.get("project", {}).get("version", "unknown")
    except Exception:
        version = "unknown"
    return version


def get_commands(lang):
    commands = [
        (
            "openstack-summary",
            ("Génère un résumé global du projet" if lang == "fr" else "Generates a global project summary"),
        ),
        (
            "openstack-admin",
            (
                "Génère un résumé global de tous les projets (mode SysAdmin)"
                if lang == "fr"
                else "Generates a global summary of all projects (SysAdmin mode)"
            ),
        ),
        (
            "openstack-optimization",
            (
                "Identifie les ressources sous-utilisées dans la semaine"
                if lang == "fr"
                else "Identifies underutilized resources in the week"
            ),
        ),
        (
            "weekly-notification",
            (
                "Paramètre l'envoi d'un e-mail avec le résumé de la semaine"
                if lang == "fr"
                else "Configure weekly summary email sending"
            ),
        ),
        (
            "openstack-metrics-collector",
            ("Lance un exporter passif pour Prometheus" if lang == "fr" else "Starts a passive Prometheus exporter"),
        ),
        ("openstack-toolbox --config", TRANSLATIONS[lang]["config_option"]),
    ]
    return commands


def display_language_menu():
    """Affiche le menu de sélection de la langue"""
    lang = get_language_preference()
    version = get_version()
    print(f"\n{TRANSLATIONS[lang]['welcome'].format(version)}\n")
    print(f"{TRANSLATIONS[lang]['current_lang'].format(lang)}\n")
    print(f"{TRANSLATIONS[lang]['available_langs']}")
    print(f"fr - {TRANSLATIONS[lang]['french']}")
    print(f"en - {TRANSLATIONS[lang]['english']}\n")


def configure_language():
    """Configure la langue de l'application"""
    lang = get_language_preference()
    display_language_menu()

    while True:
        choice = Prompt.ask(TRANSLATIONS[lang]["select_lang"], choices=["fr", "en"])
        if choice in ["fr", "en"]:
            set_language_preference(choice)
            print(f"\n{TRANSLATIONS[choice]['lang_updated'].format(choice)}")
            break
        else:
            print(f"\n{TRANSLATIONS[lang]['invalid_choice']}")


def main():
    parser = argparse.ArgumentParser(description="OpenStack Toolbox")
    parser.add_argument("--config", action="store_true", help="Configure language settings")
    args = parser.parse_args()

    if args.config:
        configure_language()
        return

    version = get_version()
    lang = get_language_preference()

    header = r"""
  ___                       _             _
 / _ \ _ __   ___ _ __  ___| |_ __ _  ___| | __
| | | | '_ \ / _ \ '_ \/ __| __/ _` |/ __| |/ /
| |_| | |_) |  __/ | | \__ \ || (_| | (__|   <
 \___/| .__/ \___|_| |_|___/\__\__,_|\___|_|\_\
|_   _|_|   ___ | | |__   _____  __
  | |/ _ \ / _ \| | '_ \ / _ \ \/ /
  | | (_) | (_) | | |_) | (_) >  <
  |_|\___/ \___/|_|_.__/ \___/_/\_\
            By Loutre
"""

    print(header)
    print(f"\n[cyan]{TRANSLATIONS[lang]['available_commands'].format(version)}[/]")
    print(f"[dim]{TRANSLATIONS[lang]['usage']}[/]\n")

    for cmd, desc in get_commands(lang):
        print(f"  • [bold]{cmd}[/bold]" + " " * (30 - len(cmd)) + f"→ {desc}")


if __name__ == "__main__":
    main()
