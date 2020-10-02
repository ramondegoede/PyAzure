from utils import azure

# check all aks secrets expiry dates
azure.get_aks_secrets_expiry(azure.get_subscriptions())