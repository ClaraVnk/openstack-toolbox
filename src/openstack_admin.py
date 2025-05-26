#!/usr/bin/env python3

import sys
import os
import tomli
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich import print
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from openstack import connection
from dotenv import load_dotenv
from src.config import get_language_preference
from src.utils import format_size, print_header

# Dictionnaire des traductions
TRANSLATIONS = {
    "fr": {
        "welcome": "🎉 Bienvenue dans OpenStack Toolbox 🧰 v{} 🎉",
        "missing_vars": "❌ Variables OpenStack manquantes : {}",
        "connection_error": "❌ Impossible de charger les identifiants OpenStack. Vérifiez votre configuration.",
        "auth_error": "❌ Échec de la connexion à OpenStack",
        "enter_project_id": "Veuillez entrer l'ID du projet: ",
        "project_details": "DÉTAILS DU PROJET AVEC ID: {}",
        "project_id": "ID: {}",
        "project_name": "Nom: {}",
        "project_description": "Description: {}",
        "project_domain": "Domaine: {}",
        "project_active": "Actif: {}",
        "yes": "Oui",
        "no": "Non",
        "no_project": "❌ Aucun projet trouvé avec l'ID: {}",
        "no_images": "🚫 Aucune image trouvée.",
        "no_instances": "🚫 Aucune instance trouvée.",
        "no_snapshots": "🚫 Aucun snapshot trouvé.",
        "no_backups": "🚫 Aucun backup trouvé.",
        "no_volumes": "🚫 Aucun volume trouvé.",
        "no_floating_ips": "🚫 Aucune IP flottante trouvée.",
        "no_containers": "🚫 Aucun container trouvé.",
        "mounted_volumes": "📦 Volumes montés par instance",
        "no_volume_mounted": "🚫 Aucun volume",
        "none": "Aucun",
        "resources_header": "LISTE DES RESSOURCES",
        "name_column": "Nom",
        "details_column": "Détails",
        "images_header": "LISTE DES IMAGES UTILISEES",
        "instances_header": "LISTE DES INSTANCES",
        "snapshots_header": "LISTE DES SNAPSHOTS",
        "backups_header": "LISTE DES BACKUPS",
        "volumes_header": "LISTE DES VOLUMES",
        "volumes_tree_header": "ARBORESCENCE DES VOLUMES",
        "floating_ips_header": "LISTE DES FLOATING IPs",
        "containers_header": "LISTE DES CONTAINERS"
    },
    "en": {
        "welcome": "🎉 Welcome to OpenStack Toolbox 🧰 v{} 🎉",
        "missing_vars": "❌ Missing OpenStack variables: {}",
        "connection_error": "❌ Unable to load OpenStack credentials. Please check your configuration.",
        "auth_error": "❌ Failed to connect to OpenStack",
        "enter_project_id": "Please enter the project ID: ",
        "project_details": "PROJECT DETAILS WITH ID: {}",
        "project_id": "ID: {}",
        "project_name": "Name: {}",
        "project_description": "Description: {}",
        "project_domain": "Domain: {}",
        "project_active": "Active: {}",
        "yes": "Yes",
        "no": "No",
        "no_project": "❌ No project found with ID: {}",
        "no_images": "🚫 No images found.",
        "no_instances": "🚫 No instances found.",
        "no_snapshots": "🚫 No snapshots found.",
        "no_backups": "🚫 No backups found.",
        "no_volumes": "🚫 No volumes found.",
        "no_floating_ips": "🚫 No floating IPs found.",
        "no_containers": "🚫 No containers found.",
        "mounted_volumes": "📦 Volumes mounted by instance",
        "no_volume_mounted": "🚫 No volume",
        "none": "None",
        "resources_header": "LIST OF RESOURCES",
        "name_column": "Name",
        "details_column": "Details",
        "images_header": "LIST OF USED IMAGES",
        "instances_header": "LIST OF INSTANCES",
        "snapshots_header": "LIST OF SNAPSHOTS",
        "backups_header": "LIST OF BACKUPS",
        "volumes_header": "LIST OF VOLUMES",
        "volumes_tree_header": "VOLUMES TREE VIEW",
        "floating_ips_header": "LIST OF FLOATING IPs",
        "containers_header": "LIST OF CONTAINERS"
    }
}

console = Console()

def get_version():
    """
    Récupère la version du projet depuis le fichier pyproject.toml.
    
    Returns:
        str: Version du projet ou "unknown" si non trouvée
        
    Examples:
        >>> get_version()
        '1.2.0'
    """
    pyproject_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
    pyproject_path = os.path.abspath(pyproject_path)

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)
        version = pyproject_data.get("project", {}).get("version", "unknown")
    except Exception as e:
        version = "unknown"
    return version

