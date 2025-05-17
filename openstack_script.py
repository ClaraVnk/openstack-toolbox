import openstack

# Se connecter à OpenStack
conn = openstack.connect(cloud='NUAGE', region_name='REGION')

# Lister les instances
print("Liste des instances :")
for server in conn.compute.servers():
    print(server)

# Lister les images
print("\nListe des images :")
for image in conn.compute.images():
    print(image)

# Lister les snapshots
print("\nListe des snapshots :")
for snapshot in conn.block_storage.snapshots():
    print(snapshot)

# Lister les services
print("\nListe des services :")
for service in conn.identity.services():
    print(service)

# Lister les types de machines virtuelles
print("\nListe des types de machines virtuelles :")
for flavor in conn.compute.flavors():
    print(flavor)

# Lister les volumes sous forme d'arborescence
print("\nArborescence des volumes :")

# Récupérer les volumes attachés aux instances
def mounted_volumes(conn):
    instances = conn.compute.servers()
    volumes = conn.block_storage.volumes()
    instance_volumes = {}

    for volume in volumes:
        if volume.attachments:
            for attachment in volume.attachments:
                instance_id = attachment['server_id']
                if instance_id not in instance_volumes:
                    instance_volumes[instance_id] = []
                instance_volumes[instance_id].append(volume)

    tree = {}
    for instance in instances:
        instance_id = instance.id
        instance_name = instance.name
        if instance_id in instance_volumes:
            tree[instance_name] = [volume.name for volume in instance_volumes[instance_id]]
        else:
            tree[instance_name] = []

    return tree

# Afficher l'arborescence
def print_tree(tree):
    for instance, volumes in tree.items():
        print(f"Instance: {instance}")
        for volume in volumes:
            print(f"  Volume: {volume}")

# Obtenir l'arborescence des volumes montés
tree = mounted_volumes(conn)

# Afficher l'arborescence
print_tree(tree)