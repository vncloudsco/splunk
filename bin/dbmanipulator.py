#
#  Version 4.0
# 
# This tool is to be used to add and remove databases when splunkd is stopped.
# 

from splunk.clilib.dbmanipulator_lib import *

if __name__ == "__main__":
    try:
        runFromCommandLine()
    except Exception as e:
        if str(e) == "0" or str(e) == "-1" :
            print("!!")
            sys.exit(int(str(e)))
        print("ERROR ::" + str(e))

        sys.exit(1)
