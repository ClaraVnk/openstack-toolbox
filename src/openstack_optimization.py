#!/usr/bin/env python3

import subprocess
import sys
import importlib
import json
import os

# Fonction pour traduire le nom du flavor (copié depuis openstack_script.py)
def parse_flavor_name(name):
    """
    Parse un nom de flavor du type 'aX-ramY-diskZ-...' et retourne une chaîne lisible + les valeurs numériques.
    Exemple : 'a2-ram8-disk40' → ('2 vCPU / 8 Go RAM / 40 Go disque', 2, 8, 40)
    """
    try:
        parts = name.split('-')
        cpu_part = next((p for p in parts if p.startswith('a') and p[1:].isdigit()), None)
        ram_part = next((p for p in parts if p.startswith('ram') and p[3:].isdigit()), None)
        disk_part = next((p for p in parts if p.startswith('disk') and p[4:].isdigit()), None)

        cpu = int(cpu_part[1:]) if cpu_part else None
        ram = int(ram_part[3:]) if ram_part else None
        disk = int(disk_part[4:]) if disk_part else None

        human_readable = f"{cpu} CPU / {ram} Go RAM / {disk} Go disque"
        return human_readable, cpu, ram, disk
    except Exception as e:
        # En cas d'échec, retourne le nom original et None pour les valeurs numériques
        print(f"❌ Échec du parsing pour le flavor '{name}' : {str(e)}")
        return name, None, None, None

def run_script(script_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))  # = src/
    script_path = os.path.join(script_dir, script_name)

    result = subprocess.run([sys.executable, script_path], check=True)

def load_openstack_credentials():
    load_dotenv()  # essaie de charger depuis .env s’il existe

    creds = {
        "auth_url": os.getenv("OS_AUTH_URL"),
        "project_name": os.getenv("OS_PROJECT_NAME"),
        "username": os.getenv("OS_USERNAME"),
        "password": os.getenv("OS_PASSWORD"),
        "user_domain_name": os.getenv("OS_USER_DOMAIN_NAME"),
        "project_domain_name": os.getenv("OS_PROJECT_DOMAIN_NAME"),
    }

    # Si une des variables est absente, on essaie de charger depuis un fichier JSON
    if not all(creds.values()):
        try:
            with open("secrets.json") as f:
                creds = json.load(f)
        except FileNotFoundError:
            raise RuntimeError("❌ Aucun identifiant OpenStack disponible (.env ou secrets.json manquant)")

    return creds

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Vérifier et installer les dépendances manquantes
try:
    importlib.import_module('openstack')
except ImportError:
    print("⚙️ Installation du package openstack...")
    install_package('openstacksdk')

try:
    importlib.import_module('dotenv')
except ImportError:
    print("⚙️ Installation du package dotenv...")
    install_package('python-dotenv')

try:
    importlib.import_module('rich')
except ImportError:
    print("⚙️ Installation du package rich...")
    install_package('rich')

from dotenv import load_dotenv
from openstack import connection
from rich import print
from rich.console import Console
from rich.table import Table

console = Console()

# Connexion à OpenStack
creds = load_openstack_credentials()
conn = connection.Connection(**creds)

