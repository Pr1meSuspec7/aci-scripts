#!/usr/bin/python3

import requests, json, yaml, os, re
from getpass import getpass
requests.urllib3.disable_warnings()


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
cookie = ""


# Get APIC Token
def get_apic_token(url, apic_user, apic_pwd):
	global cookie
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
        

# Input
class_names = ['fvRsPathAtt', 'l3extRsPathL3OutAtt']


# Function to query fvRsPathAtt
def aci_query_staticbind(url, class_name, cookie):
    r_get = requests.get(url + '/node/class/' + class_name + '.json', cookies=cookie, verify=False)
    get_json = r_get.json()
    json_formatted_str = json.dumps(get_json['imdata'], indent=2)
    list_encap = []
    for item in get_json['imdata']:
         list_encap.append(item['fvRsPathAtt']['attributes']['encap'] + ' -> ' + re.search("(?<=epg-)((?!/).)*" ,item['fvRsPathAtt']['attributes']['dn']).group())
         #list_encap.append(item['fvRsPathAtt']['attributes']['encap'])
    list_encap_unique = set(list_encap)
	#string_encap_unique = ', '.join(list_encap_unique)
    string_encap_unique = ', '.join(sorted(list_encap_unique))
    string_encap_unique = string_encap_unique.replace(', ', '\n')
    string_encap_unique = string_encap_unique.replace('vlan-', '')
    log_file = open("vlans.log", "a")
    log_file.write("*** Vlan used by EPGs:\n")
    log_file.write(string_encap_unique)
    log_file.write("\n\n")


# Function to query l3extRsPathL3OutAtt
def aci_query_l3out(url, class_name, cookie):
	r_get = requests.get(url + '/node/class/' + class_name + '.json', cookies=cookie, verify=False)
	get_json = r_get.json()
	json_formatted_str = json.dumps(get_json['imdata'], indent=2)
	list_encap = []
	for item in get_json['imdata']:
		list_encap.append(item['l3extRsPathL3OutAtt']['attributes']['encap'] + ' -> ' + re.search("(?<=out-)((?!/).)*" ,item['l3extRsPathL3OutAtt']['attributes']['dn']).group())
        #list_encap.append(item['l3extRsPathL3OutAtt']['attributes']['encap'])
	list_encap_unique = set(list_encap)
	string_encap_unique = ', '.join(sorted(list_encap_unique))
	string_encap_unique = string_encap_unique.replace(', ', '\n')
	string_encap_unique = string_encap_unique.replace('vlan-', '')
	log_file = open("vlans.log", "a")
	log_file.write("*** Vlan used by L3Out:\n")
	log_file.write(string_encap_unique)
	log_file.write("\n\n")



###

interactive_pwd()
get_apic_token(BASE_URL, apic_user, apic_pwd)

if os.path.exists("vlans.log"):
  os.remove("vlans.log")
  print("Old vlans.log file deleted !!!")
else:
  pass

print("Running query...")
for class_name in class_names:
	if class_name == "fvRsPathAtt":
		aci_query_staticbind(BASE_URL, class_name, cookie)
	else:
		aci_query_l3out(BASE_URL, class_name, cookie)
