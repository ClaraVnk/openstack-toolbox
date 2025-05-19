#!/usr/bin/env python3
import subprocess
import sys

def run_script(script_name):
    print(f"--- Lancement de {script_name} ---")
    result = subprocess.run([sys.executable, script_name])
    if result.returncode != 0:
        print(f"❌ Le script {script_name} a échoué avec le code {result.returncode}")
        sys.exit(result.returncode)

def main():
    run_script("fetch_billing.py")
    run_script("openstack_script.py")

if __name__ == "__main__":
    main()