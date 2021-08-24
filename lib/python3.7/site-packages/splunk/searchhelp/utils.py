from __future__ import absolute_import
from __future__ import print_function
from builtins import object

import logging
import logging.handlers
import re
import time

import splunk.auth
import splunk.bundle


## import os
## logger.basicConfig(level=logger.DEBUG,
##                    format='%(asctime)s %(levelname)s %(message)s',
##                    filename=os.environ['SPLUNK_HOME'] + '/var/log/splunk/shelp.log',
##                    filemode='a')
logger = logging.getLogger('splunk.searchhelp.util')

ABUSE_PENALITY = 0.5


class AgedCache(object):
    # delete old cached values every 100 requests
    # keep list of fields for 10 minutes
    
    def __init__(self, clean_count=100, max_seconds=600):
        self.cache = {}  
        self.request_count = 0 
        self.clean_count = clean_count
        self.max_seconds = max_seconds
        
    def _cleanupCache(self):
        self.request_count += 1
        # if it's time
        if self.request_count % self.clean_count == 0:
            now = time.time()
            doomed = []
            # for each cached value that is too old, delete
            for key, (data_time, out) in self.cache.items():
                if data_time + self.max_seconds < now:
                    doomed.append(key)
            for d in doomed:
                if d in self.cache:
                    del self.cache[d]

    def getValid(self, key, default=None):
        '''return value if cache has a value that has not expired'''
        key = hash(key)
        self._cleanupCache()
        if key in self.cache:
            data_time, out = self.cache[key]
            if data_time + self.max_seconds > time.time():
                return out
        return default

    def __getitem__(self, key):
        self._cleanupCache()
        key = hash(key)
        return self.cache[key][1]
        
    def __setitem__(self, key, value):
        key = hash(key)        
        self.cache[key] = (time.time(), value)
        
    def __delitem__(self, key):
        key = hash(key)                
        del self.cache[key]
    def __iter__(self):
        return self.cache.__iter__()
    def __len__(self):
        return self.cache.__len__()
    def __str__(self):
        return self.cache.__str__()
    def __repr__(self):
        o = [x for x in self.cache]
        return o.__repr__()
    def __contains__(self, key):
        key = hash(key)                
        return key in self.cache
    def get(self, key, default=None):
        key = hash(key)                
        if key in self.cache:
            return self.__getitem__(key)
        return default
    def keys(self):
        return self.cache.keys()
        



# cache confs, as splunk.bundle is really, really slow
g_conf_cache = AgedCache(clean_count=10000)
g_running_gets = []

def getStanzas(confFile, sessionKey, username, namespace):
    
    key = (confFile, sessionKey, username, namespace)
    # if we have a cache
    vals = g_conf_cache.getValid(key)
    if vals != None:
        return vals
    
    # don't let dozens of simulateous users from a unit test get the same bundle at once
    skcount = g_running_gets.count(key)
    if skcount > 0:
        # start = time.time()  #### DEBUG        
        time.sleep(ABUSE_PENALITY * skcount) # sleep proportial to how abuse the sessionkey is
        ## logger.error("SHELPER TIMING %s GETSTANZAS: sleeping abusive session: %6f" % (sessionKey, time.time() - start)) #### DEBUG        
        # perhaps now we have a valid cached value.
        vals = g_conf_cache.getValid(key)
        if vals != None:
            return vals

    # start = time.time()  #### DEBUG
    try:
        g_running_gets.append(key)
        g_conf_cache[key] = splunk.bundle.getConf(confFile, sessionKey=sessionKey, namespace=namespace, owner=username)
        
    except Exception as e:
        msg = "Unable to get '%s' configuration for '%s' namespace: %s" % (confFile, namespace, e)
        logger.error(msg)
        #print("********* " + msg)
        raise Exception(msg)
    finally:
        # remove all copies of user session.
        while key in g_running_gets:
            g_running_gets.remove(key)

    ## logger.error("SHELPER TIMING %s GETSTANZAS: really-get-conf=%6f" % (sessionKey, time.time() - start)) #### DEBUG            
    return g_conf_cache[key]

def isPublic(stanza, name="unknown"):
    if "usage" not in stanza:
        # code is called by dict and bundle stanza objs
        if isinstance(stanza, dict):
            logger.warn("The %s command is missing a 'usage' value." % name)
        else:
            logger.warn("The %s command is missing a 'usage' value." % stanza.name)
        return False
    usage = stanza["usage"].strip().lower()
    return "public" in usage and not "deprecated" in usage

