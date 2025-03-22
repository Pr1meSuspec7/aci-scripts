#!/usr/bin/python3

import requests
import json
import yaml
import argparse
import re
import datetime
from getpass import getpass
from UliPlot.XLSX import auto_adjust_xlsx_column_width
requests.urllib3.disable_warnings()
from prettytable import PrettyTable


# Argument definitions
parser = argparse.ArgumentParser(description='Script to search interface description. *** Required ACI 5.2 or above ***')
parser.add_argument('-w', '--maxwidth', type=str, help='Max width of EPGs column. If the EPG column is not well formatted, \
                    try to adjust this parameter.', required=False, default='70')
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-d', '--description', nargs='*', type=str, help='String to search. You can search for multiple strings. \
                   Example: python interface-configuration-search.py -d SRV01 SRV02 "SRV03|srv03".')
group.add_argument('-i', '--interface', nargs='*', type=str, help='Pod + node-id + interface. You can search for multiple interfaces. \
                   Example: python interface-configuration-search.py -i pod-1 101 eth1/3 pod-1 302 eth1/42.')
# To run in python terminal invert comment in the lines (for debug) 
args = parser.parse_args()
# args = parser.parse_args(['-d', 'PA-AS-MI-01'])
# args = parser.parse_args(['-d', 'PA-AS-MI-01', '-w', '70'])
# args = parser.parse_args(['-i', 'pod-1', '101', 'eth1/3', 'pod-1', '102', 'eth1/3', '-w', '70'])
# args = parser.parse_args(['-i', 'pod-1', '302', 'eth1/1'])
# args = parser.parse_args(['-i', 'pod-1', '302', 'eth1/42'])
# args = parser.parse_args(['-i', 'pod-1', '101', 'eth1/3', 'pod-1', '302', 'eth1/42'])

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H-%M-%S")

def interactive_pwd():
    '''Function to ask password if not set'''
    global apic_pwd
    if apic_pwd == "" or apic_pwd == None:
          apic_pwd = getpass(f'Insert APIC password for user "{apic_user}": ')
    else:
          pass


def yaml_to_json(file):
    '''Function to convert yaml to json'''
    with open(file, "r") as stream:
        try:
            parsed_yaml=yaml.safe_load(stream)
            return parsed_yaml
        except yaml.YAMLError as exc:
            print(exc)
    pass


# Import APIC vars
apic_vars = yaml_to_json("apic.yaml")
apic_ip = apic_vars['apic_ip']
apic_user = apic_vars['apic_user']
apic_pwd = apic_vars['apic_pwd']
BASE_URL = 'https://' + apic_ip + '/api'


def get_apic_token(url, apic_user, apic_pwd):
    ''' Get APIC Token'''
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

