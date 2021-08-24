from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from builtins import range
import re, sys, time, traceback, difflib, json

import logging as logger

import splunk.entity
import splunk.rest
from splunk.searchhelp import describer
from splunk.searchhelp import didYouKnow
from splunk.searchhelp import didYouMean
from splunk.searchhelp import fieldInfo
from splunk.searchhelp import next
from splunk.searchhelp import parser
from splunk.searchhelp import utils

## import os
## logger.basicConfig(level=logger.DEBUG,
##                    format='%(asctime)s %(levelname)s %(message)s',
##                    filename=os.environ['SPLUNK_HOME'] + '/var/log/splunk/shelp.log',
##                    filemode='a')

# Searchhelp
#
#
#  search error | ? report on top ips
#
# - suggest terms
#    - you might also be interested in ___?
#    - the ____ field can help narrow does these results
# - suggest operators
#   - matches search against savedsearch snippets (not valid save searches, but named/tagged/described snippets of search)
#     - [most common values of a field] = | top FIELD
#     - [make a graph to chart the max values against two other fields] = | stats max(FIELD) by _time | timechart FIELD2 by FIELD3
#   - match search operator against tags/description of operator: "|report " -- did you mean chart or timechart?
#   - order typeahead/search assistant by most common operators that follow an operator. e.g. search->stats,sort.  stats->chart,timechart
#     - get order grabbing all search commands used on tiny.
# - suggest searches
#   - keep history of user's searches that return results and suggest them when query is similar.
#     - ideally replace fields and values. e.g. stored: "search ip=10* | top ip" queried "search source=*error*"  .. suggest: "search source=*error* | top source"
# - generate a description from each search:
#   - "search ip=10* source=*mail*| top ip | chart ip" -- "search for events where ip starts with '10' and contains 'mail'.  From those results, calculate the most frequent ip addresses. And from those results,  graph a chart of the ip values".  simpler -- "search for ip=10* source=*mail* and calculate most frequent values, and then make a chart."
#
# - suggest optimizations. swapping of operators.  search | sort FIELD | head N  --> search | sort N FIELD
#                                                  search | sort | fields -> search | fields | sort  (test case 20% faster)

g_cache = utils.AgedCache(clean_count=5000, max_seconds=60)


def help(sessionKey, namespace, user, search, insertpos=None, earliest_time=None, latest_time=None, count=10, max_time=None, servers=None,
         useTypeahead=False, showCommandHelp=True, showCommandHistory=True, showFieldInfo=True, prod_type=None):

    cachekey = (sessionKey, namespace, user, search, insertpos, earliest_time, latest_time, count, max_time, servers,
                useTypeahead, showCommandHelp, showCommandHistory, showFieldInfo)

    out = g_cache.getValid(cachekey)
    if out != None:

        # check to see if we've updated our field info
        if (splunk.util.normalizeBoolean(showFieldInfo)):
            if len(out['fields']) == 0:
                usersquery = search
                if usersquery.startswith("search "):
                    usersquery = usersquery[len("search "):]
                # add field info
                fieldInfo.usefulFields(out, sessionKey, namespace, user, usersquery)
        return out

    g_cache[cachekey] = out = doHelp(sessionKey, namespace, user, search, insertpos, earliest_time, latest_time, count, max_time, servers, useTypeahead, showCommandHelp, showCommandHistory, showFieldInfo, prod_type)

    return out


# help outputs dic with these keys:
#    notices : list of string notices
#    fields : list of interesting fields
#    args : list of (arg,perc) pairs
#    nexts : list of (next,perc) pairs
#    command : dict of strings ('name', 'shortdesc', 'details', 'syntax') and 'examples' pair of (example, comment)

