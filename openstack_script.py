#!/usr/bin/env python3

import subprocess
import sys
import importlib
import json
import openstack
from datetime import datetime, timedelta

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# La spéciale Infomaniak
def check_cloudkitty_version():
    try:
        # Commande pour lister les services OpenStack
        command = ["openstack", "service", "list", "-c", "Name", "-c", "Type", "-f", "json"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Analyser la sortie JSON
        services = json.loads(result.stdout)

        # Rechercher le service CloudKitty
        for service in services:
            if service.get('Type') == 'rating':
                print(f"CloudKitty est installé avec le nom de service: {service.get('Name')}")
                return True
        print("CloudKitty n'est pas installé ou n'est pas trouvé dans la liste des services.")
        return False
    except subprocess.CalledProcessError as e:
        print("Erreur lors de l'exécution de la commande OpenStack CLI")
        print(e.stderr)
        return False
    except json.JSONDecodeError:
        print("Erreur dans le format de sortie de la commande OpenStack")
        return False

def get_cloudkitty_version():
    try:
        # Commande pour obtenir la version de CloudKitty
        cmd = ["cloudkitty", "--version"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Extraire la version de la sortie
        # Exemple de sortie: "CloudKitty 13.0.0"
        version_output = result.stdout.strip()
        version = version_output.split()[-1]  # Prend le dernier élément (numéro de version)
        
        print(f"Version de CloudKitty détectée: {version}")
        return version
    except subprocess.CalledProcessError as e:
        print("Impossible d'obtenir la version de CloudKitty")
        print(e.stderr if e.stderr else "Commande échouée sans message d'erreur")
        return None

def determine_cloudkitty_client_version(cloudkitty_version):
    if not cloudkitty_version:
        return None
        
    if cloudkitty_version.startswith('13.'):
        return 'cloudkittyclient==4.1.0'
    elif cloudkitty_version.startswith('20.'):
        return 'cloudkittyclient==5.0.0'
    else:
        print(f"Version de CloudKitty non reconnue: {cloudkitty_version}")
        return None

def main():
    # Vérifier si CloudKitty est installé
    if not check_cloudkitty_version():
        return
    
    # Obtenir la version de CloudKitty
    cloudkitty_version = get_cloudkitty_version()
    if not cloudkitty_version:
        return

    # Déterminer la version du client à installer
    client_version = determine_cloudkitty_client_version(cloudkitty_version)
    if client_version:
        print(f"Installation du client CloudKitty version: {client_version}")
        install_package(client_version)
    else:
        print("Version de CloudKitty non reconnue, installation annulée.")

if __name__ == "__main__":
    main()

# Vérifier et installer les dépendances manquantes
try:
    importlib.import_module('openstack')
except ImportError:
    print("Installation du package openstack...")
    install_package('openstacksdk')

try:
    importlib.import_module('dotenv')
except ImportError:
    print("Installation du package dotenv...")
    install_package('python-dotenv')

# Se connecter à OpenStack
from dotenv import load_dotenv
import os

load_dotenv()

auth_url = os.getenv("OS_AUTH_URL")
project_name = os.getenv("OS_PROJECT_NAME")
username = os.getenv("OS_USERNAME")
password = os.getenv("OS_PASSWORD")
user_domain_name = os.getenv("OS_USER_DOMAIN_NAME")
project_domain_name = os.getenv("OS_PROJECT_DOMAIN_NAME")

# Créer la connexion OpenStack
conn = openstack.connect(
    auth_url=auth_url,
    project_name=project_name,
    username=username,
    password=password,
    user_domain_name=user_domain_name,
    project_domain_name=project_domain_name,
)

# Vérifier la connexion
if conn.authorize():
    print("Connexion réussie à OpenStack")
else:
    print("Échec de la connexion à OpenStack")
    exit(1)

# Fonction pour afficher les en-têtes
def print_header(header):
    print("\n" + "=" * 50)
    print(header.center(50))
    print("=" * 50 + "\n")

def get_billing_data(start_time, end_time):
    # Commande pour récupérer les données de facturation
    command = [
        "openstack", "rating", "dataframes", "get",
        "-b", start_time,
        "-e", end_time,
        "-c", "Resources",
        "-f", "json"
    ]

    # Exécuter la commande et récupérer la sortie
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("Erreur lors de la récupération des données de facturation")
        print(result.stderr)
        return None

    return json.loads(result.stdout)

def calculate_instance_cost(billing_data, icu_to_currency):
    # Calculer le coût total en utilisant les données de facturation
    total_icu = sum(float(resource['rating']) for resource in billing_data['Resources'])
    total_cost = total_icu / icu_to_currency

    return total_cost

def main():
    # Définir la période de temps pour la récupération des données
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)

    # Formater les dates pour la commande OpenStack
    start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    # Récupérer les données de facturation
    billing_data = get_billing_data(start_time_str, end_time_str)
    if not billing_data:
        return

    # Taux de conversion ICU à la devise souhaitée (par exemple, CHF)
    icu_to_chf = 50  # 50 ICUs = 1 CHF
    icu_to_euro = 55.5  # 55.5 ICUs = 1 Euro

    # Calculer le coût total
    total_cost = calculate_instance_cost(billing_data, icu_to_chf, icu_to_euro)
    if total_cost is None:
        print("Erreur lors du calcul du coût total")
        return

if __name__ == "__main__":
    main()

# Lister les images privées et partagées
def list_images(conn):
    print_header("LISTE DES IMAGES UTILISEES")
    # Récupérer les images privées et les convertir en liste
    private_images = list(conn.image.images(visibility='private'))
    # Récupérer les images partagées et les convertir en liste
    shared_images = list(conn.image.images(visibility='shared'))
    # Combiner les images privées et partagées
    all_images = private_images + shared_images

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<36} {'Visibilité':<20}")
    print("-" * 96) 
    for image in all_images:
        print(f"{image.id:<36} {image.name:<36} {image.visibility:<20}")

