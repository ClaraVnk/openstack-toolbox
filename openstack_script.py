#!/usr/bin/env python3

import subprocess
import sys
import importlib

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

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

import openstack
import json

# Se connecter à OpenStackv 
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

# Lister les images privées et partagées
def list_images(conn):
    # Récupérer les images privées et les convertir en liste
    private_images = list(conn.image.images(visibility='private'))

    # Récupérer les images partagées et les convertir en liste
    shared_images = list(conn.image.images(visibility='shared'))

    # Combiner les images privées et partagées
    all_images = private_images + shared_images

    # Afficher les images
    print("Liste des images privées et partagées :")
    for image in all_images:
        print(f"ID: {image.id}, Nom: {image.name}, Visibilité: {image.visibility}")

list_images(conn)

# Lister les instances
def list_instances(conn):
    # Récupérer les instances
    instances = list(conn.compute.servers())

    # Récupérer toutes les flavors disponibles
    flavors = {flavor.id: flavor for flavor in conn.compute.flavors()}

    # Extraire les informations des instances avec les détails des flavors
    instances_info = []
    for instance in instances:
        flavor_id = instance.flavor['id']
        flavor = flavors.get(flavor_id)
        if flavor:
            flavor_name = flavor.name
        else:
            flavor_name = 'Unknown Flavor'
        instances_info.append({
            'id': instance.id,
            'name': instance.name,
            'flavor_id': flavor_id,
            'flavor_name': flavor_name
        })

    # Convertir en JSON pour une meilleure lisibilité
    instances_json = json.dumps(instances_info, indent=4)

    # Afficher les instances avec les détails des flavors
    print("Liste des instances avec les détails des flavors :")
    print(instances_json)

list_instances(conn)

# Lister les snapshots
print("\nListe des snapshots :")
for snapshot in conn.block_storage.snapshots():
    print(snapshot)

# Lister les volumes sous forme d'arborescence
print("\nArborescence des volumes :")

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

# Afficher l'arborescence
print_tree(tree)