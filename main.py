import os
import subprocess
import json
import base64
import datetime
import time

from utils import azure

azure.get_aks_secrets_expiry(azure.get_subscriptions())