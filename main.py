from utils import azure

# check all aks secrets expiry dates
# azure.get_aks_secrets_expiry(azure.get_subscriptions())

# renew aks cluster secrets
cluster_name = "AKSGordon"
cluster_resourcegroup = "AKS-Gordon"
cluster_subscription = "DEV-topaas"
secrets = ["servicePrincipal"]
azure.reset_aks_secrets_expiry(cluster_name, cluster_resourcegroup, cluster_subscription, secrets)