def doHelp(sessionKey, namespace, user, search, insertpos=None, earliest_time=None, latest_time=None, count=10, max_time=None, servers=None,
         useTypeahead=False, showCommandHelp=True, showCommandHistory=True, showFieldInfo=True, prod_type=None):
    """
    "did you mean ___?"
    "did you know ___?"
    "the 'sort' operator takes blah arguments and does blah"
    "you might also be interested in ___?"
    "the fields ___ can help narrow does these results"
    "these past searches are similar to your search"
    "these saved searches are similar to your search"
    "you are searching for ip and host and then deduplicating by host"
    "your search would be faster if you ..."
    """

    originalsearch = search
    if insertpos == None: # no insertion point, use end
        insertpos = len(search)
    else:
        try:
            insertpos = int(insertpos)
        except:
            insertpos = len(search)

    search = search[:insertpos].strip()

    if search == "":
        search = "| search"
    elif not search.startswith("|"):
        search = "| " + search

    usersquery = originalsearch
    if usersquery.startswith("search "):
        usersquery = usersquery[len("search "):]
    queryprefix = utils.allButLast(usersquery)
    # defaults
    output = { 'notices': [], 'fields': [], 'args': [], 'nexts': [], 'autonexts':[], 'autocomplete':[], 'autocomplete_match':'', 'command':{}, 'typeahead': [],
               'search': usersquery, 'searchprefix': queryprefix, 'allcommands': [], 'savedsearches': [], 'arg_typeahead':[], 'has_field_args':False}
    try:
        
        ## overallstart = start = time.time()

        bnf = utils.getStanzas("searchbnf", sessionKey, user, namespace)

        ###################
        ## now = time.time()
        ## timing_bnf = now - start
        ## start = now
        ###################
        
        output['allcommands'] = utils.getAllCommands(bnf, user, namespace, prod_type=prod_type)

        ###################
        ## now = time.time()
        ## timing_allcommands = now - start
        ## start = now
        ###################
        
        aliasMap = utils.getAliasMap(bnf, prod_type)

        ###################
        ## now = time.time()
        ## timing_aliasmap = now - start
        ## start = now
        ###################
        
        if (splunk.util.normalizeBoolean(useTypeahead)):
            suggestSearchTypeahead(output, search, usersquery, count, max_time, earliest_time, latest_time, servers, namespace, user)

        ###################
        ## now = time.time()
        ## timing_typeahead = now - start
        ## start = now
        ###################            
        
        firstTermShouldBeCommand(output, search, aliasMap)

        ###################
        ## now = time.time()
        ## timing_firstterm = now - start
        ## start = now
        ###################            
        
        didYouMean.help(output, bnf, sessionKey, namespace, user, search, usersquery)

        ###################
        ## now = time.time()
        ## timing_didyoumean = now - start
        ## start = now
        ###################            
        
        didYouKnow.help(output, aliasMap, user, search)

        ###################
        ## now = time.time()
        ## timing_didyouknow = now - start
        ## start = now
        ###################            
        
        relatedPastSearches(output, user, search)

        ###################
        ## now = time.time()
        ## timing_relatedpastsearches = now - start
        ## start = now
        ###################            
        
        relatedSearches(output, sessionKey, namespace, user, search)

        ###################
        ## now = time.time()
        ## timing_relatedsearches = now - start
        ## start = now
        ###################            

        if (splunk.util.normalizeBoolean(showCommandHelp)):
            commandHelp(output, user, search, aliasMap, bnf, prod_type)

        ###################
        ## now = time.time()
        ## timing_commandhelp = now - start
        ## start = now
        ###################            
    
        nextCommand(output, sessionKey, namespace, user, search, usersquery, queryprefix, aliasMap, bnf, splunk.util.normalizeBoolean(showCommandHistory))

        ###################
        ## now = time.time()
        ## timing_nextcommand = now - start
        ## start = now
        ###################            
        
        relatedTerms(output, user, search)

        ###################
        ## now = time.time()
        ## timing_relatedterms = now - start
        ## start = now
        ###################            
        
        if (splunk.util.normalizeBoolean(showFieldInfo)):
            fieldInfo.usefulFields(output, sessionKey, namespace, user, usersquery)


        ###################
        ## now = time.time()
        ## timing_usefulfields = now - start
        ## start = now
        ###################            

            
        describeSearch(output, user, search)


        ###################
        ## now = time.time()
        ## timing_describesearch = now - start
        ## start = now
        ###################            


        suggestOptimizations(output, user, search)


        ###################
        ## now = time.time()
        ## timing_optimize = now - start
        ## start = now
        ###################            
        
        argTypeahead(output, sessionKey, namespace, user, bnf, search)

        ###################
        ## now = time.time()
        ## timing_argtypeahead = now - start
        ## start = now
        ###################            

        ## overall_time = now - overallstart
        ## msg = "aliasmap=%6f, allcommands=%6f, argtypeahead=%6f, bnf=%6f, commandhelp=%6f, describesearch=%6f, didyouknow=%6f, didyoumean=%6f, firstterm=%6f, nextcommand=%6f, optimize=%6f, relatedpastsearches=%6f, relatedsearches=%6f, relatedterms=%6f, typeahead=%6f, usefulfields=%6f" % (timing_aliasmap, timing_allcommands, timing_argtypeahead, timing_bnf, timing_commandhelp, timing_describesearch, timing_didyouknow, timing_didyoumean, timing_firstterm, timing_nextcommand, timing_optimize, timing_relatedpastsearches, timing_relatedsearches, timing_relatedterms, timing_typeahead, timing_usefulfields)
        ## logger.error("SHELPER TIMING: %s overall=%6f -- %s" % (sessionKey, overall_time, msg))
        
    except Exception as e:
        msg = "! Error in search assistant: %s" % e
        msg += traceback.format_exc()
        output['notices'].insert(0, msg)

        logger.error(msg)
        # output['notices'].insert(0,msg)

    return output


