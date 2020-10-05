import os
import subprocess
import json
import base64
import datetime
import time
from . import azure


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

    time.sleep(10)

    print("updating service principal secret for {}".format(cluster_name))
    subprocess.check_output("az aks update-credentials --name {} --resource-group {} --reset-service-principal --service-principal {} --client-secret {}".format(cluster_name, cluster_resourcegroup, service_principal_id, new_secret), shell=True)
    print("update was successfull")

"""
Get information of AKS End Of Support
"""
def get_aks_end_of_support(subscriptions):

    ## check supported versions
    print("Supported versions are:")
    available_versions = json.loads(subprocess.check_output("az aks get-versions --location eastus --output json", shell=True).decode("UTF-8"))


    versions = []
    for version in available_versions['orchestrators']:
        ## create list of available versions
        minor_version = version['orchestratorVersion'].split(".")
        minor_version = "{}.{}".format(minor_version[0], minor_version[1])
        if minor_version not in versions:
            versions.append(minor_version)

        ## check versions to upgrade to
        upgraded_to = ""
        if version['upgrades']:
            for upgrade in version['upgrades']:
                upgraded_to = "{} {:<8}".format(upgraded_to, upgrade['orchestratorVersion'])

        print("{:<8} can be upgraded to: {}".format(version['orchestratorVersion'], upgraded_to))

    # create table
    print("{:<30} {:<35} {:<25} {:<30}".format("Subscription", "Cluster Name", "Cluster version", "Alert"))



    for subscription in subscriptions:
        # change subscription
        subprocess.call(["az", "account", "set", "-s", subscription['name']])

        subscription_name = subscription['name']
        # get all aks clusters of the subscription
        aks_clusters = subprocess.check_output("az aks list", shell=True).decode("UTF-8")
        if aks_clusters:
            aks_clusters = json.loads(aks_clusters)
            for aks_cluster in aks_clusters:
                # print(aks_cluster)
                aks_cluster_name = aks_cluster['name']
                aks_cluster_version = aks_cluster['kubernetesVersion']

                ## create alerts
                minor_version_cluster = aks_cluster_version.split(".")
                minor_version_cluster = "{}.{}".format(minor_version_cluster[0], minor_version_cluster[1])
                if minor_version_cluster not in versions:
                    error_color = '\033[91m'
                    reason = "Not supported version"
                else:
                    for supported_index, supported_version in enumerate(versions):
                        if supported_version == minor_version_cluster:
                            # print(supported_index)
                            # print(type(supported_index))
                            if supported_index == 0:
                                reason = "Last supported version"
                                error_color = '\033[91m'
                                break
                            if supported_index == 1:
                                reason = "Second to last supported version"
                                error_color = '\033[93m'
                                break
                            else:
                                reason = ""
                                error_color = '\033[92m'
                                break

                ## create output
                print("{}{:<30} {:<35} {:<25} {:<30}".format(error_color, subscription_name, aks_cluster_name, aks_cluster_version, reason))

                ## TODO ADD agentpool check
                # for pool in aks_cluster['agentPoolProfiles']:
                #     pass

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
                    secret = azure.get_service_principal(aks_cluster['servicePrincipalProfile']["clientId"])

                    if secret['passwordCredentials']:
                        # get Secret exipy dates
                        for password in secret['passwordCredentials']:

                            expiry_date_service_principal = azure.azure_format_time(password['endDate'])
                            # check if need to alert
                            alert_formatted = datetime.datetime.strptime(expiry_date_service_principal, '%d-%m-%Y')
                            alert = azure.create_alert(alert_formatted)

                            print(alert + "{:<30} {:<35} {:<25} {:<15}".format(subscription_name, aks_cluster_name, "Service Principal Secret", expiry_date_service_principal))

                ### check aadProfile (clientAppId and serverAppID)
                if aks_cluster['aadProfile']:
                    ## serverAppId
                    serverAppId = azure.get_service_principal(aks_cluster['aadProfile']['serverAppId'])
                    if serverAppId['passwordCredentials']:
                        for password in serverAppId['passwordCredentials']:
                            expiry_date_serverAppId = azure.azure_format_time(password['endDate'])

                            alert_formatted = datetime.datetime.strptime(expiry_date_serverAppId, '%d-%m-%Y')
                            alert = azure.create_alert(alert_formatted)

                            print(alert + "{:<30} {:<35} {:<25} {:<15}".format(subscription_name, aks_cluster_name, "AAD Server App Secret", expiry_date_serverAppId))

                    clientAppId = azure.get_service_principal(aks_cluster['aadProfile']['clientAppId'])
                    if clientAppId['passwordCredentials']:
                        for password in clientAppId['passwordCredentials']:
                            expiry_date_clientAppId = azure.azure_format_time(password['endDate'])

                            alert_formatted = datetime.datetime.strptime(expiry_date_clientAppId, '%d-%m-%Y')
                            alert = azure.create_alert(alert_formatted)
                            print(alert + "{:<30} {:<35} {:<25} {:<15}".format(subscription_name, aks_cluster_name, "AAD Client App Secret", expiry_date_clientAppId))
      