def generate_report():
    try:
        with open('/tmp/openstack_optimization_report.txt', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "❌ Le fichier /tmp/openstack_optimization_report.txt est introuvable."

if __name__ == '__main__':
    content = generate_report()
    print(content)