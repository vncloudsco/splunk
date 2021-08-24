from builtins import range
from splunk.models.app import App
from splunk.models.user import User
import logging
logger = logging.getLogger('splunk.appserver.controllers.clustering')


def getAppOptions():
    appList = App.all().search('disabled=false')
    appOptionList = [  {'label': '%s (%s)' % (x.label, x.name), 'value': x.name} for x in appList ]
    return appOptionList

def getPwnrs():
    pwnrList = User.all().search("roles=*")
    pwnrOptionList = [  {'label': "%s (%s)" % (x.name, x.realname), 'value': x.name} for x in pwnrList ]
    pwnrOptionList.append({'label': _("No owner"), 'value': 'nobody'})
    return pwnrOptionList



def initialize(searchArgs):
    searchArgs['appOptionList'] = getAppOptions()
    searchArgs['pwnrOptionList'] = getPwnrs()

def filterEntities(searchArgs, entities):
    search = searchArgs.get("search", None)
    countPerPage = int(searchArgs.get("count", 25))
    offset = int(searchArgs.get("offset", 0))
    ns = searchArgs.get('ns', None)
    pwnr = searchArgs.get('pwnr', None)
    sort_by = searchArgs.get('sort_by', 'name')
    sort_dir = searchArgs.get('sort_dir', 'desc')

    filteredList =[]
    if search is not None:
        entities = entities.search(search)
    if ns is not None:
        entities = entities.filter_by_app(ns)
    if pwnr is not None:
        entities = entities.filter_by_user(pwnr)

    entities = entities.order_by(sort_by, sort_dir=sort_dir)
    startSpan = offset
    numItems = len(entities)
    searchArgs['numItems'] = numItems
    endSpan = min(offset + countPerPage, numItems) 
      
    for i in range(startSpan, endSpan):
        entity = entities[i]
        filteredList.append(entity)


    return filteredList



