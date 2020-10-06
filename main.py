from utils import azure, aks

# check all aks secrets expiry dates and EOS state
aks.get_aks_end_of_support(azure.get_subscriptions())
aks.get_aks_secrets_expiry(azure.get_subscriptions())


# renew aks cluster secrets
# cluster_name = "AKS20AKSVPARA-P"
# cluster_resourcegroup = "VPARA-PROD"
# cluster_subscription = "\"Betalen naar gebruik\""
# secrets = ["servicePrincipal"]
# azure.reset_aks_secrets_expiry(cluster_name, cluster_resourcegroup, cluster_subscription, secrets)