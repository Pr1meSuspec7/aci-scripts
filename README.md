# Simple ACI query

This script helps engineers speed up moqueries on ACI.


### Requirements

This script tested on Linux/Windows with python3.10 or higher.  
It's recommended to crate a virtual environment, activate it and then install the packages:

For Windows:

```sh
> git clone https://github.com/Pr1meSuspec7/simple-aci-query.git
> cd simple-aci-query
> python -m venv VENV-NAME
> VENV-NAME\Scripts\activate.bat
> pip install -r requirements.txt
```

For Linux:

```sh
$ git clone https://github.com/Pr1meSuspec7/simple-aci-query.git
$ cd simple-aci-query
$ python -m venv VENV-NAME
$ source VENV-NAME/bin/activate
$ pip install -r requirements.txt
```
>NOTE: chose a name for virtual environment and replace the `VENV-NAME` string


### How it works

You need to setup the ip/hostname and credentials login for the apic in the apic.yaml file:
```yaml
---
apic_ip: "apic_ip_or_hostname"
apic_user: "apic_username"
apic_pwd: "apic_password"
```
>NOTE: You can omit the password for security. Password will be prompted during script execution.

After that you can run this command for help:
```sh
$ python query-general.py -h

usage: query-general.py [-h] -c CLASS_NAME [-p PROPERTY_NAME] [-f FILTER_NAME]

Simple script to run ACI moquery

options:
  -h, --help            show this help message and exit
  -c CLASS_NAME, --class_name CLASS_NAME
                        Object class to query: fvTenant, fvAp, fvAEPg, fvRsPathAtt, l3extRsPathL3OutAtt, l1PhysIf
  -p PROPERTY_NAME, --property_name PROPERTY_NAME
                        Class property to filter: descr, dn, encap
  -f FILTER_NAME, --filter_name FILTER_NAME
                        String to match in filtered property
```

You can run a query using only the CLASS_NAME object or by adding PROPERTY_NAME of the object followed by FILTER_NAME.

Each output will be saved in the output.log file. 
>NOTE: The output.log file will be overwritten at each execution !!!


### Examples

This command query all Tenants:
```sh
$ python query-general.py -c fvTenant
```

This command query the Tenant named "Test-Tenant":
```sh
$ python query-general.py -c fvTenant -p name -f Test-Tenant
```

This command query all interfaces with "esx or ESX" in the "description" field:
```sh
$ python query-general.py -c l1PhysIf -p descr -f "esx|ESX"
```
>NOTE: When using a regex for the filter, include it between double quotes.


### Extra

How many times have you asked yourself "is this vlan used in ACI?" or "what are the vlans I'm using in ACI?" 
Now you can know in a flash using the script all-vlans-query.py.

Simply by running the command
```sh
$ python all-vlans-query.py
```
you will find all the vlans actually used by all EPGs and L3Outs. This list will be saved in the vlans.log file.


### MIT License
Feel free to edit, improve and share
