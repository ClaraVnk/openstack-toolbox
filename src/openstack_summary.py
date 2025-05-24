#!/usr/bin/env python3

import sys
import importlib
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
import tomli
from importlib.metadata import version, PackageNotFoundError
from openstack import connection
from dotenv import load_dotenv
from rich import print
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

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
def isoformat(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

# Ajout des fonctions auxiliaires
def trim_to_minute(dt_str):
    return dt_str.replace("T", " ")[:16]

def input_with_default(prompt, default):
    s = input(f"{prompt} [Défaut: {default}]: ")
    return s.strip() or default

def generate_billing():
    try:
        # Dates par défaut : 2 dernières heures UTC
        default_start_dt = datetime.now(timezone.utc) - timedelta(hours=2)
        default_end_dt = datetime.now(timezone.utc)

        print("Entrez la période de facturation souhaitée (format: YYYY-MM-DD HH:MM), appuyez sur Entrée pour la valeur par défaut.")

        start_input = input_with_default("Date de début", trim_to_minute(isoformat(default_start_dt)))
        end_input = input_with_default("Date de fin", trim_to_minute(isoformat(default_end_dt)))

        # Parsing des dates saisies
        start_dt = datetime.strptime(start_input, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_input, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

        start_iso = isoformat(start_dt)
        end_iso = isoformat(end_dt)

        print(f"\n🗓️ Période de facturation sélectionnée : {start_iso} → {end_iso}\n")

        cmd = [
            "openstack", "rating", "dataframes", "get",
            "-b", start_iso,
            "-e", end_iso,
            "-c", "Resources",
            "-f", "json"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        else:
            return f"❌ Échec de la récupération des données : {result.stderr.strip()}"

    except Exception as e:
        return f"❌ Exception lors de la récupération du billing : {e}"

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

# Fonction pour afficher les en-têtes
def print_header(header):
    print("\n" + "=" * 50)
    print(f"[bold yellow]{header.center(50)}[/]")
    print("=" * 50 + "\n")

# Fonction pour obtenir les détails d'un projet spécifique
def get_project_details(conn, project_id):
    print_header(f"DÉTAILS DU PROJET AVEC ID: {project_id}")
    project = conn.identity.get_project(project_id)

    if project:
        print(f"ID: {project.id}")
        print(f"Nom: {project.name}")
        print(f"Description: {project.description}")
        print(f"Domaine: {project.domain_id}")
        print(f"Actif: {'Oui' if project.is_enabled else 'Non'}")
    else:
        print(f"[bold red]❌ Aucun projet trouvé avec l'ID:[/] {project_id}")

# Fonction pour obtenir les détails d'une instance
def get_billing_data_from_file(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

# Fonction pour calculer le coût d'une instance
def calculate_instance_cost(billing_data, instance_id=None, icu_to_chf=50, icu_to_euro=55.5):
    if not billing_data:
        return 0.0, 0.0

    total_icu = 0.0

    for group in billing_data:
        resources = group.get("Resources", [])
        for resource in resources:
            desc = resource.get("desc", {})
            resource_id = desc.get("id")
            if instance_id and resource_id != instance_id:
                continue  # ignorer les autres

            try:
                price = float(resource.get("rating", 0))
                total_icu += price
            except (TypeError, ValueError):
                continue

    cost_chf = total_icu / icu_to_chf
    cost_euro = total_icu / icu_to_euro

    return cost_chf, cost_euro

# Fonction pour formater la taille
def format_size(size_bytes):
    # Définir les unités et leurs seuils
    units = [
        ('To', 1000000000000),
        ('Go', 1000000000),
        ('Mo', 1000000),
        ('Ko', 1000)
    ]

    # Parcourir les unités pour trouver la plus appropriée
    for unit, threshold in units:
        if size_bytes >= threshold:
            size = size_bytes / threshold
            return f"{size:.2f} {unit}"
    return f"{size_bytes} octets"

# Lister les images privées et partagées
def list_images(conn):
    print_header("LISTE DES IMAGES UTILISEES")
    # Récupérer les images privées et les convertir en liste
    private_images = list(conn.image.images(visibility='private'))
    # Récupérer les images partagées et les convertir en liste
    shared_images = list(conn.image.images(visibility='shared'))
    # Combiner les images privées et partagées
    all_images = private_images + shared_images

    if not all_images:
        print("🚫 Aucune image privée ou partagée trouvée.")
        return

    # Affichage avec rich.Table
    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Visibilité", style="green")
    for image in all_images:
        table.add_row(image.id, image.name, image.visibility)
    console.print(table)

# Lister les instances
def list_instances(conn, billing_data):
    print_header("LISTE DES INSTANCES")
    if not billing_data:
        print("❌ Aucune donnée de facturation disponible (indisponible ou trop faible) — les coûts affichés seront à 0.\n")

    # Récupérer les instances
    instances = list(conn.compute.servers())  

    if not instances:
        print("🚫 Aucune instance trouvée.")
        return

    # Taux de conversion ICU vers monnaies
    icu_to_chf = 50  # Taux de conversion ICU vers CHF
    icu_to_euro = 55.5  # Taux de conversion ICU vers EUR

    # Calculer le coût total des ressources consommées
    total_cost_chf = 0.0
    total_cost_euro = 0.0
    for instance in instances:
        cost_chf, cost_euro = calculate_instance_cost(billing_data, instance_id=instance.id, icu_to_chf=icu_to_chf, icu_to_euro=icu_to_euro)
        total_cost_chf += cost_chf
        total_cost_euro += cost_euro
    
    # Calculer le coût horaire moyen global à partir des données
    rate_values = []
    for group in billing_data:
        for resource in group.get("Resources", []):
            rate = resource.get("rate_value")
            if rate is not None:
                try:
                    rate_values.append(float(rate))
                except ValueError:
                    continue

    if rate_values:
        avg_rate_icu = sum(rate_values) / len(rate_values)
        avg_rate_eur = avg_rate_icu / icu_to_euro
        avg_rate_chf = avg_rate_icu / icu_to_chf

    # Initialiser les totaux
    total_vcpus = 0
    total_ram_go = 0
    total_disk_go = 0

    table = Table(title="")

    table.add_column("État", justify="center", style="bold")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Flavor ID", style="green")
    table.add_column("Uptime", justify="right")
    table.add_column("Coût (CHF)", justify="right")
    table.add_column("Coût (EUR)", justify="right")

    for instance in instances:
        try:
            flavor_id = instance.flavor['id']
            _, cpu, ram, disk = parse_flavor_name(flavor_id)

            total_vcpus += cpu if cpu else 0
            total_ram_go += ram if ram else 0
            total_disk_go += disk if disk else 0

            created_at = datetime.strptime(instance.created_at, "%Y-%m-%dT%H:%M:%SZ")
            uptime = datetime.now() - created_at
            uptime_str = str(uptime).split('.')[0]

            cost_chf, cost_euro = calculate_instance_cost(billing_data, instance_id=instance.id)
            state = instance.status.lower()
            emoji = "🟢" if state == "active" else "🔴"

            table.add_row(emoji, instance.id, instance.name, flavor_id, uptime_str, f"{cost_chf:.2f}", f"{cost_euro:.2f}")
        except Exception as e:
            print(f"❌ Erreur lors du traitement de l'instance '{instance.name}' : {str(e)}")
            continue

    console.print(table)

    # 4. Afficher le total
    print(f"\n📊 Total des ressources consommées : {total_vcpus} CPU, {total_ram_go} Go de RAM, {total_disk_go} Go de stockage")

    # Afficher le coût total des ressources consommées
    print(f"\n💰 Coût total des ressources consommées : {total_cost_chf:.2f} CHF, {total_cost_euro:.2f} EUR")

    if rate_values:
        print(f"\n💸 Coût horaire moyen : {avg_rate_chf:.5f} CHF, {avg_rate_eur:.5f} EUR")
    else:
        print("\n💸 Coût horaire moyen : Données insuffisantes")

# Lister les snapshots
def list_snapshots(conn):
    print_header("LISTE DES SNAPSHOTS")
    # Récupérer les snapshots
    snapshots = list(conn.block_storage.snapshots())

    if not snapshots:
        print("🚫 Aucun snapshot trouvé.")
        return

    # Affichage avec rich.Table
    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Volume associé", style="green")
    for snapshot in snapshots:
        table.add_row(snapshot.id, snapshot.name, snapshot.volume_id)
    console.print(table)

# Lister les backups
def list_backups(conn):
    print_header("LISTE DES BACKUPS")
    # Récupérer les backups
    backups = list(conn.block_storage.backups())

    if not backups:
        print("🚫 Aucun backup trouvé.")
        return

    # Affichage avec rich.Table
    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Volume associé", style="green")
    for backup in backups:
        table.add_row(backup.id, backup.name, backup.volume_id)
    console.print(table)

# Lister les volumes 
def list_volumes(conn):
    print_header("LISTE DES VOLUMES")
    # Récupérer les volumes
    volumes = list(conn.block_storage.volumes())

    if not volumes:
        print("🚫 Aucun volume trouvé.")
        return

    # Affichage avec rich.Table
    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Taille", justify="right")
    table.add_column("Type", style="green")
    table.add_column("Attaché", justify="center")
    table.add_column("Snapshot", style="blue")
    for volume in volumes:
        attached = "Oui" if volume.attachments else "Non"
        snapshot_id = volume.snapshot_id[:6] if volume.snapshot_id else 'Aucun'
        table.add_row(volume.id, volume.name, str(volume.size), volume.volume_type, attached, snapshot_id)
    console.print(table)

# Récupérer les volumes attachés aux instances
def mounted_volumes(conn):
    instances = conn.compute.servers()
    volumes = conn.block_storage.volumes()
    instance_volumes = {}

    for volume in volumes:
        if volume.attachments:
            for attachment in volume.attachments:
                instance_id = attachment['server_id']
                if instance_id not in instance_volumes:
                    instance_volumes[instance_id] = []
                instance_volumes[instance_id].append(volume)

    tree = {}
    for instance in instances:
        instance_id = instance.id
        instance_name = instance.name
        if instance_id in instance_volumes:
            tree[instance_name] = [volume.name for volume in instance_volumes[instance_id]]
        else:
            tree[instance_name] = []

    return tree

# Afficher l'arborescence
def print_tree(tree_data):
    tree = Tree("📦 Volumes montés par instance")
    for instance, volumes in tree_data.items():
        instance_branch = tree.add(f"🖥️ {instance}")
        if volumes:
            for volume in volumes:
                instance_branch.add(f"💾 {volume}")
        else:
            instance_branch.add("🚫 Aucun volume")
    console.print(tree)

# Lister les IP flottantes
def list_floating_ips(conn):
    print_header("LISTE DES FLOATING IPs")
    # Récupérer les adresses IP flottantes
    floating_ips = list(conn.network.ips())

    if not floating_ips:
        print("🚫 Aucune IP flottante trouvée.")
        return

    # Affichage avec rich.Table
    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("IP", style="cyan")
    table.add_column("Statut", style="green")
    for ip in floating_ips:
        table.add_row(ip.id, ip.floating_ip_address, ip.status)
    console.print(table)

# Lister les containers
def list_containers(conn):
    print_header("LISTE DES CONTAINERS")
    # Récupérer les containers
    containers = list(conn.object_store.containers())

    if not containers:
        print("🚫 Aucun container trouvé.")
        return

    # Affichage avec rich.Table
    table = Table(title="")
    table.add_column("Nom", style="cyan")
    table.add_column("Taille totale", justify="right", style="magenta")
    for container in containers:
        size_formatted = format_size(container.bytes)
        table.add_row(container.name, size_formatted)
    console.print(table)

# Fonction principale
def main():
    toolbox_version = get_version()
    print(f"\n[bold yellow]🎉 Bienvenue dans OpenStack Toolbox 🧰 v{toolbox_version} 🎉[/]")

    header = r"""
  ___                       _             _       
 / _ \ _ __   ___ _ __  ___| |_ __ _  ___| | __   
| | | | '_ \ / _ \ '_ \/ __| __/ _` |/ __| |/ /   
| |_| | |_) |  __/ | | \__ \ || (_| | (__|   <    
 \___/| .__/ \___|_| |_|___/\__\__,_|\___|_|\_\   
/ ___||_|  _ _ __ ___  _ __ ___   __ _ _ __ _   _ 
\___ \| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |
 ___) | |_| | | | | | | | | | | | (_| | |  | |_| |
|____/ \__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |
                                            |___/ 
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

    # Lister les ressources
    list_images(conn)
    list_instances(conn, billing_data)
    list_snapshots(conn)
    list_backups(conn)
    list_volumes(conn)
    print_header("ARBORESCENCE DES VOLUMES")
    tree = mounted_volumes(conn)
    print_tree(tree)
    list_floating_ips(conn)
    list_containers(conn)

if __name__ == "__main__":
    main()