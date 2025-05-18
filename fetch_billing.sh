#!/bin/bash
source ~/openstack.sh          # adapte selon ton environnement
source ~/projects/openstack/bin/activate  # adapte selon ton venv

start_time="$1"
end_time="$2"
output_file="$3"

openstack rating dataframes get -b "$start_time" -e "$end_time" -c Resources -f json > "$output_file"