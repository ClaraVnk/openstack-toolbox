#!/usr/bin/env python3

from importlib.metadata import version, PackageNotFoundError

def get_version():
    try:
        return version("openstack-toolbox")
    except PackageNotFoundError:
        return "unknown"

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

    print (header)
    print (f"\n[cyan]🧰 Commandes disponibles (version {version}:[/]")
    print ("  • [bold]openstack-summary[/]      → Génère un résumé global du projet")
    print(f"  • [bold]openstack-admin[/]        → Génère un résumé global de tous les projets (mode SysAdmin)")
    print ("  • [bold]openstack-optimization[/] → Identifie les ressources sous-utilisées dans la semaine")
    print ("  • [bold]weekly-notification[/]    → Paramètre l'envoi d'un e-mail avec le résumé de la semaine")

if __name__ == '__main__':
    main()