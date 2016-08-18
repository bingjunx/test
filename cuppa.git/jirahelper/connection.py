from jira.client import JIRA
from protected_config import credential

# TODO temporary solution for ssl error
# The problem is our JIRA sites uses ssl_version 1.2
# and requests trys to use ssl_version 3.
# The proper way to do this is write a custom HTTPAdapter (from requests)
# and modify(find a way) the jira package to use it.
import requests.packages.urllib3.util.ssl_
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL'

try:
    JR = JIRA(options=credential['options'], basic_auth=credential['basic_auth'])
except:
    JR = None

