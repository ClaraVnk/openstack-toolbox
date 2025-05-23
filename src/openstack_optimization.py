#!/usr/bin/env python3

import sys
import importlib
import json
import os
import tomli
import subprocess
from openstack import connection
from dotenv import load_dotenv
from rich import print
from rich.console import Console
from rich.table import Table
try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version, PackageNotFoundError

# Ajoute le dossier src au path pour les imports locaux
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fonction pour récupérer la version
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

# Fonction pour générer le fichier de billing
def generate_billing():
    try:
        from . import weekly_billing
        weekly_billing.main()
    except Exception as e:
        return f"❌ Erreur lors de l'exécution de weekly_billing.py : {e}"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    billing_path = os.path.join(script_dir, "weekly_billing.json")

    try:
        with open(billing_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"❌ Le fichier weekly_billing.json est introuvable à l'emplacement attendu : {billing_path}"

# Fonction pour traduire le nom du flavor 
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

# Fonction pour charger les identifiants OpenStack
def load_openstack_credentials():
    load_dotenv()  # Charge .env si présent

    expected_vars = [
        "OS_AUTH_URL",
        "OS_PROJECT_NAME",
        "OS_USERNAME",
        "OS_PASSWORD",
        "OS_USER_DOMAIN_NAME",
    ]

    creds = {}
    missing_vars = []

    # Récupération des variables obligatoires
    for var in expected_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            key = var.lower().replace("os_", "")
            creds[key] = value

    # Récupération du project_domain_name ou project_domain_id
    project_domain_name = os.getenv("OS_PROJECT_DOMAIN_NAME")
    project_domain_id = os.getenv("OS_PROJECT_DOMAIN_ID")

    if project_domain_name:
        creds["project_domain_name"] = project_domain_name
    elif project_domain_id:
        creds["project_domain_id"] = project_domain_id
    else:
        missing_vars.append("OS_PROJECT_DOMAIN_NAME/OS_PROJECT_DOMAIN_ID")

    if missing_vars:
        print(f"[bold red]❌ Variables OpenStack manquantes : {', '.join(missing_vars)}[/]")
        return None

    return creds

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
        instances = list(conn.compute.servers())
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
    toolbox_version = get_version()
    print(f"\n[bold yellow]🎉 Bienvenue dans OpenStack Toolbox 🧰 v{toolbox_version} 🎉[/]")
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
    
    # Test des credentials
    creds = load_openstack_credentials()
    if not creds:
        print("[bold red]❌ Impossible de charger les identifiants OpenStack. Vérifiez votre configuration.[/]")
        return

    conn = connection.Connection(**creds)
    if not conn.authorize():
        print("[bold red]❌ Échec de la connexion à OpenStack[/]")
        return

    # Générer le fichier de billing
    billing_text = generate_billing()
    if "introuvable" in billing_text:
        print("[bold red]❌ Échec de la récupération du billing[/]")
        billing_data = []
    else:
        try:
            billing_data = json.loads(billing_text)
        except json.JSONDecodeError as e:
            print("[bold red]❌ Erreur de parsing du fichier billing[/]")
            billing_data = []

    # Collecter et analyser les données
    report_body = collect_and_analyze_data()

    # Enregistrer le rapport dans un fichier
    with open('openstack_optimization_report.txt', 'w') as f:
        f.write(report_body)

    print("[bold green]🎉 Rapport généré avec succès :[/] openstack_optimization_report.txt")
    
    # Afficher le rapport
    print(report_body)

if __name__ == '__main__':
    main()