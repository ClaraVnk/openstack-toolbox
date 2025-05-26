#!/usr/bin/env python3

import os
import tomli
from rich import print
from .config import get_language_preference

def get_version():
    pyproject_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
    pyproject_path = os.path.abspath(pyproject_path)

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)
        version = pyproject_data.get("project", {}).get("version", "unknown")
    except Exception as e:
        version = "unknown"
    return version

def get_commands(lang):
    if lang == "fr":
        return [
            ("openstack-summary", "Génère un résumé global du projet"),
            ("openstack-admin", "Génère un résumé global de tous les projets (mode SysAdmin)"),
            ("openstack-optimization", "Identifie les ressources sous-utilisées dans la semaine"),
            ("weekly-notification", "Paramètre l'envoi d'un e-mail avec le résumé de la semaine"),
            ("openstack-metrics-collector", "Lance un exporter passif pour Prometheus")
        ]
    else:
        return [
            ("openstack-summary", "Generates a global project summary"),
            ("openstack-admin", "Generates a global summary of all projects (SysAdmin mode)"),
            ("openstack-optimization", "Identifies underutilized resources in the week"),
            ("weekly-notification", "Configure weekly summary email sending"),
            ("openstack-metrics-collector", "Starts a passive Prometheus exporter")
        ]

def main():
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
    if lang == "fr":
        print(f"\n[cyan]🧰 Commandes disponibles (version {version}):[/]")
    else:
        print(f"\n[cyan]🧰 Available commands (version {version}):[/]")

    for cmd, desc in get_commands(lang):
        print(f"  • [bold]{cmd}[/]" + " " * (30 - len(cmd)) + f"→ {desc}")

if __name__ == '__main__':
    main()