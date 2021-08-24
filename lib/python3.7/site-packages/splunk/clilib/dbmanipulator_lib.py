from __future__ import print_function
#   Version 4.0

from splunk.util import cmp
import os
import sys
import xml.etree.cElementTree as et
import time
import re
import splunk.clilib.cli_common as comm
import errno

dirre = re.compile("(\d+)_(\d+)_\d+")

import shutil

TIME_FORMAT = "%m/%d/%Y:%H:%M:%S"

btool_list = "\"" + os.path.join(os.environ["SPLUNK_HOME"], "bin", "btool") + "\" indexes list"
btool_add = "\"" + os.path.join(os.environ["SPLUNK_HOME"], "bin", "btool") + "\" indexes add"
btool_delete = "\"" + os.path.join(os.environ["SPLUNK_HOME"], "bin", "btool") + "\" indexes delete \"\" "

usageInfo =  """    * Index Commands
    *  index-list
          o This lists the names of the indexes currently installed, and indicates the current default index.

    * database-clean <<indexname>>
          o This cleans all indexes or just the specified indexname if provided.

    * index-create [indexname] [directory]
          o This creates a new index with indexname in directory.

    * python index-delete [indexname] <<newdefaultindex>>
          o This deletes a index indexname. If the default index is deleted it will prompt for newdefaultindex if not provided.

    * python index-default [indexname]
          o Sets the default index to indexname

          """

#  Added xxx since this is the valid usage I just dont want it to show.
xxxusageInfo =  """    *  python dbmanipulator.py --list
          o This lists the names of the databases currently installed, and indicates the current default index.

    * python dbmanipulator.py --clean <<databasename>>
          o This cleans all databases or just the specified databasename if provided.

    * python dbmanipulator.py --create [databasename] [directory]
          o This creates a new database with databasename in directory.

    * python dbmanipulator.py --delete [databasename] <<newdefaultdatabase>>
          o This deletes a database databasename. If the default database is deleted it will prompt for newdefaultdatabase if not provided.

    * python dbmanipulator.py --default [databasename]
          o Sets the default database to databasename
          
    * python dbmanipulator.py --showdefault 
          o Prints the default database name

    * python dbmanipulator.py --migrate [databasename] <<newdirectory>>
          o Moves database name to a new directory, prompts for newdirectory if not provided.

    * python dbmanipulator.py --hibernate [databasename]
          o Removes a database from the config file but does not remove the data.

    * python dbmanipulator.py --revive [directoryname] [databasename]
          o Adds an existing database directory structure to the config file as databasename.
          
    * python dbmanipulator.py --verify <<databasename>>
          o Verifys that the directory structure for <<databasename>> is intact. If no <<databasename>> is supplied verifys all databases.

    * python dbmanipulator.py --validate <<databasename>>
          o Validates that the directory structure for <<databasename>> is intact. If a problem is found the directory structure is restored. If no <<databasename>> is supplied validates all databases.

    * python dbmanipulator.py --migrateconfig [2.0.x multiindexer.xml]
          o Migrates an old 2.0.x multiindexer.xml config file to the 2.1 format

    * python dbmanipulator.py --resurrect <<directory>> <<index>> 
          o Resurrects a single directory to the specified index

    * python dbmanipulator.py --resurrect  <<archive_directory>> <<index>> <<from_time>> <<end_time>> 
          o Resurrects any directories in archive_directory that contain events in the time interval
          o Time format %m/%d/%Y:%H:%M:%S (mm/dd/yyyy/:hh:mm:ss)
          
    * python dbmanipulator.py --ascend <index> <from_time> <end_time>
          o Removes resurrected directories from the specified index
          """    

def getdbs(databases):
    lines = os.popen(btool_list, 'r').readlines()
    database = {}

    for line in lines:
        line = line.strip()
        if line[0] == '[':
            database = {}
            current_db = line.strip("[]")
            #print("current db: %s" % (current_db))
            if current_db != "default":
                database["name"] = current_db
                databases.append(database)
            continue

        # Skip over lines until we find a [foo] line denoting a db
        if not len(database):
            continue

        split_line = line.split("=")
        if len(split_line) != 2:
            print('Suspicious entry in indexes.conf: %s' % line)
            #somethings wrong here...it should be of the format key = value
            #anyways, we'll let the caller of this function detect it's invalid

            #a mere presence of '=' does not indicate an error. '=' is a valid char in a filename. May not be what the user intended though
            #print a warning...
            try:
                n = split_line[0]
            except:
                n = ''
            try:
                v = ''.join(split_line[1:])
            except:
                v = ''
        else:
            (n, v) = line.split("=")

        database[n.strip()] = v.strip()
        