def isListed(stanza, prod_type=None):
    if prod_type == None or "optout-in" not in stanza:
        return True
    blacklist = stanza["optout-in"].strip().lower()
    return not prod_type in blacklist

def isGenerating(stanza):
    return stanza.get("generating", "false").lower().startswith("t")

def getAttr(stanzas, command, attr, defaultval):
    if not command.endswith("-command"):
        command += "-command"
    if command not in stanzas.stanzas:
        return defaultval
    stanza = stanzas[command]
    return stanza.get(attr, defaultval)

pubnames_cache = AgedCache()
gen_pubnames_cache = AgedCache()

def getAllCommands(stanzas, username, namespace, onlyGenerating = False, prod_type=None):
    global pubnames_cache, gen_pubnames_cache

    # caching based on username/namespace key
    cachekey = (username, namespace)


    if onlyGenerating:
        vals = gen_pubnames_cache.getValid(cachekey)
        if vals != None:
            return vals

    if not onlyGenerating:
        vals = pubnames_cache.getValid(cachekey)
        if vals != None:
            return vals

    publicnames = []
    stanzanames = stanzas.stanzas
    SEP = re.compile("[, ]+")
    for key in stanzanames:
        val = stanzas[key]
        if key.endswith("-command") and isPublic(val) and isListed(val, prod_type) and (not onlyGenerating or isGenerating(val)):
            name = key[0:-8]
            publicnames.append(name)
            # add aliases, if any
            aliasstr = stanzas[key].get('alias', None)
            if aliasstr != None:
                aliases = SEP.split(aliasstr)
                publicnames.extend(aliases)
    publicnames.sort()
    if onlyGenerating:
        val = gen_pubnames_cache[cachekey] = publicnames
    else:
        val = pubnames_cache[cachekey] = publicnames
    return val

ALIASMAP = {}
# return a dict mapping alias to preferred name
def getAliasMap(stanzas, prod_type=None):
    global ALIASMAP
    if len(ALIASMAP) > 0:
        return ALIASMAP
    aliasMap = {}
    SEP = re.compile("[, ]+")
    stanzanames = stanzas.stanzas
    for key in stanzanames:
        val = stanzas[key]
        if key.endswith("-command") and isPublic(val) and isListed(val, prod_type):
            name = key[0:-8]
            # make an alias from command to itself
            aliasMap[name] = name
            # if any aliases, map them to the preferred name
            aliasstr = stanzas[key].get('alias', None)
            if aliasstr != None:
                aliases = SEP.split(aliasstr)
                for alias in aliases:
                    aliasMap[alias] = name
    ALIASMAP = aliasMap
    return ALIASMAP

def getJustCommands(search, aliasMap):
    commands = getCommands(search, aliasMap)
    return [c.strip() for search in commands for c, a in search ]

# removes quotedparts
def removeQuotedParts(search):
    search = search.replace('\\"', "ESCAPED_QUOTE")
    # remove all quote pairs or last quote
    quotes = re.findall('".*?(?:"|$)', search)
    for quote in quotes:
        search = search.replace(quote, '-=X=-')
    search = search.replace("ESCAPED_QUOTE", '\\"')
    return search.strip(), quotes


def getCommands(search, aliasMap):
    seq = []
    search = search.strip()
    if not search.startswith("search") and not search.startswith('|'):
        search = "|search " + search
    if not search.startswith('|'):
        search = "| " + search
    search, quoteds = removeQuotedParts(search)
    subsearches = re.findall('\[(.*)\]', search) # greedy to get outtermost ]
    for subsearch in subsearches:
        search = search.replace(subsearch, '')
        subcommandseqs = getCommands("| " + subsearch, aliasMap)
        for sub in subcommandseqs:
            if len(sub) > 0:
                seq.append(sub)
    commandsAndArgs = re.findall("(?s)\|\s*([a-zA-Z0-9_]+)([^|\[\]]*)", search)
    commandsAndArgs = [(c.lower(), a) for c, a in commandsAndArgs]

    i = 0
    fixedCA = []
    # put extracted quotes back in
    for c, a in commandsAndArgs:
        while '-=X=-' in a and i < len(quoteds):
            a = a.replace('-=X=-', quoteds[i], 1)
            i += 1
        fixedCA.append((c, a))
    seq.append(fixedCA)
    
    if aliasMap != None:
        for search in seq:
            for c, a in search:
                lc = c.lower()
                if lc in aliasMap:
                    val = (c, a)
                    pos = search.index(val)
                    search.remove(val)
                    search.insert(pos, (aliasMap[lc], a))
    return seq
    
