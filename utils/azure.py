import os
import subprocess
import json
import base64
import datetime
import time

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
"""
Creates list of subscriptions owned by logged in CLI session
"""
def get_subscriptions():
    command = "az account list --output json"
    output = subprocess.check_output(command, shell=True)
    decode_output = output.decode('UTF-8')
    json_output = json.loads(decode_output)
    return json_output

"""
alert
"""
def create_alert(datetime_object):
    time_now = datetime.datetime.now()
    # calculate time difference
    time_difference = datetime_object - time_now
    if time_difference.days < 30:
        ## red color
        alert = "\033[91m"
    elif time_difference.days < 100:
        ## orange color
        alert = "\033[93m"
    else:
        ## green color
        alert = "\033[92m"
    return alert
"""
Gets all kubeconfigs from all subscriptions
"""
def get_kubeconfigs(subscriptions):
    for subscription in subscriptions:
        # change subscription
        subprocess.call(["az", "account", "set", "-s", subscription['name']])

        clusters = subprocess.check_output("az aks list", shell=True).decode("UTF-8")
        clusters_json = json.loads(clusters)

        print("checking {}".format(subscription['name']))

        if clusters_json:

            # print(clusters_json)

            for cluster in clusters_json:
                cluster_resourcegroup = cluster['resourceGroup']
                cluster_name = cluster['name']

                command = "az aks get-credentials --name {} --resource-group {} --overwrite-existing".format(cluster_name, cluster_resourcegroup)

                print("added " + cluster_name + " to contexts")
                time.sleep(1)


"""
Get app registration/service principal information
"""
def get_service_principal(sp_id):
    sp_info = subprocess.check_output("az ad app show --id {}".format(sp_id), shell=True).decode("UTF-8")
    sp_info_json = json.loads(sp_info)
    return sp_info_json

"""
format azure time responses
"""
def azure_format_time(azure_time):
    azure_time_split = azure_time.split("T")
    azure_time_split = azure_time_split[0]

    azure_time_formatted = datetime.datetime.strptime(azure_time_split, '%Y-%m-%d').strftime('%d-%m-%Y')
    return azure_time_formatted



"""
Add role assignments
inputs :
 - subscription : string of subscriptionId e.g.: "11111111-2222-3333-4444-555555555555"
 - resource_groups : list of resourcegroups e.g.: ["RESOURCEGROUP01","RESOURCEGROUP02"]
"""
def add_role_assignments(subscription, resource_groups):
    role = "\"CustomRole - Resource Lock\""
    assignee = "\"a0c4bc02-7bee-49ff-9535-bf53df501732\""
    for resource_group in resource_groups:
        scope = "/subscriptions/{}/resourceGroups/{}".format(subscription, resource_group)
        output = subprocess.check_output("az role assignment create --assignee {} --role {} --scope {}".format(assignee, role, scope), shell=True).decode("UTF-8")
        print("gave {} the role {} on resourcegroup: {}".format(assignee, role, resource_group))