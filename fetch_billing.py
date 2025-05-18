#!/usr/bin/env python3
import subprocess
from datetime import datetime, timedelta, timezone

def isoformat(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

def input_with_default(prompt, default):
    s = input(f"{prompt} [Défaut: {default}]: ")
    return s.strip() or default

def main():
    default_start = isoformat(datetime.now(timezone.utc) - timedelta(hours=2))
    default_end = isoformat(datetime.now(timezone.utc))

    print("Entrez la période de facturation souhaitée (format: YYYY-MM-DD HH:MM)")
    start_input = input_with_default("Date de début", default_start.replace("T", " ")[:-6])
    end_input = input_with_default("Date de fin", default_end.replace("T", " ")[:-6])

    # Conversion en datetime
    start_dt = datetime.strptime(start_input, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end_input, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

    start_iso = isoformat(start_dt)
    end_iso = isoformat(end_dt)

    print(f"Période choisie: {start_iso} → {end_iso}")

    # Construire la commande openstack
    cmd = [
        "openstack", "rating", "dataframes", "get",
        "-b", start_iso,
        "-e", end_iso,
        "-c", "Resources",
        "-f", "json"
    ]

    print("Exécution de la commande:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        with open("billing.json", "w") as f:
            f.write(result.stdout)
        print("✅ Données enregistrées dans 'billing.json'")
    else:
        print("❌ Échec de la récupération des données")
        print("STDERR:", result.stderr)
        print("STDOUT:", result.stdout)

if __name__ == "__main__":
    main()