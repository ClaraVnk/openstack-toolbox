#!/bin/bash

cat << "EOF"
  ___                       _             _    
 / _ \ _ __   ___ _ __  ___| |_ __ _  ___| | __
| | | | '_ \ / _ \ '_ \/ __| __/ _` |/ __| |/ /
| |_| | |_) |  __/ | | \__ \ || (_| | (__|   < 
 \___/| .__/ \___|_| |_|___/\__\__,_|\___|_|\_\
|_   _|_|   ___ | | |__   _____  __            
  | |/ _ \ / _ \| | '_ \ / _ \ \/ /            
  | | (_) | (_) | | |_) | (_) >  <             
  |_|\___/ \___/|_|_.__/ \___/_/\_\            
           
            By Loutre

EOF

echo "Commandes disponibles:"
echo "  • openstack-summary      → Génère un résumé global du projet"
echo "  • openstack-optimization → Identifie les ressources sous-utilisées dans la semaine"
echo "  • weekly-notification    → Paramètre l'envoi d'un e-mail avec le résumé de la semaine"