#!/usr/bin/env python3
import subprocess
import sys
import os

def run_script(script_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))  # = src/
    script_path = os.path.join(script_dir, script_name)

    result = subprocess.run([sys.executable, script_path], check=True)
    if result.returncode != 0:
        print(f"❌ Le script {script_name} a échoué avec le code {result.returncode}")
        sys.exit(result.returncode)

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
                       by Loutre
    """
    print(header)
    run_script("fetch_billing.py")
    run_script("openstack_script.py")

if __name__ == "__main__":
    main()