def load_openstack_credentials():
    """
    Charge les identifiants OpenStack depuis les variables d'environnement.
    
    Les variables requises sont :
    - OS_AUTH_URL
    - OS_PROJECT_NAME
    - OS_USERNAME
    - OS_PASSWORD
    - OS_USER_DOMAIN_NAME
    - OS_PROJECT_DOMAIN_NAME ou OS_PROJECT_DOMAIN_ID
    
    Returns:
        dict: Dictionnaire des identifiants OpenStack ou None si manquants
        
    Examples:
        >>> creds = load_openstack_credentials()
        >>> if creds:
        ...     conn = connection.Connection(**creds)
    """
    lang = get_language_preference()
    load_dotenv()

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
        print(f"[bold red]{TRANSLATIONS[lang]['missing_vars'].format(', '.join(missing_vars))}[/bold red]")
        return None

    return creds

def get_project_details(conn, project_id):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]['project_details'].format(project_id))
    project = conn.identity.get_project(project_id)

    if project:
        print(TRANSLATIONS[lang]['project_id'].format(project.id))
        print(TRANSLATIONS[lang]['project_name'].format(project.name))
        print(TRANSLATIONS[lang]['project_description'].format(project.description))
        print(TRANSLATIONS[lang]['project_domain'].format(project.domain_id))
        is_active = TRANSLATIONS[lang]['yes'] if project.is_enabled else TRANSLATIONS[lang]['no']
        print(TRANSLATIONS[lang]['project_active'].format(is_active))
    else:
        print(f"[bold red]{TRANSLATIONS[lang]['no_project'].format(project_id)}[/bold red]")

def list_images(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["images_header"])
    private_images = list(conn.image.images(visibility='private'))
    shared_images = list(conn.image.images(visibility='shared'))
    all_images = private_images + shared_images

    if not all_images:
        print(TRANSLATIONS[lang]["no_images"])
        return

    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Visibilité", style="green")
    for image in all_images:
        table.add_row(image.id, image.name, image.visibility)
    console.print(table)

def list_instances(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["instances_header"])
    instances = list(conn.compute.servers())

    if not instances:
        print(TRANSLATIONS[lang]["no_instances"])
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

def list_snapshots(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["snapshots_header"])
    snapshots = list(conn.block_storage.snapshots())

    if not snapshots:
        print(TRANSLATIONS[lang]["no_snapshots"])
        return

    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Volume associé", style="green")
    for snapshot in snapshots:
        table.add_row(snapshot.id, snapshot.name, snapshot.volume_id)
    console.print(table)

def list_backups(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["backups_header"])
    backups = list(conn.block_storage.backups())

    if not backups:
        print(TRANSLATIONS[lang]["no_backups"])
        return

    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Volume associé", style="green")
    for backup in backups:
        table.add_row(backup.id, backup.name, backup.volume_id)
    console.print(table)

def list_volumes(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["volumes_header"])
    volumes = list(conn.block_storage.volumes())

    if not volumes:
        print(TRANSLATIONS[lang]["no_volumes"])
        return

    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Taille (Go)", justify="right")
    table.add_column("Type", style="green")
    table.add_column("Attaché", style="blue")
    table.add_column("Snapshot associé", style="magenta")
    for volume in volumes:
        attached = TRANSLATIONS[lang]["yes"] if volume.attachments else TRANSLATIONS[lang]["no"]
        snapshot_id = volume.snapshot_id if volume.snapshot_id else TRANSLATIONS[lang]["none"]
        table.add_row(volume.id, volume.name, str(volume.size), volume.volume_type, attached, snapshot_id)
    console.print(table)

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

def print_tree(tree_data):
    lang = get_language_preference()
    tree = Tree(TRANSLATIONS[lang]["mounted_volumes"])
    for instance, volumes in tree_data.items():
        instance_branch = tree.add(f"🖥️ {instance}")
        if volumes:
            for volume in volumes:
                instance_branch.add(f"💾 {volume}")
        else:
            instance_branch.add(TRANSLATIONS[lang]["no_volume_mounted"])
    console.print(tree)

def list_floating_ips(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["floating_ips_header"])
    floating_ips = list(conn.network.ips())

    if not floating_ips:
        print(TRANSLATIONS[lang]["no_floating_ips"])
        return

    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("IP", style="cyan")
    table.add_column("Statut", style="green")
    for ip in floating_ips:
        table.add_row(ip.id, ip.floating_ip_address, ip.status)
    console.print(table)

def list_containers(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["containers_header"])
    containers = list(conn.object_store.containers())

    if not containers:
        print(TRANSLATIONS[lang]["no_containers"])
        return

    table = Table(title="")
    table.add_column("Nom", style="cyan")
    table.add_column("Taille totale", justify="right", style="magenta")
    for container in containers:
        size_formatted = format_size(container.bytes)
        table.add_row(container.name, size_formatted)
    console.print(table)

