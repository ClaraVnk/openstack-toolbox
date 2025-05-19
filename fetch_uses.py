#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime, timedelta, timezone
import argparse
import sys
import importlib

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    importlib.import_module('gnocchiclient')
except ImportError:
    print("Installation du package Gnocchi...")
    install_package('gnocchiclient')

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

def get_active_instances_from_gnocchi(start_iso, end_iso):
    print("📡 Interrogation de Gnocchi pour récupérer l’historique des VM actives...")
    try:
        cmd = [
            "openstack", "metric", "resource", "list",
            "--type", "instance",
            "-f", "json"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("⚠️ Impossible de récupérer la liste des ressources Gnocchi.")
            print("STDERR:", result.stderr)
            return set()

        resources = json.loads(result.stdout)
        active_ids = set()

        for res in resources:
            resource_id = res["id"]
            metric_cmd = [
                "openstack", "metric", "measures", "show",
                res["metrics"]["cpu"],
                "--start", start_iso,
                "--end", end_iso,
                "-f", "json"
            ]
            metric_result = subprocess.run(metric_cmd, capture_output=True, text=True)
            if metric_result.returncode != 0:
                continue

            measures = json.loads(metric_result.stdout)
            if measures:
                active_ids.add(resource_id)
        return active_ids
    except Exception as e:
        print("❌ Erreur lors de l’accès à Gnocchi :", e)
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
            if volume > 0:
                usages[project_id]["cpu"] += cpu * volume
                usages[project_id]["ram"] += ram * volume
                usages[project_id]["storage"] += disk * volume
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

        with open("fetch_uses.json", "w") as f:
            json.dump(usage_list, f, indent=2)
    else:
        print("❌ Échec de la récupération des données")
        print("STDERR:", result.stderr)
        print("STDOUT:", result.stdout)

if __name__ == "__main__":
    main()