#!/usr/bin/python3

import requests
import json
import yaml
import sys
import argparse
from getpass import getpass
requests.urllib3.disable_warnings()


# Argument definitions
parser = argparse.ArgumentParser(description='Simple script to run ACI moquery')
parser.add_argument('-c', '--class_name', type=str, help='Object class to query: fvTenant, fvAp, fvAEPg, fvRsPathAtt, l3extRsPathL3OutAtt, l1PhysIf', required=True)
parser.add_argument('-p', '--property_name', type=str, help='Class property to filter: descr, dn, encap', required=False)
parser.add_argument('-f', '--filter_name', type=str, help='String to match in filtered property', required=False)
args = parser.parse_args()


# Function to ask password
def interactive_pwd():
    global apic_pwd
    if apic_pwd == "" or apic_pwd == None:
          apic_pwd = getpass("Insert APIC password for user " + apic_user +": ")
    else:
          pass
    

# Function to convert yaml to json
def yaml_to_json(file):
    with open(file, "r") as stream:
        try:
            parsed_yaml=yaml.safe_load(stream)
            return parsed_yaml
        except yaml.YAMLError as exc:
            print(exc)
    pass


# Import APIC vars
apic_vars = yaml_to_json("apic.yaml")


# APIC
apic_ip = apic_vars['apic_ip']
apic_user = apic_vars['apic_user']
apic_pwd = apic_vars['apic_pwd']
BASE_URL = 'https://' + apic_ip + '/api'


# Get APIC Token
def get_apic_token(url, apic_user, apic_pwd):
	login_url = f'{url}/aaaLogin.json'
	s = requests.Session()
	payload = {
		"aaaUser" : {
			"attributes" : {
				"name" : apic_user,
				"pwd" : apic_pwd
			}
		}
	}
	resp = s.post(login_url, json=payload, verify=False)
	resp_json = resp.json()
	token = resp_json['imdata'][0]['aaaLogin']['attributes']['token']
	cookie = {'APIC-cookie':token}
	return cookie


# Function to query MO
def aci_query(url, class_name, property_name, filter_name, cookie):
	if property_name == None:
		r_get = requests.get(url + '/node/class/' + class_name + '.json', cookies=cookie, verify=False)
		get_json = r_get.json()
		yaml_formatted_str = yaml.dump(get_json)
		print(yaml_formatted_str)
		log_file = open("./output/output.log", "w")
		log_file.write(yaml_formatted_str)
		log_file.write("\n")
	else:
		r_get = requests.get(url + '/node/class/' + class_name + '.json?query-target-filter=and(wcard(' + class_name + '.' + property_name + ',"' + filter_name + '"))', cookies=cookie, verify=False)
		get_json = r_get.json()
		yaml_formatted_str = yaml.dump(get_json)
		print(yaml_formatted_str)
		log_file = open("./output/output.log", "w")
		log_file.write(yaml_formatted_str)
		log_file.write("\n")
	pass

def check_property_filter():
      ''' Forces use -f when -p option is selected  '''
      if args.property_name and args.filter_name is None:
            parser.error('When using -p you must specify a filter using the -f option')

########################

check_property_filter()
interactive_pwd()
cookie = get_apic_token(BASE_URL, apic_user, apic_pwd)
aci_query(BASE_URL, args.class_name, args.property_name, args.filter_name, cookie)