def getNumericalInput(default):
    input = input().strip()
    if input:
        return int(input)
    else:
        return default

def fixDbPath(dbPath):
    for variable in os.environ:
        dbPath = os.environ[variable].join(dbPath.split("$"+variable))
    return dbPath

def updateConf(dbs):
    dbPath = os.environ["SPLUNK_DB"]
    f = os.popen(btool_add, 'w')
    if f == None:
        print("Popen of btool_add failed")
    for x in dbs:
#        print("looking at db: %s" % x["name"])
        f.write("[%s]\n" % (x["name"]))
        for k in x:
            if x[k] == None:
                continue
            if k != "name":
                out = k + " = " + x[k].replace(dbPath, "$SPLUNK_DB") + "\n"
                f.write(out)
        f.write("\n")


def deleteDatabase(databaseName, removeFromFileSystem, newDefaultDatabase=None):
#    print("deleteDatabase called")
    databases = []
    getdbs(databases)
    db = databases[0]
    dbFound = 0
    #Check if we are about to delete the default database
    if db["defaultDatabase"] == databaseName: 
        if newDefaultDatabase == None:
            print("You are about to remove the default database please enter the new default database")
            newDefaultDatabase = input().strip()
            newDefaultDbFound = 0
            for database in databases:
                if newDefaultDatabase == database["name"]:
                    newDefaultDbFound = 1
            if not newDefaultDbFound:
                raise Exception("Unable to find database " + newDefaultDatabase)
    for database in databases:
        database["defaultDatabase"] = newDefaultDatabase #Set the new default
#        print("looking at %s" % database["name"])
        if cmp(databaseName, database["name"]) == 0:
            dbFound = 1
            print("Removing " + database["name"])
            databases.remove(database)
            if removeFromFileSystem:                
                try:
                    for parmName in ("homePath", "coldPath", "thawedPath"):
                        fixedPath = fixDbPath(database[parmName])
                        print("\tDeleting " + fixedPath)
                        delDirContents(fixedPath)
                            
                # SPL-27013 provide information on windows permissions
                # workaround
                except IOError as e:
                    if os.name == 'nt' and e.errno == 5 and  e.strerrno == 'Access is denied':
                        print("Permissions error during clean. Please manually delete var\\lib\\splunk subdirectories. SPL-27013")
                    raise # reraise

    if not dbFound:
        raise Exception("Unable to find database " + databaseName)
    os.system(btool_delete + databaseName)

def delDirContents(dirPath):
    #SPL-18700
    if os.path.exists(dirPath):
      for item in os.listdir(dirPath):
        fullPath = os.path.join(dirPath, item)
        if os.path.isdir(fullPath):
            comm.remove_tree(fullPath)
        else:
            comm.remove_file(fullPath)
    
def listDatabases(showDirectories = True):
    print("List databases called")
    databases = []
    getdbs(databases)
    for database in databases:
        dbName = database["name"]
        if database["defaultDatabase"] == dbName:
            dbName = dbName + " * Default *"
        if(not showDirectories):
            print(dbName)
        else:
            print(dbName +  "\n\t" +  fixDbPath(database["homePath"]) +  "\n\t" + fixDbPath(database["coldPath"]) + "\n\t" + fixDbPath(database["thawedPath"]))

def showDefaultDatabase():
    databases = []
    getdbs(databases)
    for database in databases:
        dbName = database["name"]
        if database["defaultDatabase"] == dbName:
            print(dbName)
            return
    print("No default database")
        

def setDefaultDatabase(databaseName):
    print("set default database called")
    databases = []
    getdbs(databases)
    dbFound = 0
    for database in databases:
        if database["name"] == databaseName:
            dbFound = 1
    if not dbFound:
        raise Exception("Unable to find database " + databaseName)
    for database in databases:
        database["defaultDatabase"] = databaseName
    updateConf(databases)