list_images(conn)

# Lister les instances
def list_instances(conn):
    print_header("LISTE DES INSTANCES")
    # Récupérer les instances
    instances = list(conn.compute.servers())
    # Récupérer toutes les flavors disponibles
    flavors = {flavor.id: flavor for flavor in conn.compute.flavors()}

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<20} {'Flavor ID':<20} {'Uptime':<20} {'Coût total':<20}")
    print("-" * 116)
    for instance in instances:
        flavor_id = instance.flavor['id']
        # Convertir la date de création en objet datetime
        created_at = datetime.strptime(instance.created_at, "%Y-%m-%dT%H:%M:%SZ")
        # Calculer l'uptime
        uptime = datetime.now() - created_at
        # Formater l'uptime en jours, heures, minutes, secondes
        uptime_str = str(uptime).split('.')[0]  # Supprimer les microsecondes
        # Calculer le coût total
        total_cost = calculate_instance_cost(flavor_id, uptime)
        print(f"{instance.id:<36} {instance.name:<20} {flavor_id:<20} {uptime_str:<20} {total_cost:<20.2f}")

list_instances(conn)

# Lister les snapshots
def list_snapshots(conn):
    print_header("LISTE DES SNAPSHOTS")
    # Récupérer les snapshots
    snapshots = list(conn.block_storage.snapshots())

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<20} {'Volume associé':<20}")
    print("-" * 96)
    for snapshot in snapshots:
        print(f"{snapshot.id:<36} {snapshot.name:<20} {snapshot.volume_id:<20}")
    
list_snapshots(conn)

# Lister les backups
def list_backups(conn):
    print_header("LISTE DES BACKUPS")
    # Récupérer les backups
    backups = list(conn.block_storage.backups())

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<20} {'Volume associé':<20}")
    print("-" * 96)
    for backup in backups:
        print(f"{backup.id:<36} {backup.name:<20} {backup.volume_id:<20}")

list_backups(conn)

# Lister les volumes 
def list_volumes(conn):
    print_header("LISTE DES VOLUMES")
    # Récupérer les volumes
    volumes = list(conn.block_storage.volumes())

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<20} {'Taille (Go)':<20} {'Type':<20} {'Attaché':<20} {'Snapshot associé':<20}")
    print("-" * 116)
    for volume in volumes:
        attached = "Oui" if volume.attachments else "Non"
        # Remplacer None par une chaîne vide pour snapshot_id
        snapshot_id = volume.snapshot_id if volume.snapshot_id else 'Aucun'
        print(f"{volume.id:<36} {volume.name:<20} {volume.size:<20} {volume.volume_type:<20} {attached:<20} {snapshot_id:<20}")

list_volumes(conn)

# Lister les volumes sous forme d'arborescence
print_header("ARBORESCENCE DES VOLUMES")
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
def print_tree(tree):
    for instance, volumes in tree.items():
        print(f"Instance: {instance}")
        for volume in volumes:
            print(f"  Volume: {volume}")

# Obtenir l'arborescence des volumes montés
tree = mounted_volumes(conn)
print_tree(tree)

# Lister les IP flottantes
def list_floating_ips(conn):
    print_header("LISTE DES FLOATING IPs")
    # Récupérer les adresses IP flottantes
    floating_ips = list(conn.network.ips())

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'IP':<20} {'Statut':<20}")
    print("-" * 96)
    for ip in floating_ips:
        print(f"{ip.id:<36} {ip.floating_ip_address:<20} {ip.status:<20}")

list_floating_ips(conn)

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

    # Afficher les en-têtes du tableau
    print(f"{'Nom':<20} {'Taille totale':<20}")
    print("-" * 40)
    for container in containers:
        size_formatted = format_size(container.bytes)
        print(f"{container.name:<20} {size_formatted:<20}")

list_containers(conn)