def argTypeahead(output, sessionKey, namespace, user, bnf, search):
    try:
        commandAndArgs = utils.getLastCommand(search, None)
        if commandAndArgs != None:
            cmd, args = commandAndArgs
            typeahead = []
            stanza = cmd + '-command'
            s = describer.cleanSyntax(describer.recurseSyntax(stanza, bnf, bnf[stanza], {}, True, 0, 1500)) # recurse syntax up to 1500 chars
            e = parser.getExp(s)

            tokens = {}
            hasFields = False
            parser.getTokens(e, tokens)
            getvalue = False
            for a, v in tokens.items():
                if a == cmd: continue

                if a.startswith('<') and a.endswith('>') and 'field' in a.lower() or v == '<field>':
                    hasFields = True

                if args.endswith('='):
                    args = args[:-1]
                    getvalue = True
                b1, replacement, b2 = getReplacement(args, a)
                # only show keywords when we match because we have so low confidence about their correctness in any given spot of a search command
                if replacement != '':
                    prev = len(replacement)+1
                    if prev > len(args) or not args[-prev].isalpha():
                        #print("%s\t: %s ('%s')" % (a,v, replacement))
                        if getvalue:
                            if v == '<bool>':
                                v = ['true', 'false']
                            a = v
                            v = 'datatype'
                        if isinstance(a, list):
                            for val in a:
                                typeahead.append((val, 'choice', replacement))
                        else:
                            if isinstance(v, list):
                                v = '<list>'
                            typeahead.append((a, v, replacement))

            output['has_field_args'] = hasFields
            output['arg_typeahead'] = typeahead

    except Exception as e:
        msg = str(e) + traceback.format_exc()
        output['notices'].insert(0, msg)

def suggestSearchTypeahead(output, search, usersquery, count, max_time, earliest_time, latest_time, servers, namespace, user):

    commandAndArgs = utils.getLastCommand(search, None)
    if commandAndArgs != None:
        command, args = commandAndArgs
        if command == "search":
            output['typeahead'] = getTypeaheadTerms(args, usersquery, count, max_time, earliest_time, latest_time, servers, namespace, user)

def firstTermShouldBeCommand(output, search, aliasMap):
    m = re.match("\s*\|\s*search\s+([^ ]+)", search)
    if m:
        groups = m.groups()
        if len(groups) > 0:
            firstArg = groups[0].lower()
            if firstArg in aliasMap:
                output['notices'].append('Your first search term is also a search command.  Did you mean " | %s"?' % firstArg)