def escapePipeBrackets(search, unescape = False):
    replacements = (("|", "-=BAR=-"), ("[", "-=OPEN=-"), ("]", "-=CLOSE=-"))
    for replacement in replacements:
        if unescape:
            search = search.replace(replacement[1], replacement[0])            
        else:
            search = search.replace(replacement[0], replacement[1])
    return search

def escapeQuotedParts(search, unescape = False):
    search = search.replace('\\"', "-=ESCAPED_QUOTE=-")
    # escape all quote pairs or last quote
    quotes = re.findall('".*?(?:"|$)', search)
    for quote in quotes:
        search = search.replace(quote, escapePipeBrackets(quote, unescape))
    search = search.replace("-=ESCAPED_QUOTE=-", '\\"')
    return search.strip()


    
# basically the same as getCommands()[-1] but tolerant over unmatched ['s
# as the user is typing in
#    e.g. "|search 404 | sort [ metadata fields " --> metadata
#    e.g. "|search 404 | sort [ metadata fields] " --> sort
def getLastCommand(search, aliasMap):

    search = escapeQuotedParts(search)
    # remove all complete [subsearches] (we couldn't be inside one if it's complete)
    subsearches = re.findall('(\[.*?\])', search)
    for subsearch in subsearches:
        search = search.replace(subsearch, '')    
    lbar = search.rfind('|')
    # we might be in a partial subsearch -- e.g. "|search [crawl"
    lsqr = search.rfind('[')
    last = None
    if lbar >= 0:
        last = lbar
    if lsqr >= 0 and lsqr > lbar:
        last = lsqr
    if last == None:
        return None
    lastcommand = re.findall("(?s)\s*([a-zA-Z0-9_]+)(.*)", search[last:])
    if len(lastcommand) > 0:
        command = lastcommand[0][0]
        args = lastcommand[0][1].strip()
        args = escapeQuotedParts(args, True)
        
        if aliasMap != None and command in aliasMap:
            command = aliasMap[command]
        return command.lower(), args
    return None

def allButLast(search):
    comm = getLastCommand(search, None)
    if comm == None:
        return ""
    command, arg = comm
    try:
        from splunk.searchhelp import parser
        arg = parser.safeRegexLiteral(arg)
        match = re.search("(?i)[|[]\s*%s\s*%s" % (command, arg), search.lower())
    except Exception as e:
        logger.error("Unable to find last command due to regex problem for command: '%s' arg: '%s': %s" % (command, arg, e))
        match = None
        
    if match == None:
        return search
    return search[:match.start()]

def readText(filename):
    text = ""
    f = None
    try:
        f = open(filename, 'r')
        text = f.read()
    except Exception as e:
        logger.error('Cannot read file %s because: %s' % (filename, e))
    finally:
        if f != None:
            f.close()

    return text


def prettyList(l, conj="and"):
    output = ""
    llen = len(l)
    if llen == 0:
        return ""
    if llen == 1:
        return l[0]
    if llen == 2:
        return "%s %s %s" % (l[0], conj, l[1])
    for i, v in enumerate(l):
        if output != "":
            output += ", "
        if i == llen-1:
            output += conj +  " " 
        output += str(v)
    return output
    
def TEST_SESSION():
    return splunk.auth.getSessionKey('admin', 'changeme')

def TEST_NAMESPACE():
    return "search"

def _main():    
    import sys
    argc = len(sys.argv)
    argv = sys.argv
    if argc > 1:
        search = argv[1]
        prod = None
        if argc > 2:
            prod = argv[2]
        
        stz = getStanzas("searchbnf", TEST_SESSION(), 'admin', TEST_NAMESPACE())
        cmds = getAllCommands(stz, 'admin', TEST_NAMESPACE(), False, prod)
        print("All Commands ==> %s" % cmds)
    else:        
        print('Usage:')
        print(argv[0] + ' <search command> [<product>]')

if __name__ == '__main__':
    _main()
