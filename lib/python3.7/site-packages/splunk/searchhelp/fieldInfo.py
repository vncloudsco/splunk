from __future__ import absolute_import
from functools import cmp_to_key
from threading import Thread

import splunk.search as se
from splunk.searchhelp import utils


MAX_FIELD_THREADS = 5         # don't get field info, if we're already handling 5 other requests.  it's a nice to have and shouldn't abuse system
FIELD_INFO_MAX_RESULTS = 100  # ask for at most 100 search results
FIELD_INFO_MAX_FIELDS = 15    # display at most 15 interesting fields
FIELD_INFO_MAX_TIME = 5       # wait up to 5 seconds for a search for field info

g_field_info_cache = utils.AgedCache()  # global storage mapping searches to field info
g_threads = []

def usefulFields(output, sessionKey, namespace, user, search):
    """the fields ___ can help narrow does these results"""

    tcount = aliveThreadCount()
    if  tcount > MAX_FIELD_THREADS:
        #print("punting on getting field info: %s %s" % (tcount, len(g_threads)))
        return

    search = getSearch(search)
    key = (search, namespace, user)
    
    # if we've calculated the interesting fields,
    fields = g_field_info_cache.getValid(key)
    if fields != None:
        if len(fields) > 0:
            output['fields'] = fields
    else:
        # otherwise, calculate the interesting fields in a separate thread,
        # and we'll present the data next time we are called.
        # initialize value so multiple threads for same search aren't kicked off        
        g_field_info_cache[key] = "" 
        if safe(search):
            thread = FieldInfoThread(sessionKey, namespace, user, search, key)
            g_threads.append(thread)
            thread.start()

def aliveThreadCount():
    count = 0
    for t in g_threads:
        if t.isAlive():
            count += 1
    return count


# list of well-known, safe commands, which are public, do not write or
# effect any data.  for further prudence, all python commands are excluded.
SAFE_COMMANDS = set([
    'abstract', 'accum', 'addinfo', 'addtotals', 'af', 'anomalies',
    'anomalousvalue', 'append', 'appendcols', 'appendpipe', 'associate',
    'audit', 'autoregress', 'bucket', 'chart', 'cluster', 'concurrency',
    'contingency', 'convert', 'correlate', 'dbinspect', 'dedup', 'delta',
    'eval', 'eventcount', 'eventstats', 'extract', 'fieldformat',
    'fields', 'file', 'filldown', 'fillnull', 'format', 'head',
    'highlight', 'history', 'inputcsv', 'inputlookup', 'join', 'kmeans',
    'loadjob', 'localize', 'localop', 'lookup', 'makecontinuous',
    'makemv', 'map', 'metadata', 'metasearch', 'multikv', 'mvcombine',
    'mvexpand', 'nomv', 'outlier', 'rare', 'regex', 'relevancy', 'rename',
    'replace', 'return', 'reverse', 'rex', 'rtorder', 'savedsearch',
    'search', 'selfjoin', 'set', 'shape', 'sichart', 'sirare', 'sistats',
    'sitimechart', 'sitop', 'sort', 'stats', 'strcat', 'streamstats',
    'table', 'tail', 'timechart', 'top', 'transaction', 'typeahead',
    'typer', 'untable', 'where', 'xyseries'])

def safe(search):
    commandinfo = utils.getCommands(search, None)
    commands = [c.strip() for search in commandinfo for c, a in search ]
    # don't even think about outsmarting a subsearches
    if len(commandinfo) > 1:
        return False
    for cmd in commands:
        if cmd not in SAFE_COMMANDS:
            return False
    return True
    

def getSearch(search):
    search = search.strip()
    # empty search.  give some initial fields
    if len(search) == 0:
        search = 'search *'
    elif not search.startswith("|"):
        search = "search " + search
    # at end of search command, 
    if search[-1] in "|[]":
        search = search[:-1]        
    else:
        search = utils.allButLast(search)
        if len(search) == 0:
            search = 'search *'
    search +=  "| head %s" % FIELD_INFO_MAX_RESULTS
    return search

def ignoredField(fieldname):
    return fieldname == '' or fieldname == None or fieldname.startswith('_') or fieldname.startswith('date_') or fieldname == 'punct' or fieldname == 'timestartpos' or fieldname == 'timeendpos'


class FieldInfoThread(Thread):
    def __init__(self, sessionKey, namespace, user, search, key):
        Thread.__init__(self)
        self.sessionKey = sessionKey
        self.namespace  = namespace
        self.user       = user
        self.search     = search
        self.key        = key

    def run(self):
        try:
            results = se.searchAll(self.search, sessionKey=self.sessionKey, namespace=self.namespace, owner=self.user, status_buckets=0, required_field_list='*',
                                   auto_finalize_ec=100, 
                                   max_count=100, max_time=FIELD_INFO_MAX_TIME,
                                   enable_lookups=0, auto_cancel=2*FIELD_INFO_MAX_TIME                                   
                                   #exec_mode='blocking', 
                                   )
            fieldCounts = {}
            fieldValues = {}
            for result in results:
                for field in result:
                    if ignoredField(field):
                        continue
                    fieldCounts[field] = fieldCounts.get(field, 0) + 1
                    if field not in fieldValues:
                        fieldValues[field] = set()
                    fieldValues[field].add(str(result[field]))
                    
            fields = list(fieldCounts.keys())
            fields.sort(key=cmp_to_key(lambda x, y: (10 * len(fieldValues[y]) + fieldCounts[y]) - (10 * len(fieldValues[x]) + fieldCounts[x])))
            fieldInfo = fields[:FIELD_INFO_MAX_FIELDS]
            # store answer away
            g_field_info_cache[self.key] = fieldInfo
        except:
            pass
        try:
            if self in g_threads:
                g_threads.remove(self)
        except:
            pass