def getTypeaheadTerms(q, usersquery, count, max_time, earliest_time, latest_time, servers, namespace, user):
    typeaheadTerms = []

    # don't bother with empty requests
    if not q or q.strip() in ('', '*'):
        return typeaheadTerms
                 
    requestArgs = { 'output_mode': 'json', 'prefix': q, 'count': count, 'max_time': max_time}
    if earliest_time: requestArgs['earliest_time'] = earliest_time
    if latest_time: requestArgs['latest_time'] = latest_time
    if servers: logger.warn('typeahead server spec not implemented yet')

    uri = splunk.entity.buildEndpoint('search', 'typeahead', namespace=namespace, owner=user)
    response = None
    try:
        response, content = splunk.rest.simpleRequest(uri, getargs=requestArgs, raiseAllErrors=True)
    except Exception as e:
        logger.error('Searchhelper could not fetch typeahead terms')
        logger.exception(e)

    # server says we have data #
    if response != None and response.status == 200:
        output = json.loads(content)['results']

        matchcount = len(output)
        for item in output:
            try:
                count = item['count']
                token = item['content']

                # unclear why this happens. ledion said it's a bug he fixed, but it's still there.
                # we're getting typeahead with quotes around the whole value (e.g. "sourcetype=foo")
                #if token.startswith('"') and token.endswith('"'):
                #    token = token[1:-1]
                replacement, match, fullmatch = getReplacement(usersquery, token)
                #print("Q: %s CONTENT: %s REPLACEMENT %s MATCH %s FULLMATCH %s" % (q, token, replacement, match, fullmatch))
                # if we only have one typeahead match and the user completely typed it, it's not a prefix,
                # then don't bother showing any typeahead
                if matchcount == 1 and fullmatch:
                    return []
                if replacement != None:
                    typeaheadTerms.append((token, replacement, match, count))
            except Exception as e:
                logger.error('unable to parse typeahead values: %s' % e)

    return typeaheadTerms



# ignore replacements past N characters.  we're getting absurd 2500 character searches.
MAX_ARG_REPLACEMENT = 250

def getReplacement(q, token):
    ''' given a search q and a typeahead token, returns 1) what the
    new search would be if the end of q is expanded by token with
    typeahead. 2) that part of q that matches token. 3) whether the
    match completely covers the end of the string and is not a prefix.

    this is complicated by the fact that a search of source=/tmp might
    return source="/tmp/foo", which is not a superstring, therefore I
    have to do some shinnanigans to allow matching to allow for
    variance in quoting and also return the correct matching suffix,
    which has quotes even though the original user q did not have it.

    same problem for user typeing index::m and typeahead returning index="main"

    q:     * sourcetype = sta
    token: sourcetype="start"

    -->
    replacement: * sourcetype="start"
    match:       sourcetype = sta
    '''
    # PUNT ON ABSURDLY LONG ARGUMENTS FOR REPLACEMENT
    if len(q) < MAX_ARG_REPLACEMENT:
        qlower = q.lower()
        for i in range(0, len(q)):
            prefix = qlower[i:]
            if normalizedMatch(token, prefix):
                return q[:i] + token, prefix, (token == prefix)

    # should (almost) never happen
    return q + token, '', False



def findNotInQuotes(text, find, first=True):
    index = -1
    inQuote = False
    l = len(text)
    i = 0
    while i < l:
        ch = text[i]
        if ch == '\\':
            i += 1
        elif ch == '"':
            inQuote = not inQuote
        elif text[i:].startswith(find) and not inQuote:
            index = i
            if first: break
        i += 1
    return index
        
        
def normalizedMatch(full, prefix):
    '''
    full:  sourcetype="stash"
    prefix: sourcetype=sta
    prefix: sourcetype = sta
    prefix: sourcetype = "sta
    prefix: sourcetype::sta
    '''
    # get a more meaningful match, not " <thematch>"
    first = prefix[0]
    if first.isspace() or first == '=':
        return False

    # simple case of exact match. prevents problem when passed "tag::" and matching against tag::source="foo"
    if full.startswith(prefix):
        return True

    #orig = prefix
    equals = findNotInQuotes(prefix, '=', False)  # equals = prefix.find("=")
    colon  = findNotInQuotes(prefix, '::', False) # colon  = prefix.find("::")
    # if user typed in an equals or a colon
    if equals >= 0 or colon >= 0:
        if equals < 0: equals = 999999
        if colon  < 0: colon  = 999999
        # if the colon comes first, change the string from 'foo::bar' to 'foo="bar'
        if colon < equals:
            prefix = prefix[:colon] + '="' + prefix[colon+2:]
        else:
            # else if the equals comes first, change the string from 'foo = "bar' to 'foo="bar'
            # by getting stripping 'foo ' to 'foo' and stripping ' "bar' to 'bar' and then combining 
            attr = prefix[:equals].strip()
            if len(prefix) == equals+1:
                val = ''
            else:
                val = prefix[equals+1].strip()
            if val.startswith('"'): val = val[1:]
            prefix = '%s="%s' % (attr, val)
    #if full.startswith(prefix):
    #    print("%s  --> %s  \t matches %s" % (orig, prefix, full))
    return full.startswith(prefix) or full.startswith('"%s' % prefix)



