"""
    This is only a sample authentication script, and is NOT SUPPORTED by Splunk.

    For the most basic example of how to use scripted auth, please see dumbScripted.py
    This script serves as an example of how to interact between splunkd and RADIUS.

    The example uses the RADIUS client from the freeradius server.
    http://www.freeradius.org/

    You must download and install this client for this script to function
    properly. If you already have your own RADIUS client you may use that
    but you may have to edit the function contactRADIUS to make it compatible
    with your client.

    Function breakdown
    Required:
        userLogin   : will be called on userLogin into splunk.
        getUserInfo : Get information about a particular user. ( username, realname, roles )
        getUsers    : Get a list of all users available.

    Optional Calls  :
        getSearchFilter : return a search filter for a given user. Called when the user searches.

"""
import subprocess
from commonAuth import *
from userMapping import *

RADIUS_CLIENT = '/opt/radius/bin/radclient'
RADIUS_SERVER = '<RADIUS_SERVER_NAME>:1812'

RADIUS_USER   = 'User-Name'
RADIUS_PASS   = 'User-Password'
# you may want to store this in a file to be passed to radclient. so it doesn't show on on cmd line.
RADIUS_SECRET = 'testing123'
RADIUS_FLAGS  = ['-s', '-r', '2']

'''
The radclient return code is always 0 if it managed to connect to the RADIUS server
regardless of whether the auth succeeded or not. If the authentication is successful
then one if the user attributes will be returned, we will search for that attr to
see if the login succeeded.
'''
RADIUS_GREP_STR = "Service-Type = Framed-User"

def getOctalStr(s):
    oct = ''
    for c in s:
        oct += '\%03o' % ord(c)
    return oct

'''
This function will be called when a user enters their credentials in the login page in UI.
    Input:
        --username=<user> --password=<pass> 
    Output:
        On Success:
            --status=success
        On Failuire:
            Anyhing but --status=success

    Splunk will print everything outputted to stdin if there is an error so you can add debugging info
    that will be printed in splunkd.log when the system is in DEBUG mode.
'''
def userLogin( infoIn  ):
    # Create the list of arguments to pass to Popen
    command = [RADIUS_CLIENT] + RADIUS_FLAGS + [RADIUS_SERVER, 'auth', RADIUS_SECRET]

    proc = subprocess.Popen( command, 
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE
                             )

    # Radius requires escaping certain special characters, so just send everything as octal to be safe
    stdInStr = 'User-Name="' + getOctalStr(infoIn['username']) + '",User-Password="' + getOctalStr(infoIn['password']) + '"'

    output = proc.communicate( stdInStr )
    proc.wait()

    # in this implementation we will consider a login a success
    # when we see Service-Type = Framed-User being returned on stdout.
    # you may change this to any other indicator you think is valid.
    if output[0].find( RADIUS_GREP_STR ) != -1:
        print(SUCCESS)
    else:
        print(FAILED)


'''
    This function prints out the details of the userId supplied.
    Input :
        --username=<user>
    Output:
        --status=success --userInfo=<userId>;<username>;<realname>;<role>:<role>:<role>    Note roles delimited by :
'''
def getUserInfo( infoIn ):
    roleList = getUsersRole( infoIn['username'] )

    outStr = SUCCESS + " --userInfo=" + infoIn["username"] + ";" + infoIn["username"] + ";" + infoIn["username"] + ";"
    for roleItem in roleList:
        outStr = outStr + roleItem + ":"

    print(outStr)



'''
    This function gets all the users in the system that scripted auth will work for.
    Input :
        N/A
    Output :
        --status=success --userInfo=<userId>;<username>;<realname>;<role>:<role>:<role> --userInfo=<userId>;<username>;<realname>;<role>:<role>:<role>  ...
'''
def getUsers( infoIn ):
    print(SUCCESS + getAllUsers())


'''
    Gets the search filter for a given user.
    You must have the flag scriptSearchFilters set to 1 on the config for this function to be used.
    Input :
        --username=<username>
    Output:
        --search_filter=<filter> --search_fil....
'''
def getSearchFilter( infoIn ):
    outStr = SUCCESS
    filters = getUsersFilters( infoIn['username'] )
    outStr = SUCCESS

    for i in filters:
        outStr = outStr + " --search_filter=" + str(i) 

    print(outStr)


def contactRADIUS( inforIn, callname ):
    print("edit this function")

  
if __name__ == "__main__":
   callName = sys.argv[1]
   dictIn = readInputs()
   
   returnDict = {}
   if callName == "userLogin":
      userLogin( dictIn )
   elif callName == "getUsers":
      getUsers( dictIn )
   elif callName == "getUserInfo":
      getUserInfo( dictIn )
   elif callName == "getSearchFilter":
      getSearchFilter( dictIn )
   else:
      print("ERROR unknown function call: " + callName)
