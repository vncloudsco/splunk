from __future__ import absolute_import
from __future__ import print_function
#   Version 4.0

import os
import subprocess
import sys

from builtins import range
import splunk.mining.dcutils as dcutils
import splunk.clilib.bundle_paths as bundle_paths

CONFIG_FILE = bundle_paths.make_splunkhome_path(['etc', 'findlogs.ini'])
print("Using configuration file found: " + CONFIG_FILE)


def loadConfig(filename):
     try:
          f = open(filename, 'r')
          lines = f.readlines()
          f.close()
          config = dict()
          for line in lines:
              if not line.startswith("#") and len(line.strip()) > 0:
                  vals = [v.strip() for v in line.split("=")]
                  if len(vals) != 2:
                      print("Ignoring line without valid \"attr = val1, val2, ...\":\n\t" + line)
                  else:
                      key, val = vals
                      valvals = [v.strip() for v in val.split(", ")] 
                      if key.endswith("SET"):
                          config[key] = set(valvals)
                      else:
                          config[key] = valvals
                          
          return config
     except KeyboardInterrupt as e:
          raise e
     except Exception as e:
          print('Cannot read file: ' + filename + ' cause: ' + str(e))
          return None

def listToRegex(vals):
    return "(" + "|".join(vals) + ")"


def makeSafeFile(filename):
     return filename.replace(" ", "\ ").replace("'", "\\'").replace("\"", "\\\"")



def executeGetFileTypes(cmd, types):
     if len(cmd) == 0:
          return
     if sys.platform.startswith("win"):
          exit("Error: Windows platform not supported for this deprecated command.  Use the 'crawl' search operator.")
     cmd = "classify manyfiles " + cmd + "|grep Classified"
     output = subprocess.getstatusoutput(cmd)[1]
     lines = output.split("\n")
     for line in lines:
          vals = line.split("\t")
          if len(vals) == 3:
               filename = vals[1]
               ftype = vals[2]
               types[filename] = ftype
                    



def getFileTypes(files, parentDir=None):
     types = {}
     cmd = ""
     for fname in files:
          if parentDir != None:
               fname = parentDir + fname
          size = len(cmd)
          if size < 1000:
               cmd += " '" + makeSafeFile(fname) + "'"
          else:
               executeGetFileTypes(cmd, types)
               cmd = ""
     executeGetFileTypes(cmd, types)               
     return types


def getOldFileTypes(parentdir, files):
     types = {}
     for fname in files:
         sourcetype = getFileType(parentdir + fname)
         if sourcetype != None:
             types[fname] = sourcetype
     return types


def getFileType(filename):

    if sys.platform.startswith("win"):
        exit("Error: Windows platform not supported for this deprecated command.  Use the 'crawl' search operator.")
     
    filename = "'" + makeSafeFile(filename) + "'"
    cmd = "classify " + filename + "|grep sourcetype"
    output = subprocess.getstatusoutput(cmd)[1]
    if "sourcetype" in output:
        return output.split("\t")[-1]
    return None
    


def throwAwayFilesIfDirectoryCoversIt(config, files):

     doomed = set()
     for file1 in files:
          for file2 in files:
               if file1 != file2 and file1.endswith("/"):
                    if file2.startswith(file1):
                         #print("Doomed: " + file2)
                         doomed.add(file2)
     for d in doomed:
          if not isCompressed(config, d):
               files.remove(d)
     return files

     
# find promising directories and use instead of individual files
# sort results by recentcy*best_directories
def findCommonDirectories(config, files, collapseThreshold):

     files = throwAwayFilesIfDirectoryCoversIt(config, files)
     ## need to write!
     counts = {}
     for fname in files:
          last = fname.rfind("/")
          if last > 0:
               dirname = fname[:last+1]
               dcutils.addToMapSet(counts, dirname, fname)

     collapsedFiles = []
     for dirname, files in list(counts.items()):
          if len(files) >= collapseThreshold:
               collapsedFiles.append(dirname)
               #print("Collapsed dir %s from %s" % (dirname,  files))
          else:
               collapsedFiles.extend(files)
     return collapsedFiles


def recursivelyFindCommonDirectories(config, files, collapseThreshold):
     compressed = []
     regular = []
     for fname in files:
          if isCompressed(config, fname):
               compressed.append(fname)
          else:
               regular.append(fname)
               
          
     for i in range(0, 4):
          #print("recurse: %u" % i)
          oldlen = len(regular)
          regular = findCommonDirectories(config, regular, collapseThreshold)
          if len(regular) == oldlen:
               break
     return regular + compressed


def isCompressed(config, filename):
    for ext in config['PACKED_EXTENSIONS']:
        if filename.endswith(ext):
            return True
    return False


def getDaysSizeKPairs(config):

     try:
          pairs = []
          vals = config['DAYS_SIZEK_PAIRS']
          for val in vals:
               day, size = val.split(",")
               pairs.append((int(day), int(size)))
          return pairs
     except:
          print('Using default DAYS_SIZEK_PAIRS because given value is invalid')
          return [(30, 1)]