def commandHelp(output, user, search, aliasMap, bnf, prod_type=None):
    commandAndArgs = utils.getLastCommand(search, aliasMap)
    if commandAndArgs != None:
        command, args = commandAndArgs
        description = describer.describeCommand(bnf, command, True, prod_type)
        if description != None:
            output['command'] = description


MAX_NEXT_COMMANDS = 10
MAX_NEXT_ARGS = 10

def fuzzSearch(search):
    return search.replace('"', '').replace(' ', '').lower()

def nextCommand(output, sessionKey, namespace, user, search, usersquery, queryprefix, aliasMap, bnf, showargs):

    ## overallstart = start = time.time()
    ## timing_last_command = 0
    ## timing_all_commands = 0
    ## timing_get_next_data = 0
    ## timing_get_args = 0
    ## timing_add_commands = 0
    ## timing_past_matches = 0
    ## timing_sort_past_matches = 0
    
    atPipe = False

    # if search ends in "|", don't give args for last command, but
    # give next information from previous commandd
    if search[-1] == "|":
        search = search[:-1]
        showargs = False
        atPipe = True
        
    nextcommands = []
    typeaheadcommands = []
    
    commandAndArgs = utils.getLastCommand(search, aliasMap)
    
    ###################
    ## now = time.time()
    ## timing_last_command = now - start
    ## start = now
    ###################

    
    if commandAndArgs == None:
        # list all generating commands.
        # make a list() copy so we don't trash it by adding search
        typeaheadcommands = list(utils.getAllCommands(bnf, user, namespace, True))

        ###################
        ## now = time.time()
        ## timing_all_commands = now - start
        ## start = now
        ###################

        
    else:        
        command, args = commandAndArgs
        data, pastsearches = next.getNextData(user, bnf, sessionKey, namespace)

        ###################
        ## now = time.time()
        ## timing_get_next_data = now - start
        ## start = now
        ###################

        
        for datum in data:
            if datum['command'] == command:
                typeaheadcommands = [x for x, y in datum['nextcommands'] if x != "<RUN>"]
                if showargs:

                    matchingargs = []
                    fs = fuzzSearch(usersquery)
                    for arg, perc in datum['args']:
                        replacement = "%s | %s %s" % (queryprefix, command, arg)
                        fr = fuzzSearch(replacement)
                        if fr.startswith(fs) and fr != fs:
                            matchingargs.append((arg, perc))
                    output['args'] =  matchingargs
                    #output['args'] =  datum['args']
                break

        ###################
        ## now = time.time()
        ## timing_get_args = now - start
        ## start = now
        ###################
            
        # now add in all commands that were not already added
        if command in aliasMap:
            # adding all the other commands not already added
            for thiscommand in utils.getAllCommands(bnf, user, namespace):
                if thiscommand not in nextcommands and thiscommand not in typeaheadcommands:
                    nextcommands.append(thiscommand)

        ###################
        ## now = time.time()
        ## timing_add_commands = now - start
        ## start = now
        ###################


        # look for pastsearches that the current search is a subset of  (like firefox url autocomplete looking for any term)
        usersearch = normalizeSearch(search)

        # if user didn't enter anything don't match on "search" or "search *", just get most recent
        if usersearch == "" or usersearch == "*":
            pastMatches = [userifySearch(p) for p in pastsearches]
        else:
            pastMatches = [userifySearch(pastsearch) for pastsearch in pastsearches if normalizedSearchMatch(True, usersquery, pastsearch)]
            pastMatches.extend([userifySearch(pastsearch) for pastsearch in pastsearches if normalizedSearchMatch(False, usersquery, pastsearch)])

        ###################
        ## now = time.time()
        ## timing_past_matches = now - start
        ## start = now
        ###################
            
        # dedup
        pastMatches = sorted(list(set(pastMatches)), key=pastMatches.index)         
        output['autocomplete'] = pastMatches[:10] # just the 10 most recent
        output['autocomplete_match'] = usersearch

        ###################
        ## now = time.time()
        ## timing_sort_past_matches = now - start
        ## start = now
        ###################


    # new.  only show next command if we aren't showing the args for the current command.
    # use will see next commands when they type "|"
    if atPipe:
        # keep only those that alias to themselves -- i.e., don't show aliases
        nextcommands = [x for x in nextcommands if aliasMap.get(x, '') == x]
        typeaheadcommands = [x for x in typeaheadcommands if aliasMap.get(x, '') == x]
        s = usersquery.strip()
        if '|' in s:
            s = s[:s.rindex('|')].strip()
        # make triplets of (command, description, replacement)
        output['autonexts'] = [(x, utils.getAttr(bnf, x, "shortdesc", ""), s + " | " + x) for x in typeaheadcommands]
        output['nexts'] = [(x, utils.getAttr(bnf, x, "shortdesc", ""), s + " | " + x) for x in nextcommands]


    ## overall_time = now - overallstart
    ## msg = "last_command=%6f, all_commands=%6f, get_next_data=%6f, get_args=%6f, add_commands=%6f, past_matches=%6f, sort_past_matches=%6f" % (timing_last_command, timing_all_commands, timing_get_next_data, timing_get_args, timing_add_commands, timing_past_matches, timing_sort_past_matches)
    ## logger.error("SHELPER TIMING: %s NEXTCOMMAND: overall=%6f -- %s" % (sessionKey, overall_time, msg))


