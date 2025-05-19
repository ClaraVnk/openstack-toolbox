#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime, timedelta, timezone
import argparse

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

def main():
    args = parse_args()
    start_iso = args.start
    end_iso = args.end
    print(f"Période reçue pour les usages: {start_iso} → {end_iso}")

    # Conversion en datetime
    start_dt = datetime.strptime(start_iso, "%Y-%m-%dT%H:%M:%S+00:00").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end_iso, "%Y-%m-%dT%H:%M:%S+00:00").replace(tzinfo=timezone.utc)

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
        usages = []
        for entry in data:
            usages.append({
                "project_id": entry.get("project_id"),
                "project_name": entry.get("project_name"),
                "cpu_hours": entry.get("cpu_hours", 0),
                "ram_gb_hours": entry.get("ram_gb_hours", 0),
                "storage_gb_hours": entry.get("storage_gb_hours", 0),
                "network_gb": entry.get("network_gb", 0)
            })
        with open("fetch_uses.json", "w") as f:
            json.dump(usages, f, indent=2)
    else:
        print("❌ Échec de la récupération des données")
        print("STDERR:", result.stderr)
        print("STDOUT:", result.stdout)

if __name__ == "__main__":
    main()