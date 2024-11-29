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
group.add_argument('-d', '--description', type=str, help='String to search. Use comma "," to search multiple strings. Example:\
                    python interface-configuration-search.py -d SRV01,SRV02.')
group.add_argument('-i', '--interface', nargs='*', type=str, help='Pod + node-id + interface. Use comma "," to search multiple interface. Example:\
                    python interface-configuration-search.py -i pod-1 101 eth1/57.')
# To run in python terminal invert comment in the next two lines (for debug) 
args = parser.parse_args()
# args = parser.parse_args(['-d', 'PA-AS-MI-01', '-w', '70'])
# args = parser.parse_args(['-i', 'pod-1', '101', 'eth1/3', 'pod-1', '102', 'eth1/3', '-w', '70'])

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H-%M-%S")

def interactive_pwd():
    '''Function to ask password if not set'''
    global apic_pwd
    if apic_pwd == "" or apic_pwd == None:
          apic_pwd = getpass("Insert APIC password for user " + apic_user +": ")
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

def aci_query_infraPortSummary_by_descr(url, description, cookie):
    '''Function to query interface description'''
    r_get = requests.get(f'{url}/node/class/infraPortSummary.json?query-target-filter=and(wcard(infraPortSummary.description,"{description}"))&order-by=infraPortSummary.description|desc',
                         cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    #get_json = [i['l1PhysIf']['attributes'] for i in get_json['imdata']]
    formatted_str = json.dumps(get_json, indent=4)
    #print(formatted_str)
    #log_file = open("output.log", "w")
    #log_file.write(formatted_str)
    #log_file.write("\n")
    return get_json

def aci_query_infraPortSummary_by_interface(url, pod, node, interface, cookie):
    '''Function to query node interface'''
    r_get = requests.get(f'{url}/node/class/infraPortSummary.json?query-target-filter=and(eq(infraPortSummary.portDn,"topology/{pod}/paths-{node}/pathep-[{interface}]"))&order-by=infraPortSummary.modTs|desc',
                         cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    formatted_str = json.dumps(get_json, indent=4)
    return get_json

def aci_query_operStQual(url, pod, node, interface, cookie):
    '''Function to query operStQual'''
    r_get = requests.get(f'{url}/node/mo/topology/pod-{pod}/node-{node}/sys/phys-[{interface}].json?query-target=children',
                         cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    formatted_str = json.dumps(get_json, indent=4)
    #print(formatted_str)
    return get_json

def aci_query_fvRsPathAtt(url, portDn, cookie):
    '''Function to query fvRsPathAtt'''
    r_get = requests.get(f'{url}/node/class/fvRsPathAtt.json?query-target-filter=and(eq(fvRsPathAtt.tDn,"{portDn}"))&order-by=fvRsPathAtt.modTs|desc',
                         cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    formatted_str = json.dumps(get_json, indent=4)
    #print(formatted_str)
    return get_json

def extract_data(imdata, imdata2, imdata3):
    '''Function to extract data and combine dictionary'''
    dict = {}
    list_of_dict = []
    for i, ii in zip(imdata, imdata2):
        list_of_epgs = []
        dict['POD']=(i['infraPortSummary']['attributes']['pod'])
        dict['NODE']=(i['infraPortSummary']['attributes']['node'])
        dict['INTERFACE']=re.findall(r'eth\S+(?=])', (i['infraPortSummary']['attributes']['portDn']))[0]
        dict['SHUTDOWN']='shutdown' if (i['infraPortSummary']['attributes']['shutdown']) == 'yes' else 'up'
        if ii[0].get('ethpmPhysIf') == None:
            dict['OPER STATUS']=(ii[1]['ethpmPhysIf']['attributes']['operSt'])
            dict['OPER REASON']=(ii[1]['ethpmPhysIf']['attributes']['operStQual'])
        else:
            dict['OPER STATUS']=(ii[0]['ethpmPhysIf']['attributes']['operSt'])
            dict['OPER REASON']=(ii[0]['ethpmPhysIf']['attributes']['operStQual'])
        if (i['infraPortSummary']['attributes']['mode']) == 'vpc':
             dict['PORT MODE']='Virtual Port-Channel'
        elif (i['infraPortSummary']['attributes']['mode']) == 'pc':
             dict['PORT MODE']='Port-Channel'
        else:
             dict['PORT MODE']='Individual'
        dict['POLICY GROUP']=re.findall(r'(?<=accbundle-|ccportgrp-)\S+', (i['infraPortSummary']['attributes']['assocGrp']))[0]
        dict['DESCRIPTION']=(i['infraPortSummary']['attributes']['description'])
        for iii in imdata3:
            if (iii['fvRsPathAtt']['attributes']['mode']) == 'regular':
                list_of_epgs.append(str(re.findall(r'tn-\S+(?=/rspat)',
                                                   (iii['fvRsPathAtt']['attributes']['dn'])))
                                                   + ' -> ' + str('trunk'))
            elif (iii['fvRsPathAtt']['attributes']['mode']) == 'untagged':
                list_of_epgs.append(str(re.findall(r'tn-\S+(?=/rspat)', 
                                                   (iii['fvRsPathAtt']['attributes']['dn'])))
                                                   + ' -> ' + str('access'))
            else:
                list_of_epgs.append(str(re.findall(r'tn-\S+(?=/rspat)',
                                                   (iii['fvRsPathAtt']['attributes']['dn'])))
                                                   + ' -> ' + str((iii['fvRsPathAtt']['attributes']['mode'])))
        # dict['EPGs']=list_of_epgs
        dict['EPGs']=' ||\n'.join(list_of_epgs)
        list_of_dict.append(dict.copy())
    return list_of_dict

def listDict_to_table(listDict):
    '''Function to create table'''
    table = PrettyTable()
    table._max_width = {'EPGs' : int(args.maxwidth)}
    table.field_names = ['POD','NODE','INTERFACE','ADMIN STATUS','OPER STATUS','OPER REASON','PORT MODE','POLICY GROUP','DESCRIPTION', 'EPGs']
    for dict in listDict:
        table.add_row(dict.values())
    return table

def format_logs(data):
    for i in data:
        i['EPGs'] = i['EPGs'].split(' ||\n')
    return data

def split_list(lst, chunk_size):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

########################

interactive_pwd()
cookie = get_apic_token(BASE_URL, apic_user, apic_pwd)

# Make a different query for each description
if args.description:
    for descr in args.description.split(','):
        query_response_infraPortSummary = aci_query_infraPortSummary_by_descr(BASE_URL, descr, cookie)

        # Go to next iteration if no results
        if len(query_response_infraPortSummary) == 0:
            print(f'\nNo results for -> {descr}\n')
            continue
        else:
            pass

        # This for loop makes other query to ethpmPhysIf and vRsPathAtt based on interfaces in query_response_infraPortSummary
        query_response_operStQual = []
        query_response_vRsPathAtt = []
        for i in query_response_infraPortSummary:
            query_response_operStQual.append(aci_query_operStQual(BASE_URL, i['infraPortSummary']['attributes']['pod'],
                                                                i['infraPortSummary']['attributes']['node'], re.findall(r'eth\S+(?=])',
                                                                    (i['infraPortSummary']['attributes']['portDn']))[0], cookie))
            if i['infraPortSummary']['attributes']['mode'] == 'pc' or i['infraPortSummary']['attributes']['mode'] == 'vpc':
                query_response_vRsPathAtt.append(aci_query_fvRsPathAtt(BASE_URL, i['infraPortSummary']['attributes']['pcPortDn'], cookie))
            else:
                query_response_vRsPathAtt.append(aci_query_fvRsPathAtt(BASE_URL, i['infraPortSummary']['attributes']['portDn'], cookie))

        data_extract = extract_data(query_response_infraPortSummary, query_response_operStQual, query_response_vRsPathAtt[0])
        #print(data_extract)
        outputTable = listDict_to_table(data_extract)
        print(outputTable)
        data_extract_log = format_logs(data_extract)
        with open('output__' + timestamp + '.log', 'a') as output:
            output.write(json.dumps(data_extract_log, indent=4))
else:
    # TODO: PROBLEMA: il primo EPG viene loopato anche sulle altre interfacce
    # si tratta dello stesso errore che avevo prima
    interfaces = split_list(args.interface, 3)
    query_response_infraPortSummaryList = []
    for interface in interfaces:
        query_response_infraPortSummary = aci_query_infraPortSummary_by_interface(BASE_URL, interface[0], interface[1], interface[2], cookie)
        query_response_infraPortSummaryList.extend(query_response_infraPortSummary)

        # Go to next iteration if no results
        if len(query_response_infraPortSummary) == 0:
            print(f'\nNo results for -> {interface}\n')
            continue
        else:
            pass

        # This for loop makes other query to ethpmPhysIf and vRsPathAtt based on interfaces in query_response_infraPortSummary
    query_response_operStQual = []
    query_response_vRsPathAtt = []
    for i in query_response_infraPortSummaryList:
        query_response_operStQual.append(aci_query_operStQual(BASE_URL, i['infraPortSummary']['attributes']['pod'],
                                                            i['infraPortSummary']['attributes']['node'], re.findall(r'eth\S+(?=])',
                                                                (i['infraPortSummary']['attributes']['portDn']))[0], cookie))
        if i['infraPortSummary']['attributes']['mode'] == 'pc' or i['infraPortSummary']['attributes']['mode'] == 'vpc':
            query_response_vRsPathAtt.append(aci_query_fvRsPathAtt(BASE_URL, i['infraPortSummary']['attributes']['pcPortDn'], cookie))
        else:
            query_response_vRsPathAtt.append(aci_query_fvRsPathAtt(BASE_URL, i['infraPortSummary']['attributes']['portDn'], cookie))

    data_extract = extract_data(query_response_infraPortSummaryList, query_response_operStQual, query_response_vRsPathAtt[0])
    #print(data_extract)
    outputTable = listDict_to_table(data_extract)
    print(outputTable)
    data_extract_log = format_logs(data_extract)
    with open('./output/output__' + timestamp + '.log', 'a') as output:
        output.write(json.dumps(data_extract_log, indent=4))
