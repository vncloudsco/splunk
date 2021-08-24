'''
 This is only a sample authentication script, and is NOT SUPPORTED by Splunk.

 For the most basic example of how to use scripted auth, please see dumbScripted.py
 This script serves as an example of how to interact between splunkd and PAM.

 Splunk will call this script to obtain several pieces of information.
 The information returned should be passed after "--status=success" over stdout.
 You must return --status==success for any successful call, otherwise Splunk
 assumes the call failed.

 Function breakdown
 Required:
     userLogin   : will be called on userLogin into splunk.
     getUserInfo : Get information about a particular user. ( username, realname, roles )
     getUsers    : Get a list of all users available.

 Optional Calls  :
    getSearchFilter : return a search filter for a given user. Called when the user searches.


 N.B.
 This script is not fully feature complete. It places all users at the admin level.
 If you wish to place users at different Role level you will have to modify the script
 to return the right role on depending on the user.
'''

# commonAuthBase contains constants and a basic mapping framework for users.
# plus any common imports to all scripts.
from commonAuth import *
from userMapping import *
import os


isMac = 0

'''
 This function will be called when a user enters their credentials in the login page in UI.
 Input:
       --username=<user> --password=<pass> 
 Output:
       On Success:
                    --status=success
       On Failure:
                   Anything but --status=success
'''
def userLogin( infoIn  ):
   command = []
   if isMac:
      command = ['dirt', '-u', str(infoIn['username']), '-p', str(infoIn['password'])]
   else:
      command = ['/path/to/pamauth', str(infoIn['username'])]
   
   # our check with pam is done with a setuid program called pamauth
   proc = subprocess.Popen( command,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE
                            )
   
   output = proc.communicate( infoIn['password'] )

   retCode = proc.wait()

   if retCode != 0:
       print(FAILED)
       return

   if isMac:
       if output[0].find('Call to checkpw(): Success') != -1:
           print(SUCCESS)
       else:
           print(FAILED)
       return

   # Not mac and we got a good return code: success
   print(SUCCESS)


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
   # just going to use /etc/passwd here but you may use any method you wish.
   FILE = open("/etc/passwd" ,"r")
   fileLines = FILE.readlines()

   outStr = SUCCESS

   if isMac:
      for line in fileLines:
         userBits = line.split( ":" )
         if len( userBits ) < 4:
            continue
         realname = userBits[4]
         if realname == "" :
            realname = userBits[0]

         username = userBits[0]
         if not username.startswith( '_' ):
            outStr = outStr + " --userInfo=" + str(userBits[2]) + ';' + str(userBits[0]) + ";" + str(realname) + ";"
            roleList = getUsersRole( userBits[0] )
            for roleItem in roleList:
               outStr = outStr + roleItem + ":"

   else:
      for line in fileLines:
         userBits = line.split( ":" )
         if userBits[6].find( '/bin/bash' ) != -1:
            realname = userBits[4]
            if realname == "" :
               realname = userBits[0]
            #                                  userId                   username                 realName
            outStr = outStr + " --userInfo=" + str(userBits[2]) + ';' + str(userBits[0]) + ";" + str(realname) + ";"
            
            roleList = getUsersRole( userBits[0] )
            for roleItem in roleList:
               outStr = outStr + roleItem + ":"


   print(outStr)



'''
 Gets the search filter for a given user.
 You must have the flag scriptSearchFilters set to 1 on the config for this function to be used.
 Input :
         --username=<username>
 Output:
         --search_filter=<filter>
 
'''
def getSearchFilter( infoIn ):
   filters = getUsersFilters( infoIn['username'])
   outStr = SUCCESS

   for i in filters:
      outStr = outStr + " --search_filter=" + str(i) 
      
   print(outStr)


  
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
