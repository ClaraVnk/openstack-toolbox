#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime, timedelta, timezone

def isoformat(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

def main():
    today = datetime.now(timezone.utc).date()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    start_dt = datetime.combine(last_monday, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(last_sunday, datetime.max.time()).replace(tzinfo=timezone.utc)

    print(f"Période choisie automatiquement : la semaine dernière {start_dt} → {end_dt}")

    start_iso = isoformat(start_dt)
    end_iso = isoformat(end_dt)

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
        with open("weekly_uses.json", "w") as f:
            json.dump(usages, f, indent=2)
        print("Usages sauvegardés dans weekly_uses.json")
    else:
        print("❌ Échec de la récupération des données")
        print("STDERR:", result.stderr)
        print("STDOUT:", result.stdout)

if __name__ == "__main__":
    main()