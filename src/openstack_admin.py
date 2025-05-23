#!/usr/bin/env python3

import sys
import importlib
import os
import tomli
from datetime import datetime
from rich import print
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from openstack import connection
from dotenv import load_dotenv
from importlib.metadata import version, PackageNotFoundError

console = Console()

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

# Connexion à OpenStack
creds = load_openstack_credentials()
conn = connection.Connection(**creds)

# Fonction header
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
        print("🚫 Aucune image trouvée.")
        return
    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Visibilité", style="green")
    for image in all_images:
        table.add_row(image.id, image.name, image.visibility)
    console.print(table)

# Lister les instances
def list_instances(conn):
    print_header("LISTE DES INSTANCES")
    # Récupérer les instances
    instances = list(conn.compute.servers())
    # Récupérer toutes les flavors disponibles
    flavors = {flavor.id: flavor for flavor in conn.compute.flavors()}

    if not instances:
        print("🚫 Aucune instance trouvée.")
        return
    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Flavor ID", style="green")
    table.add_column("Uptime", justify="right")
    for instance in instances:
        flavor_id = instance.flavor['id']
        created_at = datetime.strptime(instance.created_at, "%Y-%m-%dT%H:%M:%SZ")
        uptime = datetime.now() - created_at
        uptime_str = str(uptime).split('.')[0]
        table.add_row(instance.id, instance.name, flavor_id, uptime_str)
    console.print(table)

# Lister les snapshots
def list_snapshots(conn):
    print_header("LISTE DES SNAPSHOTS")
    # Récupérer les snapshots
    snapshots = list(conn.block_storage.snapshots())

    if not snapshots:
        print("🚫 Aucun snapshot trouvé.")
        return
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
    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Taille (Go)", justify="right")
    table.add_column("Type", style="green")
    table.add_column("Attaché", style="blue")
    table.add_column("Snapshot associé", style="magenta")
    for volume in volumes:
        attached = "Oui" if volume.attachments else "Non"
        snapshot_id = volume.snapshot_id if volume.snapshot_id else 'Aucun'
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
    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("IP", style="cyan")
    table.add_column("Statut", style="green")
    for ip in floating_ips:
        table.add_row(ip.id, ip.floating_ip_address, ip.status)
    console.print(table)

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

# Lister les containers
def list_containers(conn):
    print_header("LISTE DES CONTAINERS")
    # Récupérer les containers
    containers = list(conn.object_store.containers())

    if not containers:
        print("🚫 Aucun container trouvé.")
        return
    table = Table(title="")
    table.add_column("Nom", style="cyan")
    table.add_column("Taille totale", justify="right", style="magenta")
    for container in containers:
        size_formatted = format_size(container.bytes)
        table.add_row(container.name, size_formatted)
    console.print(table)

def main():
    version = get_version()
    print(f"\n[bold yellow]🎉 Bienvenue dans OpenStack Toolbox 🧰 v{version} 🎉[/]")

    header = r"""
  ___                       _             _    
 / _ \ _ __   ___ _ __  ___| |_ __ _  ___| | __
| | | | '_ \ / _ \ '_ \/ __| __/ _` |/ __| |/ /
| |_| | |_) |  __/ | | \__ \ || (_| | (__|   < 
 \___/| .__/_\___|_| |_|___/\__\__,_|\___|_|\_\
   / \|_|__| |_ __ ___ (_)_ __                 
  / _ \ / _` | '_ ` _ \| | '_ \                
 / ___ \ (_| | | | | | | | | | |               
/_/   \_\__,_|_| |_| |_|_|_| |_|               
            
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

    # Demander à l'utilisateur de saisir l'ID du projet
    project_id = input("Veuillez entrer l'ID du projet: ")
    get_project_details(conn, project_id)

    # Lister les ressources
    list_images(conn)
    list_instances(conn)
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