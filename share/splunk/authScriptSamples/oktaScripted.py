from commonAuth import *
import requests
import json

# If Okta is your identity provider, you can use this script to extract Security Assertion
# Markup Language (SAML) user information as an alternative to using SAML attribute
# query requests (AQR) which Okta does not support.
#
# You can provide your Okta API key credentials in the authentication.conf
# file and use the Okta API to extract user information.
# In authentication.conf, configure the 'scriptSecureArguments' setting to
# "oktaKey:<your Okta API key>". For example:
#
# scriptSecureArguments = oktaKey:<your Okta API key string>
#
# After you restart the Splunk platform, the platform encrypts your Okta credentials.
# For more information about Splunk platform configuration files, search the
# Splunk documentation for "about configuration files".

# set the BASE_URL constant to the url associated to your okta developer account
BASE_URL = ''

def getUserInfo(args):
        # Here, we are extracting the okta API key from authentication.conf under scriptSecureArguments
        API_KEY = args['oktaKey']
        API_KEY_HEADER = 'SSWS ' + API_KEY
        OKTA_HEADERS = {'Accept':'application/json', 'Content-Type':'application/json', 'Authorization':API_KEY_HEADER}

        usernameStr = args['username']
        nameUrl = BASE_URL + '/api/v1/users/' + usernameStr
        groupsUrl = nameUrl + '/groups'

        nameResponse = requests.request('GET', nameUrl, headers=OKTA_HEADERS)
        groupsResponse = requests.request('GET', groupsUrl, headers=OKTA_HEADERS)

        roleString = ''
        realNameString = ''
        fullString = ''
        if groupsResponse.status_code != 200 or nameResponse.status_code != 200:
                print(FAILED)
                return
        nameAttributes = json.loads(nameResponse.text)
        realNameString += nameAttributes['profile']['firstName'] + ' ' + nameAttributes['profile']['lastName']
        groupAttributes = json.loads(groupsResponse.text)
        for i in range(0, len(groupAttributes)):
                roleString += groupAttributes[i]['profile']['name']
                if i != len(groupAttributes) - 1:
                        roleString += ':'
        fullString += SUCCESS + ' ' + '--userInfo=' + usernameStr + ';' + realNameString + ';' + roleString
        print(fullString)

if __name__ == "__main__":
        callName = sys.argv[1]
        dictIn = readInputs()

        if callName == "getUserInfo":
                getUserInfo(dictIn)
