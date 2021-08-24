# This is a sample scripted auth implementation with a couple users with the password 'changeme'
from commonAuth import *

# Maps users to roles - All users must be lowercase
# Roles should be lowercase as well, but there's some uppercase for testing
umap = { 'scriptedadmin' : ['admin','user','foo'],
         'foobar' : ['user'],
         'upperuser' : ['UsEr'] }

def userLogin( args ):
    # Everyone's password is 'changeme'
    if args[USERNAME] in umap and args['password'] == 'changeme':
        print(SUCCESS)
    else:
        print(FAILED)

def getUserInfo( args ):
    # Use the same name for userId (deprecated), username, realname
    un = args[USERNAME]
    if un in umap:
        print(SUCCESS + ' --userInfo=' + un + ';' + un + ';' + un + ';' + ':'.join(umap[un]))
    else:
        print(FAILED)

def getUsers( args ):
    out = SUCCESS
    for u, r in umap.items():
        out += ' --userInfo=' + u + ';' + u + ';' + u + ';' + ':'.join(r)

    print(out)

def getSearchFilter( args ):
    # Ignore search filters
    if args[USERNAME] in umap:
        print(SUCCESS)
    else:
        print(FAILED)

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
