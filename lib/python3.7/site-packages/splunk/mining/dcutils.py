from __future__ import print_function
# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.
from builtins import range
from functools import cmp_to_key
import os
import sys
import re
import pickle
import logging
import logging.handlers
import configparser
import codecs
import datetime 
import traceback
import time

import splunk
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.util import format_local_tzoffset
import splunk.Intersplunk
import splunk.util as util

LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
class LoggingFormatterWithTimeZoneOffset(logging.Formatter):
    converter=datetime.datetime.fromtimestamp
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            correct_tz_time = format_local_tzoffset()
            s = "%s,%03d %s" % (t, record.msecs, correct_tz_time)
        return s

defMaxBytes = 26214400
defMaxBackupIndex = 10
defLogLevel = "INFO"

scannedMaxBytes = defMaxBytes
scannedMaxBackupIndex = defMaxBackupIndex
scannedLogLevel = defLogLevel

config_cp = configparser.ConfigParser(delimiters=('='), strict=False)
config_cp.readfp(codecs.open(make_splunkhome_path(['etc', 'log.cfg']), mode='r', encoding="utf-8-sig"))

try:
    scannedLogLevel = config_cp.get('python', 'splunk')
    scannedLogLevel = scannedLogLevel.split('#')[0] # pylint: disable=E1103
except configparser.NoOptionError:
    scannedLogLevel = defLogLevel

try:
    scannedMaxBackupIndex = config_cp.get('splunkd', 'appender.python.maxBackupIndex')
    scannedMaxBackupIndex = scannedMaxBackupIndex.split('#')[0] # pylint: disable=E1103
except configparser.NoOptionError:
    scannedMaxBackupIndex = defMaxBackupIndex

try:
    scannedMaxBytes = config_cp.get('splunkd', 'appender.python.maxFileSize')
    scannedMaxBytes = scannedMaxBytes.split('#')[0] # pylint: disable = E1103
except configparser.NoOptionError:
    scannedMaxBytes = defMaxBytes


level = logging.getLevelName(scannedLogLevel)
if not isinstance(level, int):
    level = logging.getLevelName(defLogLevel)

try:
    scannedMaxBackupIndex = int(scannedMaxBackupIndex)
except:
    scannedMaxBackupIndex = defMaxBackupIndex

try:
    scannedMaxBytes = int(scannedMaxBytes)
except:
    scannedMaxBytes = defMaxBytes


my_logger = logging.getLogger('splunk')
pythonLogHandler = logging.handlers.RotatingFileHandler(filename=os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'python.log'), mode='a', maxBytes=scannedMaxBytes, backupCount=scannedMaxBackupIndex)
pythonLogHandler.setFormatter(LoggingFormatterWithTimeZoneOffset(LOGGING_FORMAT))
my_logger.setLevel(level)
my_logger.addHandler(pythonLogHandler)

# Creates error results or logs the error message 
# If graceful is, (0, "0", None, "f"/"F", or "false") the input results are returned
# and an error message is logged in python.log otherwise an error search results is returned
# Use this method when doing error-checking/reporting
#
def getErrorResults(results, graceful, message):
    if(graceful == None or graceful == 0 or graceful == "0" or str(graceful).lower() == "f" or str(graceful).lower() == "false"):
        results = splunk.Intersplunk.generateErrorResults(message)
    else:
        logging.error(message)
    return results  

def getLogger():
    return my_logger

def getLoggerHandler():
    return pythonLogHandler

# returns a dictionary of the arguments which given to python
# recognizes stuff like: python script key=value key2=value

def getArgValues():
    argvals = dict()
    if len(sys.argv) >= 1:
        args = sys.argv[1:]
        for arg in args:
            pieces = arg.split( "=", 1 )
            if len(pieces) > 1:
                argvals[pieces[0].lower()] = pieces[1]
                
    return argvals

def looksLikeWord(token):
    upper = lower = 0
    for c in token:
        if not c.isalpha():
            return False
        if c.isupper():
            upper += 1
        else:
            lower += 1
    return len(token) > 2 and (upper == 0 or lower == 0 or upper == 1)


# returns maps of terms and phrases to their count
def tokenize(text, phrasesP, wordsOnlyP):
    vector = dict()
    tokens = re.compile(r'\W+').split(text)
    lastToken = "[START]"
    for token in tokens:
        if len(token) == 0:
            continue
        isWord = looksLikeWord(token)
        if not wordsOnlyP or isWord:
            incCount(vector, token, 1)
        if wordsOnlyP and not isWord:
            if token[0].isdigit():
                token = "#"
            else:
                token = "?"
        if phrasesP:
            incCount(vector, lastToken + '-' + token, 1)
        lastToken = token
    return vector


