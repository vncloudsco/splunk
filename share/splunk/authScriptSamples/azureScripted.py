from commonAuth import *
import requests
import json

# If Azure is your identity provider, you can use this script to extract Security Assertion
# Markup Language (SAML) user information as an alternative to using SAML attribute
# query requests (AQR) which Azure does not support.
#
# You can provide your Azure API key credentials in the authentication.conf file and use 
# the Azure API to extract user information. In authentication.conf, configure the 
# 'scriptSecureArguments' setting to "azureKey:<your Azure API key>". For example:
#
# scriptSecureArguments = azureKey:<your Azure API key string>
#
# After you restart the Splunk platform, the platform encrypts your Azure credentials.
# For more information about Splunk platform configuration files, search the
# Splunk documentation for "about configuration files".

USER_ENDPOINT = 'https://graph.microsoft.com/v1.0/users/'

def getUserInfo(args):
        apiKey = args['azureKey']
        API_KEY_HEADER = 'Bearer ' + apiKey
        AZURE_HEADERS = {'Host' : 'graph.microsoft.com', 'Authorization' : API_KEY_HEADER}

        realNameStr = ''
        # Assuming the username passed in is in the form of an email address corresponding
        # to the Azure user.
        usernameStr = args['username']
        objectId = ''
        fullString = ''
        rolesString = ''

        # Unable to append the username to users endpoint to gather user info, so get
        # all users, search for the username, and map this username to other user fields.
        # Operating under the assumption that the object id of a user needs to be appended
        # to the user endpoint in order to obtain information for the user.
        userResponse = requests.request('GET', USER_ENDPOINT, headers=AZURE_HEADERS)

        if userResponse.status_code != 200:
                print(FAILED)
                return

        userAttributes = json.loads(userResponse.text)

        # Assuming the username is the email for a user.
        for item in userAttributes['value']:
                if item['mail'] == usernameStr:
                        objectId = item['id']
                        realNameStr = item['displayName']
                        break

        # Construct a groups endpoint with the user's object ID
        groupsEndpoint = USER_ENDPOINT + objectId + '/memberOf'
        groupsResponse = requests.request('GET', groupsEndpoint, headers=AZURE_HEADERS)

        if groupsResponse.status_code != 200:
                print(FAILED)
                return

        groupsAttributes = json.loads(groupsResponse.text)

        # Returning the display Name associated with each group the user is a part of
        for item in groupsAttributes['value']:
                rolesString += item['displayName']
                if item != groupsAttributes['value'][-1]:
                        rolesString += ':'

        fullString += SUCCESS + ' ' + '--userInfo=' + usernameStr + ';' + realNameStr + ';' + rolesString
        print(fullString)

if __name__ == "__main__":
        callName = sys.argv[1]
        dictIn = readInputs()

        if callName == "getUserInfo":
                getUserInfo(dictIn)
