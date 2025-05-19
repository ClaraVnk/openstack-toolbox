#!/usr/bin/env python3
import subprocess
from datetime import datetime, timedelta, timezone
import argparse

def trim_to_minute(dt_str):
    return dt_str.replace("T", " ")[:16]

def isoformat(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

def input_with_default(prompt, default):
    s = input(f"{prompt} [Défaut: {default}]: ")
    return s.strip() or default

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', help="Date de début au format ISO")
    parser.add_argument('--end', help="Date de fin au format ISO")
    return parser.parse_args()

def main():
    args = parse_args()
    if args.start and args.end:
        start_iso = args.start
        end_iso = args.end
        print(f"Période reçue pour le billing: {start_iso} → {end_iso}")
    else:
        default_start = isoformat(datetime.now(timezone.utc) - timedelta(hours=2))
        default_end = isoformat(datetime.now(timezone.utc))
        print("Entrez la période de facturation souhaitée (format: YYYY-MM-DD HH:MM)")
        start_input = input_with_default("Date de début", trim_to_minute(default_start))
        end_input = input_with_default("Date de fin", trim_to_minute(default_end))
        start_dt = datetime.strptime(start_input, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_input, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        start_iso = isoformat(start_dt)
        end_iso = isoformat(end_dt)
        print(f"Période choisie: {start_iso} → {end_iso}")

    cmd = [
        "openstack", "rating", "dataframes", "get",
        "-b", start_iso,
        "-e", end_iso,
        "-c", "Resources",
        "-f", "json"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        with open("billing.json", "w") as f:
            f.write(result.stdout)
    else:
        print("❌ Échec de la récupération des données")
        print("STDERR:", result.stderr)
        print("STDOUT:", result.stdout)

if __name__ == "__main__":
    main()