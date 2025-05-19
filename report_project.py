#!/usr/bin/env python3

import subprocess
import sys
import importlib
import json
import os
import re
from collections import defaultdict

def print_header(header):
    print("\n" + "=" * 50)
    print(header.center(50))
    print("=" * 50 + "\n")

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

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
            raise RuntimeError("Aucun identifiant OpenStack disponible (.env ou secrets.json manquant)")

    return creds

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
        print(f"Aucun projet trouvé avec l'ID: {project_id}")

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

from dotenv import load_dotenv
from openstack import connection

# Connexion à OpenStack
creds = load_openstack_credentials()
conn = connection.Connection(**creds)

# Conversion ICU → EUR et CHF
ICU_CONVERSION = {
    "icu_to_eur": 1 / 55.5,  # 1 ICU = 0.018018 EUR
    "icu_to_chf": 1 / 50.0   # 1 ICU = 0.02 CHF
}
ICU_TO_EUR = ICU_CONVERSION["icu_to_eur"]
ICU_TO_CHF = ICU_CONVERSION["icu_to_chf"]

# Fonctions 
def load_billing(filepath="billing.json"):
    with open(filepath, "r") as f:
        return json.load(f)

def parse_flavor_name(flavor_name):
    # Parse flavor_name du style 'a2-ram4-disk50-perf1'
    match = re.match(r"[a-zA-Z]?(\d+)-ram(\d+)-disk(\d+)", flavor_name)
    if match:
        cpu = int(match.group(1))
        ram = int(match.group(2))
        disk = int(match.group(3))
        return cpu, ram, disk
    return 0, 0, 0

def load_usages(filepath="fetch_uses.json"):
    with open(filepath, "r") as f:
        data = json.load(f)

    if not data:
        print("⚠️  Aucune donnée reçue, fichier fetch_uses.json non généré.")
        return {}

    usages_by_project = {}

    for entry in data:
        project_id = entry.get("project_id", "inconnu")
        cpu = float(entry.get("cpu", 0))
        ram = float(entry.get("ram", 0))
        storage = float(entry.get("storage", 0))

        if project_id not in usages_by_project:
            usages_by_project[project_id] = {"cpu": 0, "ram": 0, "storage": 0}

        usages_by_project[project_id]["cpu"] += cpu
        usages_by_project[project_id]["ram"] += ram
        usages_by_project[project_id]["storage"] += storage

    return usages_by_project

def aggregate_costs(data):
    costs_by_project = {}
    
    for entry in data:
        project_id = entry.get("project_id") or entry.get("tenant_id") or "inconnu"
        rating = entry.get("rating", 0)  # en ICU
        if rating is None:
            continue
        costs_by_project.setdefault(project_id, 0)
        costs_by_project[project_id] += float(rating)
    
    return costs_by_project

# Affichage du rapport
def main():
    if not conn.authorize():
        print("Échec de la connexion à OpenStack")
        return

    print("Connexion réussie à OpenStack")
    project_id = input("Entrez l'ID du projet à analyser : ").strip()

    header = r"""
  ___                       _             _                       
 / _ \ _ __   ___ _ __  ___| |_ __ _  ___| | __                   
| | | | '_ \ / _ \ '_ \/ __| __/ _` |/ __| |/ /                   
| |_| | |_) |  __/ | | \__ \ || (_| | (__|   <                    
 \___/| .__/ \___|_| |_|___/\__\__,_|\___|_|\_\               _   
|  _ \|_|__ ___ (_) ___  ___| |_  |  _ \ ___ _ __   ___  _ __| |_ 
| |_) | '__/ _ \| |/ _ \/ __| __| | |_) / _ \ '_ \ / _ \| '__| __|
|  __/| | | (_) | |  __/ (__| |_  |  _ <  __/ |_) | (_) | |  | |_ 
|_|   |_|  \___// |\___|\___|\__| |_| \_\___| .__/ \___/|_|   \__|
              |__/                          |_|                   
      |_|                                                 
         Openstack SysAdmin Toolbox

"""
    print(header)

    # Demander la période à l'utilisateur UNE SEULE FOIS
    from datetime import datetime, timedelta, timezone

    def trim_to_minute(dt_str):
        # dt_str est du type '2025-05-19T13:00:00+00:00'
        # On veut '2025-05-19 13:00'
        # Corrige les formats invalides du type '2025-03:01' → '2025-03-01'
        dt = datetime.strptime(dt_str[:16].replace("T", " "), "%Y-%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M")

    def isoformat(dt):
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    default_start = isoformat(datetime.now(timezone.utc) - timedelta(hours=2))
    default_end = isoformat(datetime.now(timezone.utc))

    print("Entrez la période de facturation souhaitée (format: YYYY-MM-DD HH:MM)")
    start_input = input(f"Date de début [Défaut: {trim_to_minute(default_start)}]: ").strip() or trim_to_minute(default_start)
    end_input = input(f"Date de fin [Défaut: {trim_to_minute(default_end)}]: ").strip() or trim_to_minute(default_end)

    # Conversion en datetime
    start_dt = datetime.strptime(start_input, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end_input, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

    start_iso = isoformat(start_dt)
    end_iso = isoformat(end_dt)

    # Passer la période aux scripts
    subprocess.run([sys.executable, 'fetch_uses.py', '--start', start_iso, '--end', end_iso], check=True)
    subprocess.run([sys.executable, 'fetch_billing.py', '--start', start_iso, '--end', end_iso], check=True)

    # Charger usages et facturation
    usages = load_usages("fetch_uses.json")
    report = []
    data = load_billing()
    aggregated = aggregate_costs(data)

    print("-" * 65)
    print(f"{'Projet':36} | CPU    | RAM    | Stockage")
    print("-" * 65)
    if project_id in usages:
        usage = usages[project_id]
        print(f"{project_id:36} | {usage['cpu']:6.2f} | {usage['ram']:6.2f} | {usage['storage']:9.2f}")

    print(f"{'Projet':36} | EUR     | CHF")
    print("-" * 65)
    if project_id in aggregated:
        total_icu = aggregated[project_id]
        eur = total_icu * ICU_TO_EUR
        chf = total_icu * ICU_TO_CHF
        print(f"{project_id:36} | {eur:7.2f} | {chf:7.2f}")

    print("Rapport généré avec succès : /tmp/openstack_project_report.txt")

    if not report:
        print("⚠️  Aucun usage ou coût détecté pour ce projet.")

if __name__ == '__main__':
    main()