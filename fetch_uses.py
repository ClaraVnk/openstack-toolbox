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
        # DEBUUUUUUUG
        print("Premier élément JSON reçu :", data[0] if data else "Aucune donnée")

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

        for entry in data[0].get("Resources", []):
            project_id = entry.get("desc", {}).get("project_id", "inconnu")
            flavor = entry.get("desc", {}).get("flavor_name", "")
            volume = float(entry.get("volume", 1.0))

            cpu, ram, disk = parse_flavor_name(flavor)

            usages[project_id]["cpu"] += cpu * volume
            usages[project_id]["ram"] += ram * volume
            usages[project_id]["storage"] += disk * volume

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