# Openstack SysAdmin Toolbox 🧰

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![infomaniak](https://img.shields.io/badge/infomaniak-0098FF?style=for-the-badge&logo=infomaniak&logoColor=white) ![OpenStack](https://img.shields.io/badge/Openstack-%23f01742.svg?style=for-the-badge&logo=openstack&logoColor=white)

### Disclaimer

These toolbox is configured to match Infomaniak's Public Cloud costs (euros and CHF). If you want, you can reconfigure it to mach your provider's costs.

<!-- GETTING STARTED -->
### Getting started with your virtual environnement

* Log in your Openstack environnement
* Activate your venv : 
  ```sh
  source openstack-toolbox/bin/activate
  source ../openstack-rc  # Source here your openstack credentials
  ```

# Easy mode 

  ```sh
  pip install openstack-toolbox
  ```

Command for the Openstack summary :

  ```sh
  openstack_summary
  ```

![OpenStack Summary Screenshot 1](https://raw.githubusercontent.com/ClaraVnk/openstack-toolbox/main/img/openstack_summary_1.png)
![OpenStack Summary Screenshot 2](https://raw.githubusercontent.com/ClaraVnk/openstack-toolbox/main/img/openstack_summary_2.png)

Command for the Openstack optimization report (weekly) :

  ```sh
  openstack_optimization
  ```

![OpenStack Optimization](https://raw.githubusercontent.com/ClaraVnk/openstack-toolbox/main/img/openstack_optimization.png)

Command for the optimization's email notification :

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
It will suggest you to add a cron tab every monday at 08 am.

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

Special thanks to [@kallioli](https://github.com/kallioli) for his support !
Thanks to [@PAPAMICA](https://github.com/PAPAMICA) for his suggestions.