def aci_query_infraPortSummary_by_interface(url, pod, node, interface, cookie):
    '''Function to query node interface'''
    r_get = requests.get(f'{url}/node/class/infraPortSummary.json?query-target-filter=and(eq(infraPortSummary.portDn,"topology/{pod}/paths-{node}/pathep-[{interface}]"))&order-by=infraPortSummary.modTs|desc',
                         cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    return get_json[0]

def aci_query_infraPortSummary_by_descr(url, description, cookie):
    '''Function to query interface description'''
    r_get = requests.get(f'{url}/node/class/infraPortSummary.json?query-target-filter=and(wcard(infraPortSummary.description,"{description}"))&order-by=infraPortSummary.description|desc',
                         cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    return get_json

def aci_query_fvRsPathAtt(url, portDn, cookie):
    '''Function to query fvRsPathAtt'''
    r_get = requests.get(f'{url}/node/class/fvRsPathAtt.json?query-target-filter=and(eq(fvRsPathAtt.tDn,"{portDn}"))&order-by=fvRsPathAtt.modTs|desc',
                         cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    return get_json

def aci_query_operStQual(url, pod, node, interface, cookie):
    '''Function to query operStQual'''
    # r_get = requests.get(f'{url}/node/mo/topology/pod-{pod}/node-{node}/sys/phys-[{interface}].json?query-target=children',
    r_get = requests.get(f'{url}/node/class/ethpmPhysIf.json?query-target-filter=and(eq(ethpmPhysIf.dn,"topology/{pod}/node-{node}/sys/phys-[{interface}]/phys"))&order-by=ethpmPhysIf.modTs|desc',
                         cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    # formatted_str = json.dumps(get_json, indent=4)
    return get_json

def extract_data(inputdata):
    '''Function to extract data and combine dictionary'''
    interface_dict = {}
    list_of_epgs = []
    interface_dict['POD']=inputdata['infraPortSummary']['attributes']['pod']
    interface_dict['NODE']=inputdata['infraPortSummary']['attributes']['node']
    interface_dict['INTERFACE']=re.findall(r'eth\S+(?=])', (inputdata['infraPortSummary']['attributes']['portDn']))[0]
    interface_dict['ADMIN STATE']='down' if inputdata['infraPortSummary']['attributes']['shutdown'] == 'yes' else 'up'
    interface_dict['OPER STATUS']=inputdata['infraPortSummary']['attributes']['operSt']
    interface_dict['OPER REASON']=inputdata['infraPortSummary']['attributes']['operStQual']
    if inputdata['infraPortSummary']['attributes']['mode'] == 'pc':
        interface_dict['PORT MODE']='Port-Channel'
    elif inputdata['infraPortSummary']['attributes']['mode'] == 'vpc':
        interface_dict['PORT MODE']='Virtual Port-Channel'
    else:
        interface_dict['PORT MODE']='Individual'
    interface_dict['POLICY GROUP']=re.findall(r'(?<=accbundle-|ccportgrp-)\S+', (inputdata['infraPortSummary']['attributes']['assocGrp']))[0]
    interface_dict['DESCRIPTION']=inputdata['infraPortSummary']['attributes']['description']
    for epg in inputdata['infraPortSummary']['attributes']['epgs']:
        if epg['fvRsPathAtt']['attributes']['mode'] == 'regular':
                list_of_epgs.append(str(re.findall(r'tn-\S+(?=/rspat)',
                                                   (epg['fvRsPathAtt']['attributes']['dn'])))
                                                   + ' -> ' + str('trunk'))
        elif epg['fvRsPathAtt']['attributes']['mode'] == 'untagged':
                list_of_epgs.append(str(re.findall(r'tn-\S+(?=/rspat)',
                                                   (epg['fvRsPathAtt']['attributes']['dn'])))
                                                   + ' -> ' + str('access'))
        else:
            list_of_epgs.append(str(re.findall(r'tn-\S+(?=/rspat)',
                                               (epg['fvRsPathAtt']['attributes']['dn'])))
                                               + ' -> ' + str(epg['fvRsPathAtt']['attributes']['mode']))
    interface_dict['EPGs'] = list_of_epgs
    return interface_dict

def format_dataframe(dataframe):
    '''Function to format dataframe'''
    for row in dataframe:
        row['EPGs'] = '\n'.join(row['EPGs'])
    return dataframe

def listDict_to_table(listOfDict):
    '''Function to create table'''
    table = PrettyTable()
    table._max_width = {'EPGs' : int(args.maxwidth)}
    table.field_names = ['POD','NODE','INTERFACE','ADMIN STATUS','OPER STATUS','OPER REASON','PORT MODE','POLICY GROUP','DESCRIPTION', 'EPGs']
    for dict in listOfDict:
        table.add_row(dict.values())
    return table

def split_args(lst, chunk_size):
    '''
    Function to split args.
    Example: split_args(['pod-1', '101', 'eth1/3', 'pod-1', '102', 'eth1/3'], 3)
    Output: [['pod-1', '101', 'eth1/3'], ['pod-1', '102', 'eth1/3']]
    '''
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def write_json_log(json_data):
    '''Function to write json log'''
    with open(f'./output/log_{timestamp}.json', 'w') as f:
        f.write(json.dumps(json_data, indent=4))

########################

interactive_pwd()
cookie = get_apic_token(BASE_URL, apic_user, apic_pwd)

# Initialize dataframe
dataframe = []

# If args is -i
if args.interface:
    interfaces = split_args(args.interface, 3)

    for interface in interfaces:
        query_interface = aci_query_infraPortSummary_by_interface(BASE_URL, interface[0], interface[1], interface[2], cookie)
        if query_interface['infraPortSummary']['attributes']['mode'] == 'pc' or query_interface['infraPortSummary']['attributes']['mode'] == 'vpc':
            query_epgs = aci_query_fvRsPathAtt(BASE_URL, query_interface['infraPortSummary']['attributes']['pcPortDn'], cookie)
        else:
            query_epgs = aci_query_fvRsPathAtt(BASE_URL, query_interface['infraPortSummary']['attributes']['portDn'], cookie)
        query_operStQual = aci_query_operStQual(BASE_URL, interface[0], interface[1], interface[2], cookie)
        query_interface['infraPortSummary']['attributes']['operSt'] = query_operStQual[0]['ethpmPhysIf']['attributes']['operSt']
        query_interface['infraPortSummary']['attributes']['operStQual'] = query_operStQual[0]['ethpmPhysIf']['attributes']['operStQual']
        query_interface['infraPortSummary']['attributes']['epgs'] = query_epgs
        dataframe.append(extract_data(query_interface))

# If args is -d
elif args.description:
    for description in args.description:
        query_description = aci_query_infraPortSummary_by_descr(BASE_URL, description, cookie)
        for interface in query_description:
            if interface['infraPortSummary']['attributes']['mode'] == 'pc' or interface['infraPortSummary']['attributes']['mode'] == 'vpc':
                query_epgs = aci_query_fvRsPathAtt(BASE_URL, interface['infraPortSummary']['attributes']['pcPortDn'], cookie)
            else:
                query_epgs = aci_query_fvRsPathAtt(BASE_URL, interface['infraPortSummary']['attributes']['portDn'], cookie)
            query_operStQual = aci_query_operStQual(BASE_URL, f"pod-{interface['infraPortSummary']['attributes']['pod']}", 
                                                    interface['infraPortSummary']['attributes']['node'], 
                                                    re.findall(r'eth\S+(?=])', (interface['infraPortSummary']['attributes']['portDn']))[0], 
                                                    cookie)
            interface['infraPortSummary']['attributes']['operSt'] = query_operStQual[0]['ethpmPhysIf']['attributes']['operSt']
            interface['infraPortSummary']['attributes']['operStQual'] = query_operStQual[0]['ethpmPhysIf']['attributes']['operStQual']
            interface['infraPortSummary']['attributes']['epgs'] = query_epgs
            dataframe.append(extract_data(interface))

# Write json log
write_json_log(dataframe)

# Format dataframe['EPGs'] for table
formatted_dataframe = format_dataframe(dataframe)
table = listDict_to_table(formatted_dataframe)
print(table)
