<br />
<div align="center">
  <h3 align="center">Openstack Sysadmin Toolbox 🧰</h3>
</div>

### Built With

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

### Disclaimer

These toolbox is configured to match Infomaniak's Public Cloud costs (euros and CHF). Iy fou want, you can reconfigure it to mach your provider's costs.

<!-- GETTING STARTED -->
## Getting started

* Log in your Openstack environnement
* Clone this repo in your Openstack directory
  ```sh
  source openstack/bin/activate
  source ../openstack.sh
  ```

## Openstack summary with instance costs

### 1. As a client

In your terminal, type this command : 
  ```sh
python3 openstack_summary.py
  ```

By default, you can see the last hour of billing (simply press enter), but you can choose the dates you want.

### 2. As an admin (beta)

As an Openstack admin, maybe you don't want to see the costs of all the instance, but you need to see a specific project.
  ```sh
python3 openstack_admin_script.py
  ```

## Openstack optimization

### 1. As a user

In your terminal, type this command : 
  ```sh
python3 openstack_optimization.py
  ```

### 2. Weekly notification

* Put your Openstack credentials in secrets.json :
  ```sh
  {
  "auth_url": "http://openstack.example.com:5000/v3",
  "username": "user",
  "password": "pass",
  "project_name": "project",
  "user_domain_name": "default",
  "project_domain_name": "default"
  }
  ```
* Configure emails in notification.py :
  ```sh
  smtp_server = '<your-smtp-server>'
  smtp_port = 587
  smtp_username = '<your-smtp-username>'
  smtp_password = '<your-smtp-password>'
  from_email = '<your-email>'
  to_email = '<recipient-email>'
  ```
* Add a cron task :
  ```sh
  crontab -e
  ```
* Adapt the path below to match the location of your project directory:
  ```sh
  0 8 * * 1 /usr/bin/python3 /path/to/your/project/weekly_notification_optimization.py >> /tmp/cron_optimization.log 2>&1
  ```

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

Special thanks to [@kallioli](https://github.com/kallioli) for his support ! 