# return true if usersearch is a substring of normalized pastsearch (but not equal)
def normalizedSearchMatch(isPrefix, usersearch, pastsearch):
    pastsearch = normalizeSearch(pastsearch)
    if isPrefix:
        return pastsearch.startswith(usersearch)
    else:
        return usersearch in pastsearch and usersearch != pastsearch

# take past searches of one form and make them how the user would type them
# "search foo | sort bar" --> "foo | sort bar"
# "crawl | sort bar"      --> "| crawl | sort bar"
def userifySearch(search):
    if search.startswith("|"):
        return search
    if search.startswith("search "):
        return search[7:]
    return "| " + search

def normalizeSearch(search):
    normalizedsearch = search.lower().strip()
    prefixes = ["| search ", "|search ", "search "]
    for prefix in prefixes:
        if normalizedsearch.startswith(prefix):
            normalizedsearch = normalizedsearch[len(prefix):]
            break
    else:
        if search == "|search" or search == "| search":
            normalizedsearch = ""
    return normalizedsearch.strip()


def relatedTerms(output, user, search):
    """you might also be interested in ___?"""
    return 

def relatedSearches(output, sessionKey, namespace, user, search):
    """these saved searches are similar to your search"""

    savedsearches = utils.getStanzas("savedsearches", sessionKey, user, namespace)
    searchmap = {}
    for name in savedsearches:
        ssearch = savedsearches[name].get('search', None)
        if ssearch != None:
            searchmap[ssearch.lower()] = (name, ssearch)
    searches = list(searchmap.keys())
    bestmatches = difflib.get_close_matches(search.lower(), searches, cutoff=0.65)
    if len(bestmatches) == 0:
        return 
    
    output['savedsearches'] = [(searchmap[match][0], searchmap[match][1]) for match in bestmatches if match!=search]



# security issue or showing other user's searches?
def relatedPastSearches(output, user, search):
    """these past searches are similar to your search"""
    # ideally replace fields and values.
    #    stored: "search ip=10* | top ip"
    #    queried "search source=*error*" ..
    #    suggest: "search source=*error* | top source"
    
    return


# generate a description from each search
def describeSearch(output, user, search):
    # search ip=10* source=*mail*| top ip | chart ip
    #
    # "search for events where ip starts with '10' and contains 'mail'.
    # From those results, calculate the most frequent ip addresses. And
    # from those results, graph a chart of the ip values".  simpler --
    # "search for ip=10* source=*mail* and calculate most frequent
    # values, and then make a chart.
    return 
    

def suggestOptimizations(output, user, search):
    # swapping of operators.
    #      search | sort FIELD | head N  --> search | sort N FIELD
    #      search | sort | fields -> search | fields | sort  (test case 20%-400% faster)
    return 



