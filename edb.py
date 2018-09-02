import requests
import json
import csv
import os
import openpyxl
import glob
import itertools


#change current directory to script diresctory for find config
os.chdir(os.path.dirname(__file__))

def get_settings():
    '''Function for read configs from edb_conf.txt file'''
    import configparser
    settings=configparser.ConfigParser()
    settings.read("./edb_conf.txt")
    return settings

def get_api_key(login, password):
    '''authorize with loginn\password and return token for future'''
    try:
        api_key=requests.get(settings['urls']['get_token'], auth=(login, password)).headers
        return api_key[settings['sensitive data']['token']]
    except Exception as e:
        print(f"There is error during authorizen, perhaps wrong login\password or troubles with connections. Emergency exit. Debug info: {e}")
        exit()

def get_all_kernel_version_from_edb(vendor, product, token):
    '''extract all available kernel's version from EDB for specific Linux distro and specific version'''
    headers={settings['sensitive data']['token'] : token}
    try:
        all_kernel_versions=requests.get(f"{settings['urls']['get_requests']}LINUX_KERNEL_RELEASES&vendor={vendor}&PRODUCT={product}", headers=headers)
        return json.loads(all_kernel_versions.content)
    except Exception as e:
        print(f"Critical error! Exiting... Debug info: {e}")
        exit()

def get_all_kernel_version_from_csv(filename):
    csv_r=csv.reader(open(filename, 'r'), delimiter=";")
    kernels_version=[]
    for row in csv_r:
        if row[1] not in kernels_version:
            kernels_version.append(row[1])
    return kernels_version

def get_server_id(server_name, token):
    '''return server id from EDB system by server name'''
    headers = {settings['sensitive data']['token']: token}
    try:
        server_id=json.loads(requests.get(f"{settings['urls']['get_requests']}server&name={server_name}", headers=headers).content)[settings['sensitive data']['data']][0]["ID"]
        return server_id
    except:
        print(f"Error during getting server_id for {server_name}")
        return None

def set_kernel_version(server_id, kernel_version, token, server_name):
    '''set server's kernel version'''
    headers = {settings['sensitive data']['token']: token}
    data=json.dumps({'ids': str(server_id),'fieldlist':{settings['sensitive data']['kernel_version']: kernel_version, settings['sensitive data']['kernel_release']:1}})
    try:
        r=requests.post(f"{settings['urls']['post_requests']}update&unit_type=kernel", data=data, headers=headers)
        if r.status_code!=requests.codes.ok:
            print(f"Fatal error with server_{server_name}, error message: {r.content}")
        else:
            print(f"kernel version has been successfully set fot {server_name} server")
    except Exception as e:
        print(f"Fatal error, {e}")

def get_servers_from_csv(filename):
    servers=[]
    csv_r=csv.reader(open(filename, 'r'), delimiter=";")
    for row in csv_r:
        servers.append(row[0])
    return servers

def parse_args():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("-f", '--filename', type=str, required=True, help='enter file name')
    parser.add_argument("-v", '--vendor', type=str, required=True, help='enter vendor name')
    parser.add_argument("-o", '--product', type=str, required=True, help='enter product name')
    return parser.parse_args()

def get_server_with_kernel_versions_from_csv(filename):
    dict_servers={}
    csv_r=csv.reader(open(filename, 'r'), delimiter=';')
    for row in csv_r:
        dict_servers[row[0]]=row[1]
    return dict_servers

def read_xls_content():
    file_name=glob.glob("./000/*.xlsx")
    if len(file_name)!=1:
        print("Please, copy Linux report to folder or make sure that we have only one report")
        exit()
    xls_file=openpyxl.load_workbook(filename=file_name[0], data_only=True)

    for row in itertools.islice(xls_file['Unix_report'], 1, None):
        for col in row:
            print(col.value)
    exit()

read_xls_content()
exit()


settings=get_settings()

my_args=parse_args()
api_key=get_api_key(settings['credentials']['login'], settings['credentials']['password'])

all_kernel_versions_in_csv=get_all_kernel_version_from_csv(my_args.filename)


#available_kernels_in_edb=get_all_kernel_version_from_edb("CentOS", "CentOS-7", api_key)
available_kernels_in_edb=get_all_kernel_version_from_edb(my_args.vendor, my_args.product, api_key)
all_kernel_versions_in_edb=[]
for current_string in available_kernels_in_edb[settings['sensitive data']['data']]:
    all_kernel_versions_in_edb.append(current_string[settings['sensitive data']['kernels']])

all_servers_from_csv=get_servers_from_csv(my_args.filename)
print(f'Kernels from csv-files which do not exists in EDB: {set(all_kernel_versions_in_csv) - set(all_kernel_versions_in_edb)}')
print("Is it OK or not?")

all_servers_with_kernel_versions=get_server_with_kernel_versions_from_csv(my_args.filename)

for current_server in all_servers_with_kernel_versions.keys():
    server_id=get_server_id(current_server, api_key)
    if server_id:
        set_kernel_version(server_id, all_servers_with_kernel_versions[current_server], api_key, current_server)
