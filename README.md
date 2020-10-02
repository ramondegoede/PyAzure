# PyAzure
Python script for azure components

# Features
 - find secret expiry date of AKS clusters
 
## aks secret expiry
AKS uses different types of secrets in the form of Service Principles to manage azure/aad. These can expire and will cause downtime. To check all AKS clusters in an tenant login with an AZ CLI session and run run.py
