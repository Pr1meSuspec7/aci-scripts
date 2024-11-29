#!/usr/bin/python3

import requests
import json
import yaml
import argparse
import pandas as pd
import os
from getpass import getpass
from UliPlot.XLSX import auto_adjust_xlsx_column_width
requests.urllib3.disable_warnings()


# Argument definitions
parser = argparse.ArgumentParser(description='Script to query leaf interfaces')
parser.add_argument('-p', '--pod_id', type=str, help='Pod ID', required=True)
parser.add_argument('-l', '--leaf_id', type=str, help='Leaf ID to query', required=True)
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

########################

# Function to query interfaces
def aci_query(url, pod_id, leaf_id, cookie):
    r_get = requests.get(url + '/node/class/topology/pod-' + pod_id + '/node-' + leaf_id + '/l1PhysIf.json?rsp-subtree=children&rsp-subtree-class=ethpmPhysIf&order-by=l1PhysIf.id|asc', cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    #get_json = [i['l1PhysIf']['attributes'] for i in get_json['imdata']]
    formatted_str = json.dumps(get_json, indent=4)
    print(formatted_str)
    log_file = open("./output/output.log", "w")
    log_file.write(formatted_str)
    log_file.write("\n")
    return get_json


# Function to extract data
def extract_data(imdata):
    dict = {}
    list_of_dict = []
    for i in imdata:
        dict['INTERFACE']=(i['l1PhysIf']['attributes']['id'])
        dict['DESCRIPTION']=(i['l1PhysIf']['attributes']['descr'])
        dict['USAGE']=(i['l1PhysIf']['attributes']['usage'])
        dict['OPER_SPEED']=(i['l1PhysIf']['children'][0]['ethpmPhysIf']['attributes']['operSpeed'])
        dict['OPER_STATE']=(i['l1PhysIf']['children'][0]['ethpmPhysIf']['attributes']['operSt'])
        dict['OPER_STATE_REASON']=(i['l1PhysIf']['children'][0]['ethpmPhysIf']['attributes']['operStQual'])
        dict['BUNDLE_ID']=(i['l1PhysIf']['children'][0]['ethpmPhysIf']['attributes']['bundleIndex'])
        dict['ALLOWED_VLAN']=(i['l1PhysIf']['children'][0]['ethpmPhysIf']['attributes']['allowedVlans'])
        list_of_dict.append(dict.copy())
    return list_of_dict


# Function to create excel file
def query_to_excel(pod_id, leaf_id, structure):
    df = pd.DataFrame(data=structure)
    if os.path.exists('pod_' + pod_id + '_interfaces.xlsx'):
        with pd.ExcelWriter('pod_' + pod_id + '_interfaces.xlsx', mode='a') as writer:
            df.to_excel(writer, index=False, sheet_name='Leaf-' + leaf_id)
            for column in df:
                column_length = max(df[column].astype(str).map(len).max(), len(str(column)))
                col_idx = df.columns.get_loc(column)
                writer.sheets['Leaf-' + leaf_id].column_dimensions[chr(65+col_idx)].width = column_length + 2
    else:
        with pd.ExcelWriter('pod_' + pod_id + '_interfaces.xlsx') as writer:
            df.to_excel(writer, index=False, sheet_name='Leaf-' + leaf_id)
            for column in df:
                column_length = max(df[column].astype(str).map(len).max(), len(str(column)))
                col_idx = df.columns.get_loc(column)
                writer.sheets['Leaf-' + leaf_id].column_dimensions[chr(65+col_idx)].width = column_length + 2
     

########################

#check_property_filter()
interactive_pwd()
cookie = get_apic_token(BASE_URL, apic_user, apic_pwd)
query_response = aci_query(BASE_URL, args.pod_id, args.leaf_id, cookie)
data_extract = extract_data(query_response)
query_to_excel(args.pod_id, args.leaf_id, data_extract)