def isDisabledIndex(dbDict):
  return "disabled" in dbDict and comm.getBoolValue("disabled", dbDict["disabled"])

def verifyDatabase(databaseName):
    # print("verify database called")
    databases = []
    getdbs(databases)
    dbFound = 0
    successful = ""

    paths = []
    for database in databases:        
        if isDisabledIndex(database):
            continue
        if databaseName == None or databaseName == database["name"]:
            if len(successful) > 0:
                successful += ", "
            successful += database["name"] 
            dbFound = 1

            hot = fixDbPath(database["homePath"])
            cold = fixDbPath(database["coldPath"])
            thawed = fixDbPath(database["thawedPath"])

            os.stat( hot )
            os.stat( cold )
            os.stat( thawed )

            paths.append( hot )
            paths.append( cold )
            paths.append( thawed )
    
    paths.sort()
    previousPath = ""
    for p in paths:
        if previousPath != "" and previousPath == p:
            raise Exception("In indexes.conf, '%s' used multiple times, please repair before restarting splunk"%p )
        previousPath = p

    #print("Verified databases: " + successful)
    if not dbFound:
        raise Exception("Unable to find database " + databaseName)


def validateDatabase(databaseName):
    #print("validateDatabase called")
    databases = []
    getdbs(databases)
    dbFound = 0
    print("\tChecking databases...")
    successful = ""
    for database in databases:        
        if isDisabledIndex(database):
            continue
        if databaseName == None or databaseName == database["name"]:
            if len(successful) > 0:
                successful += ", "
            successful += database["name"] 
            dbFound = 1
            dirsToCreate = []
            # collect dirs for this index that don't exist.
            for pathKey in ("homePath", "coldPath", "thawedPath"):
                path = fixDbPath(database[pathKey])
                if not os.path.exists(path):
                    dirsToCreate.append(path)
            # print dirnames & create dirs.
            for path in dirsToCreate:
                try:
                    os.makedirs(path)
                except Exception as e:
                    raise Exception('Could not create path %s appearing in indexes.conf: %s' % (path, str(e)))

    verifyDatabase(None)

    print("\tValidated databases: " + successful)

    if not dbFound:
        raise Exception("Unable to find database " + databaseName)

def addDatabase(databaseName, newPath, isNewDb, maxDataSizeMegs=None, maxWarmDBCount=None, frozenTimeOutPeriodSecs=None, maxTotalDataSize=None):
    print("add database called")
    databases = []
    getdbs(databases)
    dbFound = 0
    paths = []
    if not isNewDb and not newPath:
        raise Exception("No path specified to revive")
    for database in databases:        
        if databaseName == database["name"]:
            dbFound = 1
        paths.append(fixDbPath(database["homePath"]))
        paths.append(fixDbPath(database["coldPath"]))
        paths.append(fixDbPath(database["thawedPath"]))
    if newPath[-1] != os.path.sep:
        newPath = newPath + os.path.sep   
    if isNewDb and dbFound:
        raise Exception("There is already a database named " + databaseName)
    if isNewDb:
        if newPath + "db" in paths:
            raise Exception("There is already a database with files in " + newPath + ".")
        if newPath + "colddb" in paths:
            raise Exception("There is already a database with files in " + newPath + ".")
        try:
            os.stat(newPath)
            print(newPath + " exists, about to delete all contents ok ? [y/N]")
            ok = input().strip()
            if ok == "y" or ok == "yes" or ok == "Y":
                delDirContents(newPath)
            else:
                sys.exit(1)
        except:
            os.mkdir(newPath)
        os.mkdir(newPath + "db")            
        os.mkdir(newPath + "colddb")
        os.mkdir(newPath + "thaweddb")
    else:
        os.stat(newPath)            
        os.stat(newPath + "db")            
        os.stat(newPath + "colddb")
        try:
            os.stat(newPath + "thaweddb")
        except:
            os.mkdir(newPath + "thaweddb")

    if maxDataSizeMegs == None:
        print("Please enter the max data size in MBs (40)")
        maxDataSizeMegs = getNumericalInput(default=40)
        #print(maxDataSizeMegs)
    if maxWarmDBCount == None:
        print("Please enter the max warm db count (100)")
        maxWarmDBCount = getNumericalInput(default=100)
        #print(maxWarmDBCount)
    if frozenTimeOutPeriodSecs == None:
        print("Please enter the frozen time out period in secs (188697600)")
        frozenTimeOutPeriodSecs = getNumericalInput(default=188697600)
        #print(frozenTimeOutPeriodSecs)
    if maxTotalDataSize == None:
        print("Please enter the max total data size in MBs (40000)")
        maxTotalDataSize = getNumericalInput(default=40000)
        #print(maxTotalDataSize)

    newDB = {}
    newDB["name"] = databaseName
    newDB["homePath"] = newPath + "db"
    newDB["coldPath"] = newPath + "colddb"
    newDB["thawedPath"] = newPath + "thaweddb"    
    newDB["tempPath"] = comm.tmpDir()
    newDB["maxWarmDBCount"] = str(maxWarmDBCount)
    newDB["frozenTimePeriodInSecs"] = str(frozenTimeOutPeriodSecs)
    newDB["maxDataSize"] = str(maxDataSizeMegs)
    newDB["maxTotalDataSizeMB"] = str(maxTotalDataSize)
    
    # updateConf wants a list of databases to be passed in - it then goes ahead
    # and writes the entire list out to local/indexes.conf.  this was incorrect
    # behavior.  now we only pass in the one that was created (or revived), but
    # we still have to pass it in list form - so, single-element list. :)
    updateConf([newDB])
    
