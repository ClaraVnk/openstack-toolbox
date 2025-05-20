#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime, timedelta, timezone
import re
from collections import defaultdict

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

        def parse_flavor_name(flavor_name):
            match = re.match(r"[a-zA-Z]?(\d+)-ram(\d+)-disk(\d+)", flavor_name)
            if match:
                cpu = int(match.group(1))
                ram = int(match.group(2))
                disk = int(match.group(3))
                return cpu, ram, disk
            return 0, 0, 0

        usages = defaultdict(lambda: {"cpu": 0, "ram": 0, "storage": 0})

        for entry in data:
            desc = entry.get("desc", {})
            project_id = desc.get("project_id", "inconnu")
            flavor = desc.get("flavor_name", "")
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

        with open("weekly_uses.json", "w") as f:
            json.dump(usage_list, f, indent=2)
    else:
        print("❌ Échec de la récupération des données")
        print("STDERR:", result.stderr)
        print("STDOUT:", result.stdout)

if __name__ == "__main__":
    main()