def enoughLines(filename, minLines):
    try:
        f = open(filename, 'r')
        lineCount = 0
        while len(f.readline()) > 0 and  lineCount < minLines:
            lineCount += 1
        f.close()
        #print(filename + " " + str(lineCount) + " " + str(minLines))
        return lineCount >= minLines
    except Exception as e:
        print('Error reading file:' + filename + ' cause: ' + str(e))
        return False
    
def numsort(x, y):
    if y[1] > x[1]:
        return 1
    elif x[1] > y[1]:
        return -1
    else:
        return 0
    #lambda x, y: y[1] - x[1]
# returns terms that occur between min and max times.
def getBestTerms(terms, minCount=0, maxCount=99999999999):
    tokensAndCounts = list(terms.items())
    tokensAndCounts.sort(key=cmp_to_key(numsort))
    result = list()
    for i in range(0, len(terms)):
        count = tokensAndCounts[i][1]
        if minCount <= count <= maxCount:
            result.append(tokensAndCounts[i][0])
    return result

def incCount(map, val, count):
    if val in map:
        map[val] += count
    else:
        map[val] = count

def mapget(dict, key, default):
    if key in dict:
        return dict[key]
    return default

def incrementMapValue(map, key, inc):
    if key in map:
        map[key] += inc
    else:
        map[key] = inc
    return map[key]


def addToMapList(map, key, value):
    if key in map:
        l = map[key]
    else:
        l = list()
        map[key] = l
    safeAppend(l, value)
    return l


def addToMapSet(map, key, value):                                               
    if key in map:
        s = map[key]
    else:
        s = set()
        map[key] = s
    s.add(value)
    return s


def safeAppend(list, val):
    if val not in list:
        list.append(val)

def safePrepend(list, val):
    if val not in list:
        list.insert(0, val)
    print(str(list))

def getLine(file):
    text = file.readline()
    if len(text) == 0:
        return None
    return text[0:len(text)-1]

def loadLines(filename):
     try:
          f = open(filename, 'r')
          lines = f.readlines()
          f.close()
          return lines
     except Exception as e:
          print('Cannot read file: ' + filename + ' cause: ' + str(e))
          return []

def fileExists(filename):
    try:
        f = open(filename, 'r')
        f.close()
        return True
    except:
        return False
    
def readText(filename):
    try:
        f = open(filename, 'r')
        text = f.read()
        f.close()
        return text
    except Exception as e:
        print('Cannot read file: ' + filename + ' cause: ' + str(e))
        return ""

def writeText(filename, text):
    try:
        f = open(filename, 'w')
        f.write(text)
        f.close()
    except Exception as e:
        print('Cannot write file: ' + filename + ' cause: ' + str(e))

def getKeywords(filename):
    keywords = set()
    lines = loadLines(filename)
    for line in lines:
        keywords.add(line.strip().lower())
    return keywords

def getKeywordMap(filename):
    keywords = dict()
    lines = loadLines(filename)
    for line in lines:
        line = line.strip().lower()
        if len(line) == 0:
            continue
        if '=' in line:
            equals = line.index('=')
            keyword = line[0:equals].strip()
            syntext = line[equals+1:]
            wsSyns = syntext.split(',')
            keywords[keyword] = keyword
            for syn in wsSyns:
                keywords[syn.strip()] = keyword
        else:
            keywords[line] = line
    return keywords



def removeNL(lines):
    for i in range(0, len(lines)):
        line = lines[i]
        if line.endswith('\r\n'):
            lines[i] = line[0:len(line)-2]
        elif line.endswith('\n'):
            lines[i] = line[0:len(line)-1]
        elif line.endswith('\r'):
            lines[i] = line[0:len(line)-1]
            
    return lines

def pickleReadObject(filename):
    try:
        return pickle.load(open(filename, 'r'))
    except:
        print('Unable to load object from file: ' + filename)
        return None

def pickleWriteObject(filename, obj):
    try:
        pickle.dump(obj, open(filename, 'w'))
    except Exception as e:
        print('Unable to write object to file: ' + filename + " because " + str(e))



def compilePatterns(formats):
    compiledList = list()
    for f in formats:
        #print(str(f))
        compiledList.append(re.compile(f, re.I))
    return compiledList

def getTimeInfoTuplet():
    timePatterns = datePatterns = maxYear = minYear = None
    timestampconfigfilename = make_splunkhome_path(['etc', 'anonymizer', 'anonymizer-time.ini'])
    text = readText(timestampconfigfilename)
    text = text.replace('\\n', '\n').replace('\n\n', '\n')
    exec(text)
    compiledTimePatterns = compilePatterns(timePatterns)
    compiledDatePatterns = compilePatterns(datePatterns)
    timeInfoTuplet = [compiledTimePatterns, compiledDatePatterns, minYear, maxYear]
    return timeInfoTuplet
