#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime, timedelta, timezone
import argparse
import sys
import importlib
import os
import requests

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    importlib.import_module('dotenv')
except ImportError:
    print("Installation du package dotenv...")
    install_package('python-dotenv')

from dotenv import load_dotenv

# Charger les variables d'environnement dès le début
load_dotenv()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    return parser.parse_args()

def trim_to_minute(dt_str):
      # Extrait "YYYY-MM-DD HH:MM" de la chaîne ISO complète
      # Exemple d'entrée : "2025-05-18T14:00:57+00:00"
      # On remplace "T" par espace puis on coupe après les 16 premiers caractères
      return dt_str.replace("T", " ")[:16]

def input_with_default(prompt, default):
    s = input(f"{prompt} [Défaut: {default}]: ")
    return s.strip() or default

def isoformat(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

def get_active_instance_ids():
    try:
        result = subprocess.run(
            ["openstack", "server", "list", "-f", "json"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print("⚠️ Impossible de récupérer les statuts des VMs.")
            print("STDERR:", result.stderr)
            return set()
        servers = json.loads(result.stdout)
        return {s["ID"] for s in servers if s.get("Status", "").upper() == "ACTIVE"}
    except Exception as e:
        print("⚠️ Erreur lors de l'appel à `openstack server list`:", e)
        return set()

def get_keystone_token():
    auth_url = os.environ.get("OS_AUTH_URL")
    username = os.environ.get("OS_USERNAME")
    password = os.environ.get("OS_PASSWORD")
    project_name = os.environ.get("OS_PROJECT_NAME")
    user_domain = os.environ.get("OS_USER_DOMAIN_NAME", "Default")
    project_domain = os.environ.get("OS_PROJECT_DOMAIN_NAME", "Default")

    if not all([auth_url, username, password, project_name]):
        print("❌ Variables d'environnement Keystone incomplètes.")
        return None, None

    payload = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "name": username,
                        "domain": {"name": user_domain},
                        "password": password
                    }
                }
            },
            "scope": {
                "project": {
                    "name": project_name,
                    "domain": {"name": project_domain}
                }
            }
        }
    }

    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(f"{auth_url}/auth/tokens", headers=headers, json=payload)
        resp.raise_for_status()
        token = resp.headers.get("X-Subject-Token")
        return token, resp.json()
    except Exception as e:
        print("❌ Authentification Keystone échouée :", e)
        return None, None

def get_active_instances_from_gnocchi(start_iso, end_iso):

    token, _ = get_keystone_token()
    if not token:
        return set()
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }

    try:
        # Sélection dynamique du endpoint Gnocchi selon la région
        dc_env = os.environ.get("OS_REGION_NAME", "")
        if "dc3" in dc_env:
            GNOCCHI_ENDPOINT = "https://api.pub1.infomaniak.cloud/metric"
        elif "dc4" in dc_env:
            GNOCCHI_ENDPOINT = "https://api.pub2.infomaniak.cloud/metric"
        else:
            GNOCCHI_ENDPOINT = os.environ.get("GNOCCHI_ENDPOINT", "https://api.pub2.infomaniak.cloud/metric")

        # Récupérer toutes les ressources de type "instance"
        url = f"{GNOCCHI_ENDPOINT}/v1/resource/instance"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("⚠️ Erreur lors de l'interrogation de /resource/instance :", response.text)
            return set()

        resources = response.json()
        active_ids = set()

        for res in resources:
            cpu_metric = res.get("metrics", {}).get("cpu")
            if not cpu_metric:
                continue

            # Requête sur les mesures de la métrique CPU
            measures_url = f"{GNOCCHI_ENDPOINT}/v1/metric/{cpu_metric}/measures"
            params = {"start": start_iso, "end": end_iso}
            measure_resp = requests.get(measures_url, headers=headers, params=params)

            if measure_resp.status_code == 200 and measure_resp.json():
                active_ids.add(res["original_resource_id"])

        return active_ids
    except Exception as e:
        print("❌ Erreur lors de l’accès à l’API Gnocchi :", e)
        return set()

def main():
    args = parse_args()
    if args.start and args.end:
        start_iso = args.start
        end_iso = args.end
        print(f"Période reçue pour les usages: {start_iso} → {end_iso}")
    else:
        default_start = isoformat(datetime.now(timezone.utc) - timedelta(hours=2))
        default_end = isoformat(datetime.now(timezone.utc))
        print("Entrez la période souhaitée (format: YYYY-MM-DD HH:MM)")
        start_input = input_with_default("Date de début", trim_to_minute(default_start))
        end_input = input_with_default("Date de fin", trim_to_minute(default_end))
        start_dt = datetime.strptime(start_input, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_input, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        start_iso = isoformat(start_dt)
        end_iso = isoformat(end_dt)
        print(f"Période choisie: {start_iso} → {end_iso}")

    active_ids = get_active_instances_from_gnocchi(start_iso, end_iso)

    # Construire la commande openstack
    cmd = [
        "openstack", "rating", "dataframes", "get",
        "-b", start_iso,
        "-e", end_iso,
        "-c", "Resources",
        "-f", "json"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        data = json.loads(result.stdout)

        if not data:
            print("⚠️  Aucune donnée reçue, fichier fetch_uses.json non généré.")
            return

        import re
        from collections import defaultdict

        def parse_flavor_name(flavor_name):
            match = re.match(r"[a-zA-Z]?(\d+)-ram(\d+)-disk(\d+)", flavor_name)
            if match:
                cpu = int(match.group(1))
                ram = int(match.group(2))
                disk = int(match.group(3))
                return cpu, ram, disk
            return 0, 0, 0

        usages = defaultdict(lambda: {"cpu": 0, "ram": 0, "storage": 0})
        counts = defaultdict(int)

        if isinstance(data, dict):
            resources = data.get("Resources", [])
        else:
            resources = data[0].get("Resources", []) if data else []

        # Cumul des ressources consommées sur la période (CPU/Go/h * heures d'utilisation)
        for entry in resources:
            desc = entry.get("desc", {})
            instance_id = desc.get("id")
            if not instance_id or instance_id not in active_ids:
                continue
            project_id = desc.get("project_id", "inconnu")
            flavor = desc.get("flavor_name", "")
            volume = float(entry.get("volume", 1.0))
            cpu, ram, disk = parse_flavor_name(flavor)
            interval_hours = 5 / 60  # 5 minutes exprimées en heures
            if volume > 0:
                usages[project_id]["cpu"] += cpu * interval_hours
                usages[project_id]["ram"] += ram * interval_hours
                usages[project_id]["storage"] += disk * interval_hours
                counts[project_id] += 1

        # Convertir en liste pour l'export JSON
        usage_list = []
        for project_id, values in usages.items():
            usage_list.append({
                "project_id": project_id,
                "cpu": values["cpu"],
                "ram": values["ram"],
                "storage": values["storage"]
            })

        print("\nContenu de fetch_uses.json en préparation :")
        for usage in usage_list:
            print(f"- Projet {usage['project_id']}: CPU={usage['cpu']:.2f}, RAM={usage['ram']:.2f}, Storage={usage['storage']:.2f}")

        with open("fetch_uses.json", "w") as f:
            json.dump(usage_list, f, indent=2)
    else:
        print("❌ Échec de la récupération des données")
        print("STDERR:", result.stderr)
        print("STDOUT:", result.stdout)

if __name__ == "__main__":
    main()