# Fonction pour récupérer les statuts des VMs via l'API OpenStack
def get_vm_statuses_from_cli():
    try:
        result = subprocess.run(
            ["openstack", "server", "list", "-f", "json"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print("❌ La commande `openstack server list` a échoué.")
            print("STDERR:", result.stderr)
            return []
        servers = json.loads(result.stdout)
        return [
            {
                "id": s["ID"],
                "name": s["Name"],
                "status": s["Status"],
                "project": s.get("Project ID", "inconnu")
            }
            for s in servers
        ]
    except Exception as e:
        print("❌ Erreur lors de l'appel à `openstack server list`:", e)
        return []

# Liste des statuts de VM à vérifier
def get_inactive_instances_from_cli():
    servers = get_vm_statuses_from_cli()
    inactive = [s for s in servers if s["status"].upper() != "ACTIVE"]
    return inactive

def get_unused_volumes():
    # Récupérer la liste des volumes
    volumes = conn.block_storage.volumes()

    unused_volumes = []
    for volume in volumes:
        # Vérifier si le volume est non utilisé (par exemple, non attaché à une instance)
        if not volume.attachments:
            unused_volumes.append(volume)

    return unused_volumes

def calculate_underutilized_costs():
    try:
        with open('weekly_billing.json', 'r') as f:
            billing_data = json.load(f)
    except FileNotFoundError:
        print("❌ Le fichier weekly_billing.json est introuvable.")
        billing_data = []
    except json.JSONDecodeError:
        print("❌ Erreur lors de la lecture du fichier weekly_billing.json : format JSON invalide.")
        billing_data = []

    ICU_to_CHF = 1 / 50
    ICU_to_EUR = 1 / 55.5

    underutilized_costs = {}
    # Parcours de la liste d'objets retournée par OpenStack
    for entry in billing_data:
        # Adapte ici les clés selon la structure exacte de chaque dict
        resource = entry.get("name") or entry.get("resource") or entry.get("ID") or entry.get("id")
        cost_icu = entry.get("rate:unit") or entry.get("ICU") or entry.get("icu") or entry.get("cost") or entry.get("rate:sum")
        # Si tu connais la clé exacte pour le coût ICU, remplace la ligne ci-dessus par entry["<clé>"]
        if resource is not None and cost_icu is not None:
            try:
                cost_icu = float(cost_icu)
            except Exception:
                continue
            cost_chf = cost_icu * ICU_to_CHF
            cost_eur = cost_icu * ICU_to_EUR
            underutilized_costs[resource] = {
                'ICU': cost_icu,
                'CHF': round(cost_chf, 2),
                'EUR': round(cost_eur, 2)
            }

    return underutilized_costs

def collect_and_analyze_data():
    inactive_instances = get_inactive_instances_from_cli()
    unused_volumes = get_unused_volumes()

    report_body = ""
    report_body += "="*60 + "\n"
    report_body += "RÉCAPITULATIF HEBDOMADAIRE DES RESSOURCES SOUS-UTILISÉES\n"
    report_body += "="*60 + "\n\n"

    report_body += "[INSTANCES INACTIVES]\n"
    if inactive_instances:
        table = Table(title="Instances inactives")
        table.add_column("ID", style="magenta")
        table.add_column("Nom", style="cyan")
        table.add_column("Statut", style="red")
        for instance in inactive_instances:
            table.add_row(instance["id"], instance["name"], instance["status"])
        console.print(table)
    else:
        report_body += "✅ Aucune instance inactive détectée.\n"
    report_body += "\n" + "-"*50 + "\n"

    report_body += "[VOLUMES NON UTILISÉS]\n"
    if unused_volumes:
        table = Table(title="Volumes non utilisés")
        table.add_column("ID", style="magenta")
        table.add_column("Nom", style="cyan")
        for volume in unused_volumes:
            table.add_row(volume.id, volume.name)
        console.print(table)
    else:
        report_body += "✅ Aucun volume inutilisé détecté.\n"
    report_body += "\n" + "-"*50 + "\n"

    report_body += "[COÛTS DES RESSOURCES SOUS-UTILISÉES]\n"
    underutilized_costs = calculate_underutilized_costs()
    if not underutilized_costs:
        report_body += "❌ Aucune donnée de facturation disponible (trop faibles ou non disponibles).\n"
    else:
        table = Table(title="Coûts des ressources sous-utilisées")
        table.add_column("Ressource", style="cyan")
        table.add_column("CHF", justify="right", style="green")
        table.add_column("EUR", justify="right", style="blue")
        for resource, costs in underutilized_costs.items():
            table.add_row(resource, f"{costs['CHF']} CHF", f"{costs['EUR']} EUR")
        console.print(table)
    report_body += "\n" + "-"*50 + "\n"
    
    report_body += "[TOTAL DES RESSOURCES CONSOMMÉES]\n"
    try:
        from openstack import connection
        from dotenv import load_dotenv

        creds = load_openstack_credentials()
        conn_summary = connection.Connection(**creds)
        instances = list(conn_summary.compute.servers())
        total_instances = len(instances)

        total_vcpus = 0
        total_ram_go = 0
        total_disk_go = 0

        for instance in instances:
            flavor_id = instance.flavor['id']
            _, cpu, ram, disk = parse_flavor_name(flavor_id)

            total_vcpus += cpu if cpu else 0
            total_ram_go += ram if ram else 0
            total_disk_go += disk if disk else 0

        report_body += f"  - Instances : {total_instances}\n"
        report_body += f"  - CPU : {total_vcpus}\n"
        report_body += f"  - RAM : {total_ram_go} Go\n"
        report_body += f"  - Disque : {total_disk_go} Go\n"
    except Exception as e:
        report_body += f"❌ Impossible de calculer le total des ressources consommées : {e}\n"
    report_body += "="*60 + "\n"

    return report_body

def main():
    # Test de connection à OpenStack
    if not conn.authorize():
        print("[bold red]❌ Échec de la connexion à OpenStack[/]")
        return
    
    # Afficher le message d'accueil
    print("\n[bold yellow]🎉 Bienvenue dans OpenStack Toolbox v1.3.1 🎉[/]")
    print("[cyan]Commandes disponibles :[/]")
    print("  • [bold]openstack_summary[/]        → Génère un résumé global du projet")
    print("  • [bold]openstack_optimization[/]   → Identifie les ressources sous-utilisées et propose un résumé de la semaine")
    print("  • [bold]openstack_weekly_notification[/]   → Paramètre l'envoi d'un e-mail avec le résumé de la semaine")

    header = r"""
  ___                       _             _               
 / _ \ _ __   ___ _ __  ___| |_ __ _  ___| | __           
| | | | '_ \ / _ \ '_ \/ __| __/ _` |/ __| |/ /           
| |_| | |_) |  __/ | | \__ \ || (_| | (__|   <            
 \___/| .__/ \___|_| |_|___/\__\__,_|\___|_|\_\           
 / _ \|_|__ | |_(_)_ __ ___ (_)______ _| |_(_) ___  _ __  
| | | | '_ \| __| | '_ ` _ \| |_  / _` | __| |/ _ \| '_ \ 
| |_| | |_) | |_| | | | | | | |/ / (_| | |_| | (_) | | | |
 \___/| .__/ \__|_|_| |_| |_|_/___\__,_|\__|_|\___/|_| |_|
      |_|                                                 
         By Loutre

"""
    print(header)

    # Exécuter le script weekly_billing.py pour récupérer les données de facturation
    run_script("weekly_billing.py")

    # Collecter et analyser les données
    report_body = collect_and_analyze_data()

    # Enregistrer le rapport dans un fichier
    with open('/tmp/openstack_optimization_report.txt', 'w') as f:
        f.write(report_body)

    print("[bold green]🎉 Rapport généré avec succès :[/] /tmp/openstack_optimization_report.txt")
    
    # Afficher le rapport
    print(report_body)

if __name__ == '__main__':
    main()