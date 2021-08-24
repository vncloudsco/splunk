from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from functools import cmp_to_key
#   Version 4.0
# 
import logging as logger
import re
import sys
import time

import splunk.search as se
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.searchhelp import describer
from splunk.searchhelp import utils

ABUSE_PENALITY = 0.5

# adds count maping command to next command
def addCount(nextmap, command, next):
    if not command in nextmap:
        nextmap[command] = {}
    nextcommmap = nextmap[command]
    if not next in nextcommmap:
        nextcommmap[next] = 0
    nextcommmap[next] += 1

# adds count for how many times command is seen
def addCommonCount(commands, command):
    commands[command] = commands.get(command, 0) + 1

def normalizeArgs(knownkeywords, arg):
    REGEX = re.compile("[a-zA-Z0-9_.-]+")
    matches = [match for match in REGEX.finditer(arg)]

    offset = 0
    for match in matches:
        keyword = match.group()
        start = match.start() + offset
        end = start + len(keyword)
        if not keyword in knownkeywords:
            arg = arg[0:start] + "VALUE" + arg[end:]
            offset += len("VALUE") - len(keyword)

    longfieldlists = re.findall("VALUE(?:,\s*VALUE){1,}", arg)
    for v in longfieldlists:
        arg = arg.replace(v, "VALUELIST")
    longfieldlists = re.findall("VALUE(?:\s+VALUE){1,}(?:\s+|$)", arg)
    for v in longfieldlists:
        arg = arg.replace(v, "VALUELIST ")
    arg = arg.replace(", ", " ")
    arg = arg.replace("  ", " ")
    arg = arg.replace("= ", "=")
    arg = arg.replace(" =", "=")
    arg = arg.replace("::", "=")

    arg = arg.replace("VALUELIST", "<value_list>")
    arg = arg.replace("VALUE", "<value>")
    
    return arg.strip()


def getPastSearches(user, sessionKey, namespace):

    bootstrapSearches = []

    try:
        bootsearchlog = make_splunkhome_path(['etc', 'system', 'static', 'bootstrapsearches.txt'])
        lines = utils.readText(bootsearchlog).split('\n')
        bootstrapSearches.extend(lines)
    except:
        logger.warn("Unable to get bootstrap search history")

    userHistory = []
    try:
        # get user's history of searches, ignoring those that didn't return any results
        q = "|history | head %s | search event_count>0 OR result_count>0 | dedup search | table search" % MAX_HISTORY
        results = se.searchAll(q, sessionKey=sessionKey, namespace=namespace, owner=user, spawn_process=False)
        userHistory = [str(r['search']) for r in results]
        if q in userHistory:
            userHistory.remove(q)
    except Exception as e:
        logger.warn("Unable to get search history: %s" % e)
        
    return bootstrapSearches, userHistory

END = "<RUN>"

g_cache = utils.AgedCache(clean_count=100, max_seconds=60)
MAX_HISTORY = 2000 # only get next data from last 2000 searches
g_running_sessions = []

def getNextData(user, stanzas, sessionKey, namespace):

    # if we have a cache of next data
    vals = g_cache.getValid(sessionKey)
    if vals != None:
        return vals

    # prevent 40 instances of the same session from hammering search at the same time. unlikely, outside the world of unit tests!
    skcount = g_running_sessions.count(sessionKey)
    if skcount > 0:
        time.sleep(ABUSE_PENALITY * skcount) # sleep proportial to how abusive the sessionkey is
        # perhaps now we have a valid cached value.
        vals = g_cache.getValid(sessionKey)
        if vals != None:
            return vals
    try:
        g_running_sessions.append(sessionKey)
        commandResults, searches = reallyGetNextData(user, stanzas, sessionKey, namespace)
    finally:
        # remove all copies of user session.
        while sessionKey in g_running_sessions:
            g_running_sessions.remove(sessionKey)
            
    # put calculated nextdata into cache
    g_cache[sessionKey] = (commandResults, searches)
    
    return commandResults, searches
        
        
        
def reallyGetNextData(user, stanzas, sessionKey, namespace):

    commandResults = []
    nextmap = {}
    commoncounts = {}
    argsmap = {}

    literals = describer.getLiterals(stanzas, user, namespace)
    bootstrapSearches, userSearches = getPastSearches(user, sessionKey, namespace)
    searches = bootstrapSearches + userSearches
    searches = searches[-MAX_HISTORY:]
    aliasMap = utils.getAliasMap(stanzas)
    badCommands = set()

    # for each search in file
    for search in searches:
        commandseqs = utils.getCommands(search, aliasMap)
        # for each sequency of commands for that search
        for j, commands in enumerate(commandseqs):
            commands.append((END, ""))
            # for each command
            for i, commandarg in enumerate(commands):
                command, arg = commandarg
                if command not in literals:
                    if command != END:
                        badCommands.add(command)
                arg = arg.strip()
                if command == END:
                    break
                addCount(argsmap, command, arg)
                addCount(nextmap, command, commands[i+1][0])
                addCommonCount(commoncounts, command)

    if len(badCommands) > 0:
        logger.warn("No searchbnf for these commands: %s!" % list(badCommands))

    commandAndCounts = list(commoncounts.items())
    commandAndCounts.sort(key=cmp_to_key(lambda x, y: y[1] - x[1]))
    for command, count in commandAndCounts:
        thisdata = {}
        commandResults.append(thisdata)
        thisdata['command'] = command
        thisdata['count'] = count

        thisargs = thisdata['args'] = []
        thisnexts = thisdata['nextcommands'] = []

        addSortedValueAndCounts(thisargs, argsmap[command])
        addSortedValueAndCounts(thisnexts, nextmap[command])

    return commandResults, userSearches

def addSortedValueAndCounts(result, valmap):
    
    valsAndCount = list(valmap.items())
    valsAndCount.sort( lambda x, y: y[1] - x[1] )
    total = 0
    for arg, count in valsAndCount:
        total += count
    for arg, count in valsAndCount:
        percent = "%.5s" % (100 * float(count) / total)
        result.append((arg, percent))



def _main():
    if len(sys.argv) > 1:
        search = sys.argv[1]
        cmds = utils.getCommands(search, None)
        comms = [c.strip() for search in cmds for c, a in search ]
        args = [a.strip() for search in cmds for c, a in search ]
        print("Commands: " + str(cmds))
        print("Commands: %s  Args: %s" % (comms, args))
    else:
        user = "admin"
        sessionKey = utils.TEST_SESSION()
        namespace = utils.TEST_NAMESPACE()
        #print(getPastSearches(user, None, sessionKey, namespace))
        bnf = utils.getStanzas("searchbnf", sessionKey, user, namespace)
        data, searches = getNextData(user, bnf, sessionKey, namespace)
        for cmd in data:
            print("\t%s" % cmd)

    
if __name__ == '__main__':
    _main()