def migrateConfig(oldConfilePath, newConfigPath = None):
    if newConfigPath == None :
        newConfigPath = oldConfilePath
    shutil.copy(oldConfilePath, oldConfilePath + ".bak") #Make a backup
    databases = []
    getdbs(databases)
    for database in databases:
        if(database["thawedPath"] != None):
            print("Database :  " + database["name"] + " already migrated .. skipping")
            continue
        maxTotalDataSizeMB = et.SubElement(database, "maxTotalDataSizeMB")
        maxTotalDataSizeMB.text = "50000" #50 GiB by default
        coldPath = database["coldPath"]
        cp = coldPath.text
        thawedPath = cp[:cp.find("colddb")] + "thaweddb"
        fixedThawedPath = fixDbPath(thawedPath)
        if not os.access(fixedThawedPath, os.F_OK):
            os.mkdir(fixedThawedPath)
        thawedPath = et.SubElement(database, "thawedPath")
        thawedPath.text = thawedPath        
    
    print("Writing out migrated  " + newConfigPath)
    updateConf(databases)

def moveDatabase(databaseName, newPath):
    print("moveDatabase called")
    databases = []
    getdbs(databases)
    dbFound = 0
    for database in databases:
        if database["name"] == databaseName:
            if not newPath:
                print("Please enter the new path for " + databaseName)
                newPath = input().strip()

            if newPath[-1] != os.path.sep:
                newPath = newPath + os.path.sep            
            
            dbFound = 1
            try:
                os.stat(newPath)
                print(newPath + " exists, about to delete all contents ok ? [y/N]")
                ok = input().strip()
                if ok == "y" or ok == "yes" or ok == "Y":
                    delDirContents(newPath)
                else:
                    sys.exit(1)
            except:
                os.mkdir(newPath)

            os.mkdir(newPath + "db")            
            os.mkdir(newPath + "colddb")
            
            for parmName, leafDir in (("homePath", "db"), ("coldPath", "colddb"), ("thawedPath", "thaweddb")):
              fixedPath = fixDbPath(database[parmName])
              # find all files/dirs in this dir...
              for item in os.listdir(fixDbPath(database[parmName])):
                # and move each one to the new destination.
                shutil.move(os.path.join(fixedPath, item), os.path.join(newPath, leafDir))

            database["homePath"] = newPath + "db"
            database["coldPath"] = newPath + "colddb"
            database["thawedPath"] = newPath + "thaweddb"
            updateConf(databases)
    if not dbFound:
        raise Exception("Unable to find database " + databaseName)

