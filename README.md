# Openstack SysAdmin Toolbox 🧰

### Built With

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

### Disclaimer

These toolbox is configured to match Infomaniak's Public Cloud costs (euros and CHF). If you want, you can reconfigure it to mach your provider's costs.

<!-- GETTING STARTED -->
### Getting started

* Log in your Openstack environnement
* Activate your venv : 
  ```sh
  source openstack-toolbox/bin/activate
  source ../openstack.sh
  ```

# Easy mode 

  ```sh
  pip install openstack-toolbox
  ```

Then for the Openstack summary :

  ```sh
  openstack_summary
  ```

For the Openstack optimization (weekly) :

  ```sh
  openstack_optimization
  ```

And for the the optimization's weekly notification :

  ```sh
  weekly_notification_optimization
  ```

# Manual mode

* Clone this repo in your Openstack directory

## Openstack summary 

This will list instances with their costs, backups, images, volumes, etc.

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

This will list inactive instances, unused volumes, and analyze the ressource usage with lost costs for the last week.

In your terminal, type this command : 
  ```sh
  python3 openstack_optimization.py
  ```

### Weekly notification

In your terminal, type this command : 
  ```sh
  python weekly_notification_optimization.py
  ```

You will have to configure SMTP services in order to send emails.
It will add a cron tab every monday at 08 am.

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

Special thanks to [@kallioli](https://github.com/kallioli) for his support !
