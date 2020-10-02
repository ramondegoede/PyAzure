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
Get information of AKS Credentials secrets
"""
def get_aks_secrets_expiry(subscriptions):
    # create table
    print("{:<30} {:<35} {:<25} {:<15}".format("Subscription", "Cluster Name", "Secret Type", "Expiry date"))


    for subscription in subscriptions:
        # change subscription
        subprocess.call(["az", "account", "set", "-s", subscription['name']])

        subscription_name = subscription['name']
        # get all aks clusters of the subscription
        aks_clusters = subprocess.check_output("az aks list", shell=True).decode("UTF-8")
        if aks_clusters:
            aks_clusters = json.loads(aks_clusters)
            for aks_cluster in aks_clusters:
                aks_cluster_name = aks_cluster['name']
            

                ### check AKS SP secret expiry
                # check if managed service identity
                if aks_cluster['servicePrincipalProfile']["clientId"] == "msi":
                    print("{:<30} {:<35} {:<25} {:<15}".format(subscription_name, aks_cluster_name, "Managed Service Identity", "N/A"))
                else:
                    #get Service Principal information
                    secret = get_service_principal(aks_cluster['servicePrincipalProfile']["clientId"])

                    if secret['passwordCredentials']:
                        # get Secret exipy dates
                        for password in secret['passwordCredentials']:

                            expiry_date_service_principal = azure_format_time(password['endDate'])
                            # check if need to alert
                            alert_formatted = datetime.datetime.strptime(expiry_date_service_principal, '%d-%m-%Y')
                            alert = create_alert(alert_formatted)

                            print(alert + "{:<30} {:<35} {:<25} {:<15}".format(subscription_name, aks_cluster_name, "Service Principal Secret", expiry_date_service_principal))

                ### check aadProfile (clientAppId and serverAppID)
                if aks_cluster['aadProfile']:
                    ## serverAppId
                    serverAppId = get_service_principal(aks_cluster['aadProfile']['serverAppId'])
                    if serverAppId['passwordCredentials']:
                        for password in serverAppId['passwordCredentials']:
                            expiry_date_serverAppId = azure_format_time(password['endDate'])

                            alert_formatted = datetime.datetime.strptime(expiry_date_serverAppId, '%d-%m-%Y')
                            alert = create_alert(alert_formatted)

                            print(alert + "{:<30} {:<35} {:<25} {:<15}".format(subscription_name, aks_cluster_name, "AAD Server App Secret", expiry_date_serverAppId))

                    clientAppId = get_service_principal(aks_cluster['aadProfile']['clientAppId'])
                    if clientAppId['passwordCredentials']:
                        for password in clientAppId['passwordCredentials']:
                            expiry_date_clientAppId = azure_format_time(password['endDate'])

                            alert_formatted = datetime.datetime.strptime(expiry_date_clientAppId, '%d-%m-%Y')
                            alert = create_alert(alert_formatted)
                            print(alert + "{:<30} {:<35} {:<25} {:<15}".format(subscription_name, aks_cluster_name, "AAD Client App Secret", expiry_date_clientAppId))
      

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

"""
Reset AKS secrets
inputs:
 - cluster_name : string of cluster "aks_cluster"
 - cluster_resourcegroup : string of cluster resourcegroup "rg_cluster"
 - cluster_subscription : string of cluster subscription "11111111-2222-3333-4444-555555555555"
 - secrets : list of secrets to renew ["servicePrincipal", "serverApp", "clientApp"]
"""
def reset_aks_secrets_expiry(cluster_name, cluster_resourcegroup, cluster_subscription, secrets):\
    # set subscription
    subprocess.call("az account set -s {}".format(cluster_subscription), shell=True)
    # get cluster info
    cluster = subprocess.check_output("az aks show --name {} --resource-group {} --subscription {}".format(cluster_name, cluster_resourcegroup, cluster_subscription), shell=True).decode("UTF-8")
    cluster = json.loads(cluster)
    #get Service Principal information
    service_principal_id = cluster['servicePrincipalProfile']["clientId"]
    # reset Service Principal secret
    print("creating new secret")
    new_secret = subprocess.check_output("az ad sp credential reset --name {} --query password -o tsv".format(service_principal_id), shell=True).decode("UTF-8")

    time.sleep(5)

    print("updating service principal secret for {}".format(cluster_name))
    subprocess.call("az aks update-credentials --name {} --resource-group {} --reset-service-principal --service-principal {} --client-secret {}".format(cluster_name, cluster_resourcegroup, service_principal_id, new_secret), shell=True)
    print("update was successfull")