def process_resource_parallel(resource_type, resource, conn):
    """
    Traite une ressource OpenStack de manière parallèle.
    
    Args:
        resource_type (str): Type de ressource ("instance", "volume", "image")
        resource (obj): Objet ressource OpenStack
        conn (Connection): Connexion OpenStack
        
    Returns:
        dict: Informations formatées sur la ressource ou None si erreur
        
    Examples:
        >>> with ThreadPoolExecutor(max_workers=10) as executor:
        ...     future = executor.submit(process_resource_parallel,
        ...         "instance", instance, conn)
        ...     result = future.result()
        >>> if result:
        ...     print(f"Name: {result['name']}, Type: {result['type']}")
    """
    lang = get_language_preference()
    try:
        if resource_type == "instance":
            flavor = conn.compute.find_flavor(resource.flavor["id"])
            flavor_name = flavor.name if flavor else TRANSLATIONS[lang]["unknown"]
            created_at = datetime.strptime(resource.created_at, "%Y-%m-%dT%H:%M:%SZ")
            uptime = datetime.now() - created_at
            return {
                "id": resource.id,
                "name": resource.name,
                "type": "Instance",
                "details": f"Flavor: {flavor_name}, Uptime: {str(uptime).split('.')[0]}"
            }
        elif resource_type == "volume":
            size = format_size(resource.size * 1024 * 1024 * 1024)
            return {
                "id": resource.id,
                "name": resource.name,
                "type": "Volume",
                "details": f"Size: {size}, Status: {resource.status}"
            }
        elif resource_type == "image":
            size = format_size(resource.size) if resource.size else TRANSLATIONS[lang]["unknown"]
            return {
                "id": resource.id,
                "name": resource.name,
                "type": "Image",
                "details": f"Size: {size}, Status: {resource.status}"
            }
    except Exception as e:
        print(f"[red]Erreur lors du traitement de la ressource {resource.id}: {str(e)}[/red]")
        return None

def list_all_resources(conn):
    """
    Liste toutes les ressources OpenStack avec parallélisation.
    
    Cette fonction collecte et affiche de manière efficace :
    - Les instances
    - Les volumes
    - Les images
    
    Args:
        conn (Connection): Connexion OpenStack
        
    Examples:
        >>> conn = connection.Connection(**creds)
        >>> list_all_resources(conn)
        ==========================================
                  LISTE DES RESSOURCES                  
        ==========================================
        Type       ID                                  Nom                  Détails
        Instance   123-456                            web-server           Flavor: a2-ram4-disk50, Uptime: 15 days
        Volume     789-012                            data-vol            Size: 100 Go, Status: in-use
        Image      345-678                            ubuntu-20.04        Size: 2.5 Go, Status: active
    """
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["resources_header"])

    resources_to_process = []
    
    # Collecte des ressources
    instances = list(conn.compute.servers())
    volumes = list(conn.block_storage.volumes())
    images = list(conn.image.images())
    
    for instance in instances:
        resources_to_process.append(("instance", instance))
    for volume in volumes:
        resources_to_process.append(("volume", volume))
    for image in images:
        resources_to_process.append(("image", image))

    # Traitement parallèle des ressources
    processed_resources = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(process_resource_parallel, res_type, resource, conn)
            for res_type, resource in resources_to_process
        ]
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    processed_resources.append(result)
            except Exception as e:
                print(f"[red]Erreur lors du traitement d'une ressource : {str(e)}[/red]")

    # Affichage des résultats
    table = Table(title="")
    table.add_column("Type", style="cyan")
    table.add_column("ID", style="magenta")
    table.add_column(TRANSLATIONS[lang]["name_column"], style="green")
    table.add_column(TRANSLATIONS[lang]["details_column"], style="white")

    for resource in sorted(processed_resources, key=lambda x: (x["type"], x["name"])):
        table.add_row(
            resource["type"],
            resource["id"],
            resource["name"],
            resource["details"]
        )

    console = Console()
    console.print(table)

def main():
    lang = get_language_preference()
    version = get_version()
    print(f"[yellow bold]{TRANSLATIONS[lang]['welcome'].format(version)}[/yellow bold]")

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
        print(f"[bold red]{TRANSLATIONS[lang]['connection_error']}[/bold red]")
        return

    conn = connection.Connection(**creds)
    if not conn.authorize():
        print(f"[bold red]{TRANSLATIONS[lang]['auth_error']}[/bold red]")
        return

    # Demander à l'utilisateur de saisir l'ID du projet
    project_id = input(TRANSLATIONS[lang]["enter_project_id"])
    get_project_details(conn, project_id)

    # Lister les ressources
    list_images(conn)
    list_instances(conn)
    list_snapshots(conn)
    list_backups(conn)
    list_volumes(conn)
    print_header(TRANSLATIONS[lang]["volumes_tree_header"])
    tree = mounted_volumes(conn)
    print_tree(tree)
    list_floating_ips(conn)
    list_containers(conn)
    list_all_resources(conn)

if __name__ == "__main__":
    main()