# returns likely next arguments and command
def nextHelp(output, user, search):
    #   - order typeahead/search assistant by most common operators that
    #     follow an operator. e.g. search->stats,sort.
    #     stats->chart,timechart
    #   - get order grabbing all search commands used on tiny.
    return 



def testtypeahead():
    qs = [
        'search index',
        
        'search index=',
        'search index="',
        'search index="_i',
        'search index=_i',

        'search index =',
        'search index ="',
        'search index ="_i',
        'search index =_i',

        'search index= ',
        'search index= "',
        'search index= "_i',
        'search index= _i',

        'search index = ',
        'search index = "',
        'search index = "_i',
        'search index = _i',

        'search * sourcetype=sta',
        'search * sourcetype = sta',
        'search * sourcetype = "sta',
        'search * sourcetype="sta',
        'search * sourcetype::sta',
        
        'search index=',
        
        'search index=_internal index=_',

        'search tag::',
        ]

    bads = ['index=index', 'ii', 'tag::tag', 'indexindex']
    
    user = 'admin'
    for q in qs:
        out = help(utils.TEST_SESSION(), utils.TEST_NAMESPACE(), user, q, None, None, None, 10, None, None, 
                    useTypeahead=True, showCommandHelp=True, showCommandHistory=True, showFieldInfo=True)
        ta = out['typeahead']
        print(q)
        print("-"*80)
        for v in ta:
            print("USERTYPED: '%s' \tSUGGESTION: '%s'" % (q, v))
            v = str(v).replace('"', '').replace(' ', '')
            for bad in bads:
                if bad in v:
                    print("FAILED IN TYPEAHEAD FOR '%s' WITH '%s'" % (q, v))
                    return
    print("passed.")

def multiuserSimulation(usercount, search):
    from splunk.searchhelp import searchhelper
    import splunk.auth
    import random
    from threading import Thread    
    class UserSimulationThread(Thread):
        def __init__(self, search, username):
            Thread.__init__(self)
            self.search     = search
            self.username   = username
            self.sessionKey = splunk.auth.getSessionKey(username, 'changeme')

        def run(self):
            try:
                search = self.search + " " + str(random.randint(0, 20)) + " | stats count"
                #print("username: %s sk: %s running search: %s" % (self.username, self.sessionKey, search))
                #print("username: %s sk: %s" % (self.username, self.sessionKey))
                help = searchhelper.help(self.sessionKey, utils.TEST_NAMESPACE(), self.username, search, None, None, None, 10, None, None, 
                                         useTypeahead=True, showCommandHelp=True, showCommandHistory=True, showFieldInfo=True)
                ta = help['typeahead']
                #print(ta)
            except Exception as e:
                print(e)
            

    start = time.time()
    threads = []
    for i in range(0, usercount):
        username = 'test%s' % (i % 20)
        user = UserSimulationThread(search, username)
        threads.append(user)
        user.start()
    for i in range(0, usercount):
        threads[i].join()
    end = time.time()
    spent = end-start
    return spent



