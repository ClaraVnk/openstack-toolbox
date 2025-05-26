# OpenStack Toolbox 🧰
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) 
![PyPi](https://img.shields.io/badge/pypi-%23ececec.svg?style=for-the-badge&logo=pypi&logoColor=1f73b7)
![Infomaniak](https://img.shields.io/badge/infomaniak-0098FF?style=for-the-badge&logo=infomaniak&logoColor=white) 
![OpenStack](https://img.shields.io/badge/OpenStack-%23f01742.svg?style=for-the-badge&logo=openstack&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=Prometheus&logoColor=white)

A suite of tools to optimize and manage your OpenStack resources, with multilingual support (FR/EN).

## 📋 Features

- 📊 **Metrics Collector** (`openstack_metrics_collector.py`)
  - Real-time Gnocchi metrics
  - Prometheus export
  - Request parallelization
  - Multi-project support

- 📈 **Resource Summary** (`openstack_summary.py`)
  - Instance list and details
  - Volumes and snapshots
  - Images and containers
  - Cost estimation
  - Mounted volumes tree view

- 👨‍💼 **Administration** (`openstack_admin.py`)
  - Project management
  - Resource overview
  - Operation parallelization

- 📧 **Weekly Notifications** (`weekly_notification_optimization.py`)
  - Automated email reports
  - Interactive SMTP configuration
  - Cron scheduling

## 🛠️ Installation

Clone the repository and install:
```bash
git clone https://github.com/your-username/openstack-toolbox.git
cd openstack-toolbox
pip install
```

Dependencies will be automatically managed through `pyproject.toml`.

## ⚙️ Configuration

### OpenStack Environment Variables

Create a `.env` file at the project root:

```bash
OS_AUTH_URL=https://your-auth-url
OS_PROJECT_NAME=your-project
OS_USERNAME=your-username
OS_PASSWORD=your-password
OS_USER_DOMAIN_NAME=your-domain
OS_PROJECT_DOMAIN_NAME=your-project-domain
OS_REGION_NAME=your-region
```

### SMTP Configuration (for notifications)

SMTP configuration is interactive. Run:
```bash
python src/weekly_notification_optimization.py
```

The script will guide you to configure:
- SMTP Server
- Port
- Credentials
- Email addresses

## 🚀 Usage

### Metrics Collector

```bash
python src/openstack_metrics_collector.py
```

The collector starts a Prometheus server on port 8000.
Available metrics:
- `openstack_identity_metrics`
- `openstack_compute_metrics`
- `openstack_block_storage_metrics`
- `openstack_network_metrics`
- `openstack_gnocchi_metric`

### Resource Summary

```bash
python src/openstack_summary.py
```

Displays a complete summary of your OpenStack resources:
- Instances (CPU, RAM, disk)
- Volumes and snapshots
- Images and containers
- Estimated costs

### Administration

```bash
python src/openstack_admin.py
```

Enter the project ID to view:
- Project details
- Resource list
- Usage metrics

### Weekly Notifications

```bash
python src/weekly_notification_optimization.py
```

Configures and sends weekly reports via email.

## 🌍 Internationalization

The project supports French (default) and English.
To change the language:

```python
from config import set_language_preference

set_language_preference('en')  # or 'fr'
```

## 📚 Function Documentation

### Utils (`utils.py`)

- `format_size(size_bytes)`: Formats a size in bytes
- `parse_flavor_name(name)`: Parses an OpenStack flavor name
- `isoformat(dt)`: Converts a date to ISO 8601
- `print_header(header)`: Displays a formatted header

### Config (`config.py`)

- `get_language_preference()`: Gets the configured language
- `set_language_preference(lang)`: Sets the language
- `create_smtp_config_interactive()`: Configures SMTP
- `load_smtp_config()`: Loads SMTP config
- `load_openstack_credentials()`: Loads OpenStack credentials

### Metrics (`openstack_metrics_collector.py`)

- Class `GnocchiAPI`: Client for Gnocchi API
  - `get_resources()`
  - `get_metrics_for_resource()`
  - `get_measures()`
- `collect_resource_metrics()`: Per-resource collection
- `collect_gnocchi_metrics_parallel()`: Parallel collection

### Admin (`openstack_admin.py`)

- `process_resource_parallel()`: Parallel processing
- `list_all_resources()`: Lists all resources
- Specialized listing functions for each type

### Notifications (`weekly_notification_optimization.py`)

- `generate_report()`: Generates the report
- `send_email()`: Sends via SMTP
- `setup_cron()`: Configures cron task

## 🤝 Contributing

Contributions are welcome! Feel free to:
1. Fork the project
2. Create a branch (`git checkout -b feature/improvement`)
3. Commit (`git commit -am 'Add feature'`)
4. Push (`git push origin feature/improvement`)
5. Open a Pull Request

## 📝 License

This project is under Apache License 2.0. See `LICENSE.TXT` file for more details.

## ✨ Author

Developed by Loutre