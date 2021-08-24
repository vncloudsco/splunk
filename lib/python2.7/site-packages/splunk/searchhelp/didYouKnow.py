from __future__ import absolute_import
import re
import time

from splunk.searchhelp import utils


# stub gettext if not running from CP
try:
    _
except NameError:
    def _(message):
        return message


# WISH LIST
#   - match fields against tags/descriptions in fields.conf
#   - match whole search commands args to description:
#     - [most common values of a field] = | top FIELD

ELLIPSE = "\xe2\x80\xa6"

def help(output, aliasMap, user, search):
    """did you know ________?"""

    # get list of commands user entered
    userCommandsAndArgs = utils.getCommands(search, aliasMap)
    # for each pipeline
    for pipeline in userCommandsAndArgs:
        searchCommands = [c.strip() for c, a in pipeline]
    
        # a sort followed by a dedup can by combined into a "dedup .. sortby .." command
        if 'dedup' in searchCommands and 'sort' in searchCommands and searchCommands.index('dedup') > searchCommands.index('sort') and isInteresting(user, "sortdedup"):
            output['notices'].append(_('Consider using "%(suggestion)s" rather than "%(current)s"') % { 
                'suggestion': 'dedup %s sortby %s' % (ELLIPSE, ELLIPSE), 
                'current': 'sort %s | dedup %s' % (ELLIPSE, ELLIPSE)
                })
            
        # "count(_raw)" probably should be just "count" in the context of
        # a stats/chart/timechart command
        if "count(_raw)" in search and isInteresting(user, "countraw"):
            output['notices'].append(_('Consider using "count()" rather than "count(_raw)"'))
    
        # 'search ...| where ...' could be combined into a single search
        # condition if the where condition is simple (i.e. if it is a
        # simple comparision of a field to a literal value)
        if 'search' in searchCommands and 'where' in searchCommands and searchCommands.index('where') > searchCommands.index('search') and isInteresting(user, "searchwhere"):
            whereargs = pipeline[searchCommands.index('where')][1].strip()
            searchargs = pipeline[searchCommands.index('search')][1].strip()
            if whereargs != "":  whereargs  = " (%s)" % whereargs
            if searchargs != "": searchargs = " (%s)" % searchargs
            output['notices'].append(_('Consider combining the "where" condition%(whereargs)s into the search condition%(searchargs)s') % {'whereargs':whereargs, 'searchargs':searchargs})
    
        # 'search ... | where ...' could be combined into a single search
        # condition if the where condition is simple (i.e. if it is a
        # simple comparision of a field to a literal value)

        # for each command
        for i, cmd in enumerate(searchCommands):
            if cmd == 'search':
                # get args
                searchargs = pipeline[i][1].strip()
                # has 10.*, 10.11.12.13, but not 10.10.10.10/16
                IPish = re.findall("([0-9]{1,3}(?:\.[0-9*]{1,3}){1,3})(?![./0-9])", searchargs)
                if len(IPish) > 0 and isInteresting(user, "searchip"):
                    output['notices'].append(_('Consider using CIDR support in the search operator (e.g., "host=10.0.0.1/16")'))
                if " and " in searchargs or " not " in searchargs or " or " in searchargs:
                    output['notices'].append(_('Boolean operators must be uppercased (e.g., AND, OR, NOT); otherwise the search is looking for the terms "and", "or", and "not".'))
                if "..." in searchargs:
                    output['notices'].append(_('Wildcards are supported with an asterisk ("*"), not an ellipsis ("...").'))

        if len(searchCommands) == 1 and searchCommands[0] == "search" and not search.strip().endswith("|"):
            #if (search == "| search" or search == "| search *") and isInteresting(user, "searchintro"):
            output['notices'].append(_("***INTROTXT***"))
            
    return output


def isInteresting(user, suggestion):
    return True  # for now


## TIMEOUT = 60*60
## cache = {}
##
## def isInteresting(user, suggestion):
##     now = time.time()
##     key = user + "-" + suggestion
##     lasttoldtime = cache.get(key, 0)
##     if now - lasttoldtime > TIMEOUT:
##         cache[key] = now
##         return True
##     return False