def _main():    
    argc = len(sys.argv)
    argv = sys.argv
    if argc >= 3:
        user = argv[1]
        search = argv[2]
        insertpos = None
        if argc > 3:
            insertpos = int(argv[3])

        print("#### Run TEST for prod_type=None")
        helpout = help(utils.TEST_SESSION(), utils.TEST_NAMESPACE(), user, search, insertpos, None, None, 10, 
                       None, None, useTypeahead=True, showCommandHelp=True, showCommandHistory=True, 
                       showFieldInfo=True)
        
        for attr, val in helpout.items():
            print("%s%s = %s\n" % (attr, " "*abs(40-len(attr)), val))

        prod="lite"
        print("#### Run TEST for prod_type=%s" % prod)
        helpout = help(utils.TEST_SESSION(), utils.TEST_NAMESPACE(), user, search, insertpos, None, None, 15, 
                       None, None, useTypeahead=True, showCommandHelp=True, showCommandHistory=True, 
                       showFieldInfo=True, prod_type=prod)
        
        for attr, val in helpout.items():
            print("%s%s = %s\n" % (attr, " "*abs(40-len(attr)), val))

    elif argc > 1 and argv[1] == 'testtypeahead':
        testtypeahead()        
    elif argc > 1 and argv[1] == 'multitest':
        # monster = "index=_internal  (( (source=\"*/httpd/access_log*\" OR source=\"*\\httpd\\access_log*\" ) status=200 file=splunk-* NOT ( ( useragent=\"Acoon-*\" ) OR ( useragent=\"AdsBot-Google *\" ) OR ( useragent=\"AISearchBot *\" ) OR ( useragent=\"Baiduspider*\" ) OR ( useragent=\"* BecomeBot/*\" ) OR ( useragent=\"Biz360 spider *\" ) OR ( useragent=\"BlogBridge *\" ) OR ( useragent=\"Bloglines-Images/*\" ) OR ( useragent=\"BlogPulseLive *\" ) OR ( useragent=\"BoardReader/*\" ) OR ( useragent=\"bot/*\" ) OR ( useragent=\"* Charlotte*\" OR useragent=\"*(Charlotte/*)\" ) OR ( useragent=\"ConveraCrawler/*\" ) OR ( useragent=\"* DAUMOA-web\" ) OR ( useragent=\"* discobot*\" ) OR ( useragent=\"* DoubleVerify *\" ) OR ( useragent=\"Eurobot/*\" ) OR ( useragent=\"* Exabot/*\" ) OR ( useragent=\"FeedHub *\" ) OR ( useragent=\"Gigabot*\" ) OR ( useragent=\"* Googlebot/*\" OR useragent=\"Googlebot-*\" ) OR ( useragent=\"Grub*\" ) OR ( useragent=\"gsa-crawler *\" ) OR ( useragent=\"* heritrix/*\" ) OR ( useragent=\"ia_archiver*\" ) OR ( useragent=\"BlogSearch/*\" ) OR ( useragent=\"ichiro/*\" ) OR ( useragent=\"Yeti/*\" ) OR ( useragent=\"Inar_spider *\" ) OR ( useragent=\"kalooga/*\" ) OR ( useragent=KeepAliveClient ) OR ( useragent=\"larbin*\" ) OR ( useragent=\"LinkAider\" ) OR ( useragent=\"McBot/*\" ) OR ( useragent=\"MLBot *\" ) OR ( useragent=\"Morfeus Fucking Scanner\" ) OR ( useragent=\"msnbot*\" ) OR ( useragent=\"MSRBOT *\" ) OR ( useragent=*nagios-plugins* ) OR ( useragent=\"* Netcraft *\" ) OR ( useragent=\"*/Nutch-*\" ) OR ( useragent=\"panscient.com\" ) OR ( useragent=\"Pingdom.com_*\" ) OR ( useragent=\"PrivacyFinder/*\" ) OR ( useragent=\"Snapbot/*\" ) OR ( useragent=\"Sogou *\" ) OR ( useragent=\"Speedy Spider *\" ) OR ( useragent=\"Sphere Scout*\" ) OR ( useragent=\"*(Spinn3r *\" ) OR ( useragent=\"Technoratibot/*\" ) OR ( useragent=\"*/Teoma*\" ) OR ( useragent=\"TurnitinBot/*\" ) OR ( useragent=\"*(Twiceler*\" ) OR ( useragent=\"UtilMind *\" ) OR ( useragent=\"* voilabot *\" ) OR ( useragent=\"WebAlta*\" ) OR ( useragent=\"Splunk webping bundle\" ) OR ( useragent=\"* Yahoo! Slurp*\" OR useragent=\"* Yahoo! * Slurp*\" ) OR ( useragent=\"Yanga *\" ) OR ( useragent=\"YebolBot *\" ) ) NOT ( ( clientip=10.0.0.0/8 OR clientip=172.16.0.0/12 OR clientip=192.168.0.0/16 ) ) NOT ( ( clientip=64.127.105.34 OR clientip=64.127.105.60 OR clientip=206.80.3.67 ) ) ) ) _time<1199000000 _time>1198950000"
        lilmonster = "error"        
        total = 0.0
        for i in range(1, 1000):
            spent = multiuserSimulation(19, 'search %s' % lilmonster)
            total += spent
            print("Time: %ss Avg: %ss" % (spent, total / i))
    else:        
        print('Usage:')
        print(argv[0] + ' <user> <search> [<insertpos>]')
        print(argv[0] + ' testtypeahead')
        print(argv[0] + ' multitest')



if __name__ == '__main__':
    _main()
