#!/usr/bin/env python3
import subprocess
from datetime import datetime, timedelta, timezone

def trim_to_minute(dt_str):
      # Extrait "YYYY-MM-DD HH:MM" de la chaîne ISO complète
      # Exemple d'entrée : "2025-05-18T14:00:57+00:00"
      # On remplace "T" par espace puis on coupe après les 16 premiers caractères
      return dt_str.replace("T", " ")[:16]

def isoformat(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

def input_with_default(prompt, default):
    s = input(f"{prompt} [Défaut: {default}]: ")
    return s.strip() or default

def main():
        header = r"""
  ___                       _             _       
 / _ \ _ __   ___ _ __  ___| |_ __ _  ___| | __   
| | | | '_ \ / _ \ '_ \/ __| __/ _` |/ __| |/ /   
| |_| | |_) |  __/ | | \__ \ || (_| | (__|   <    
 \___/| .__/ \___|_| |_|___/\__\__,_|\___|_|\_\   
/ ___||_|  _ _ __ ___  _ __ ___   __ _ _ __ _   _ 
\___ \| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |
 ___) | |_| | | | | | | | | | | | (_| | |  | |_| |
|____/ \__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |
                                            |___/ 
           Openstack SysAdmin Toolbox
    """
    print(header)

    default_start = isoformat(datetime.now(timezone.utc) - timedelta(hours=2))
    default_end = isoformat(datetime.now(timezone.utc))

    print("Entrez la période de facturation souhaitée (format: YYYY-MM-DD HH:MM)")
    start_input = input_with_default("Date de début", trim_to_minute(default_start))
    end_input = input_with_default("Date de fin", trim_to_minute(default_end))

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