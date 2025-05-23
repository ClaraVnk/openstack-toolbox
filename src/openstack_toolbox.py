#!/usr/bin/env python3

import os
import tomllib  # Python 3.11+

def get_version():
    pyproject_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
    pyproject_path = os.path.abspath(pyproject_path)

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
        version = pyproject_data.get("project", {}).get("version", "unknown")
    except Exception as e:
        version = "unknown"
    return version

def main():
    version = get_version()

    header = """
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
    print(f"\n[cyan]🧰 Commandes disponibles (version {version}:[/]")
    print("  • [bold]openstack-summary[/]      → Génère un résumé global du projet")
    print(f"  • [bold]openstack-admin[/]       → Génère un résumé global de tous les projets (mode SysAdmin)")
    print("  • [bold]openstack-optimization[/] → Identifie les ressources sous-utilisées dans la semaine")
    print("  • [bold]weekly-notification[/]    → Paramètre l'envoi d'un e-mail avec le résumé de la semaine")

if __name__ == '__main__':
    main()