def resurrectDatabaseDirectory(databaseName, pathToDirectory):
    databases = []
    getdbs(databases)
    for database in databases:
        if database["name"] == databaseName:
            thawedpath = fixDbPath(database["thawedPath"])
            homepath = fixDbPath(database["homePath"])
            splunk_home = os.environ["SPLUNK_HOME"]
            if  splunk_home[-1] != os.path.sep:
                splunk_home = splunk_home + os.path.sep

            if pathToDirectory[-1] == os.path.sep:
                pathToDirectory = pathToDirectory[:-1]
            return os.spawnv(os.P_WAIT, splunk_home+"bin/resurrectionJoe", (splunk_home+"bin/resurrectionJoe", "--resurrect", homepath, pathToDirectory, thawedpath))
    else:
        return -1

def unresurrectDatabaseDirectory(databaseName, pathToDirectory):    
    databases = []
    getdbs(databases)
    for database in databases:
        if database["name"] == databaseName:
            thawedpath = fixDbPath(database["thawedPath"])
            homepath = fixDbPath(database["homePath"])
            splunk_home = os.environ["SPLUNK_HOME"]
            if  splunk_home[-1] != os.path.sep:
                splunk_home = splunk_home + os.path.sep
            return os.spawnv(os.P_WAIT, splunk_home+"bin/resurrectionJoe", (splunk_home+"bin/resurrectionJoe", "--unresurrect", homepath, pathToDirectory))
    else:
        return -1

def getMatchingDirs(databaseName, archivePath, startTimeStr, endTimeStr):
    startTime = 0
    endTime = 0
    try:
        startTime = time.mktime(time.strptime(startTimeStr, TIME_FORMAT))
    except:
        print("Could not parse the time " + startTimeStr + " expected the format  %m/%d/%Y:%H:%M:%S (mm/dd/yyyy/:hh:mm:ss) ")
        return -1

    try:
        endTime = time.mktime(time.strptime(endTimeStr, TIME_FORMAT))
    except:
        print("Could not parse the time " + endTimeStr + " expected the format  %m/%d/%Y:%H:%M:%S (mm/dd/yyyy/:hh:mm:ss) ")
        return -1    

    dirsToReturn = []
    allDirs = []

    if archivePath[-1] != os.path.sep:
        archivePath = archivePath + os.path.sep

    allDirs = os.listdir(archivePath)

    for dir in allDirs:
        if os.path.isdir(archivePath + dir) and dirre.findall(dir):
            dirEnd, dirStart = dirre.findall(dir)[0]
            dirEnd = float(dirEnd)
            dirStart = float(dirStart)
            if dirEnd < endTime and dirEnd > startTime:
                dirsToReturn.append(archivePath + dir)
            elif dirStart > startTime and dirStart < endTime:
                dirsToReturn.append(archivePath + dir)
    
    return dirsToReturn

def resurrectDatabaseRange(databaseName, archivePath, startTimeStr, endTimeStr):
    dirsToRes = getMatchingDirs(databaseName, archivePath, startTimeStr, endTimeStr)
    for dir in dirsToRes:
        print("resurrecting " + dir)
        if resurrectDatabaseDirectory(databaseName, dir) == -1:
            print("ERROR resurrecting " + dir)
            
def unresurrectDatabaseRange(databaseName, startTimeStr, endTimeStr):
    dirsToUnRes = []
    databases = []
    getdbs(databases)
    for database in databases:
        if database["name"] == databaseName:
            thawedpath = fixDbPath(database["thawedPath"])
            dirsToUnRes = getMatchingDirs(databaseName, thawedpath, startTimeStr, endTimeStr)

    for dir in dirsToUnRes:
        print("unresurrecting " + dir)
        if unresurrectDatabaseDirectory(databaseName, dir) == -1:
            print("ERROR unresurrecting " + dir)
    else:
        return -1

def usage():
    print(usageInfo)

def runFromCommandLine():
    if(len(sys.argv) < 2):
        usage()
        sys.exit(0)
    action = sys.argv[1]
    
    if action.find("--") == 0:
        action = action[2:]
    else:
        usage()
        sys.exit(1)

    if action == 'list':
        listDatabases()
    elif action == 'resurrect':
        if len(sys.argv) == 4:
            if resurrectDatabaseDirectory(sys.argv[3], sys.argv[2]) == -1:
                sys.exit(1)
        elif len(sys.argv) == 6:
            if resurrectDatabaseRange(sys.argv[3], sys.argv[2], sys.argv[4], sys.argv[5]) == -1:
                sys.exit(1)
        else:
            usage()
            sys.exit(1)            
    elif action == 'unresurrect':
        if len(sys.argv) == 5:
            if unresurrectDatabaseRange(sys.argv[2], sys.argv[3], sys.argv[4]) == -1:
                sys.exit(1)
        else:
            usage()
            sys.exit(1)
    elif action == 'delete':
        if len(sys.argv) == 3:
            databaseToDelete = sys.argv[2]            
            deleteDatabase(databaseToDelete, True)
        elif len(sys.argv) == 4:
            databaseToDelete = sys.argv[2]            
            newDefaultDB = sys.argv[3]            
            deleteDatabase(databaseToDelete, True, newDefaultDB)
        else:
            sys.stderr.write("ERROR :: No database to delete specified\n")
            #usage()
            sys.exit(1)
    elif action == 'hibernate':
        if len(sys.argv) == 3:
            databaseToDelete = sys.argv[2]            
            deleteDatabase(databaseToDelete, False)
        else:
            sys.stderr.write("ERROR :: No database to hibernate specified\n")
            #usage()
            sys.exit(1)            
    elif action == 'default':
        if len(sys.argv) == 3:
            databaseToDefault = sys.argv[2]            
            setDefaultDatabase(databaseToDefault)
        else:
            sys.stderr.write("ERROR :: No database to set to default specified\n")
            #usage()
            sys.exit(1)
    elif action == 'migrate':
        if len(sys.argv) > 2:
            databaseToMigrate = sys.argv[2]
            pathToMigrateTo = None
            if len(sys.argv) > 3:
                pathToMigrateTo = sys.argv[3]
            moveDatabase(databaseToMigrate, pathToMigrateTo)
        else:
            sys.stderr.write("ERROR :: No database to migrate specified\n")
            usage()
            sys.exit(1)
    elif action == 'verify':
        databaseToVerify = None
        if len(sys.argv) == 3:
            databaseToVerify = sys.argv[2]
        verifyDatabase(databaseToVerify)
    elif action == 'validate':
        databaseToValidate = None
        if len(sys.argv) == 3:
            databaseToValidate = sys.argv[2]
        validateDatabase(databaseToValidate)
    elif action == 'migrateconfig':
        configToMigrate = None
        if len(sys.argv) == 3:
            configToMigrate = sys.argv[2]
        else:
            sys.stderr.write("ERROR :: No configuration to migrate specified\n")
            usage()
            sys.exit(1)            
        migrateConfig(configToMigrate)        
    elif action == 'add' or action == 'create':
        if len(sys.argv) >= 3:
            databaseToAdd = sys.argv[2]
            if databaseToAdd == 'all':
                sys.stderr.write("ERROR :: 'all' is not a valid database name\n")
                sys.exit(1)                
            if len(sys.argv) >= 4:
                pathToAdd = sys.argv[3]
                addDatabase(databaseToAdd, pathToAdd, True)
            else:
                sys.stderr.write("ERROR :: No path for database " + databaseToAdd + " specified \n")
                usage()
                sys.exit(1)                
        else:
            sys.stderr.write("ERROR :: No database to revive specified\n")
            usage()
            sys.exit(1)
    elif action == 'showdefault':
        showDefaultDatabase()
    elif action == 'revive':
        if len(sys.argv) >= 3:
            databaseToAdd = sys.argv[2]
            if databaseToAdd == 'all':
                sys.stderr.write("ERROR :: 'all' is not a valid database name\n")
                sys.exit(1)                
            if len(sys.argv) >= 4:
                pathToAdd = sys.argv[3]
                addDatabase(databaseToAdd, pathToAdd, False)
            else:
                sys.stderr.write("ERROR :: No path for database " + databaseToAdd + " specified \n")
                usage()
                sys.exit(1)                
        else:
            sys.stderr.write("ERROR :: No database to revive specified\n")
            usage()
            sys.exit(1)
    else:
        usage()
        sys.exit(1)
