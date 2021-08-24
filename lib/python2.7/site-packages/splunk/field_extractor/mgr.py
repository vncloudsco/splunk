from __future__ import absolute_import
from __future__ import print_function
from builtins import object

import sys, time, re, os
import xml.sax.saxutils as su

import splunk.auth
import splunk.search
import splunk.entity as en
import splunk.bundle as bundle
import splunk.util

from splunk.field_extractor import MultiFieldLearn as fieldlearner

import logging
logger = logging.getLogger('dmfx')


# when extraction applies to [source::...foo...] and restriction is sourcetype=bar,
# we have to search for sourcetype=bar, looking for any that 
MAX_TO_SCAN_FOR_MATCHING_SOURCE = 10000

# only willing to show 1000 events.  this way we can grab 1000 events,
# and even if we're only showing 100 events and the user changes to
# say he wants to see 1000 events we have the events right there,
# ready to show without refetching and erasing his markups
MAX_WILLING_TO_SHOW = 100

# in finding diverse events, scan at most 10k events to cluster
MAX_TO_SCAN_FOR_DIVERSE_EVENTS = 10000
# show N events per cluster for diverse
MAX_EVENTS_PER_CLUSTER = 3
CLUSTER_THRESHOLD = 0.6 # make option if necessary


def log(msg):
   pass
   
class ModelException(Exception):
   pass


"""

    # get the form output ;)
    @route('/=gtfo')
    def gtfo(self, **kwargs):
        required_args = {
            "app": ('string', None),
            "field": ('string', None),
            "restriction_type": ('choice', ['source','sourcetype','host']),
            "restriction_value": ('string', None),
            "filter": ('string', None)
            "max_events": ('int', (1,1000)),
            "result_type": ('choice', ['latest', 'diverse', 'outliers']),
            "add_filter_to_regex": ('bool', None),
            "max_learn_events": ('int', (1,1000)),
            "max_lines_per_event": ('int', (1, 200)),
            "markup": ('json', None),
            "counter_examples": ('json', None)
            }
        optional_args = ['sid','offset', "markups"]
        output = mgr.gtfo(sessionKey, username, namespace, kwargs)

setEventMarkup(id, markup)
getFilteredEvents()
getRunnableExistingExtractions()
generateRules()

"""

def gtfo(sessionKey, source_field, marked_up_events, counter_examples, filter, sid, offset, count):

   events = None
   if sid != None and offset != None:
      try:
         job = splunk.search.getJob(sid, sessionKey=sessionKey)
         events = job.events[int(offset):int(count)]
      except Exception as e:
         # search job expired or is invalid for some reason
         raise Exception('Could not find job with id: %s' % sid)

   events = convertEvents(events)
   rules = _generateRules(sessionKey, source_field, events, marked_up_events, counter_examples, filter)

   patterns = [ rule.getPattern() for rule in rules]

   return patterns


def convertEvents(results):
   """ convert search results into list of dict"""
   events = []            
   for i, result in enumerate(results):
      event = {}
      for k in result:
         event["%s" % k] = str(result[k])
      events.append(event)
   return events

        
def getRestrictionValues(sessionKey, rtype, index):

        rsearch = "|metadata type=%ss index=\"%s\"| sort -lastTime | head 50 | table %s" % (rtype, index, rtype)
        log("getRestrictionValue: %s" % rsearch)
        results = splunk.search.searchAll(rsearch, sessionKey=sessionKey)
        if results == None:
            values = [None]
        else:
            values = [str(result[rtype]) for result in results]
        if len(values) == 1:
           values = values[0]
        return values


# only returns extractions that can run given the existing restrictions (e.g. source=/tmp/foo.log) and field (e.g. host).
def getSavedExtractions(sessionKey, app, owner, index, rtype, rval, source_field, edited_extractions):

       extractions = edited_extractions
       
       entities = en.getEntities('data/props/extractions', namespace=app, owner=owner, search="type=inline",  count=-1, sessionKey=sessionKey)
       extractions_cache = {}

       for name in entities:
           entity = entities[name]
           if entity['type'].lower() != "inline": continue
           
           stanza = entity['stanza']
           attribute = entity['attribute']
           value = entity['value']
           acl = entity['eai:acl']
           if attribute.lower().startswith("extract-"):
              attribute = attribute[8:]
           m = re.search("(?P<regex>.+) in (?P<srcfield>[a-zA-Z0-9_]+)$", value)
           if m != None:
               regex = m.groupdict()['regex']
               srcfield = m.groupdict()['srcfield']
           else:
               regex = value
               srcfield = '_raw'
           if srcfield != source_field:
              continue
           # no match to edited rule.  add if we can
           if _extractionCanRun(extractions_cache, sessionKey, index, stanza, rtype, rval, source_field):
              rule = ExistingExtraction(stanza, attribute, srcfield, regex, acl)
              extractions.append(rule)

       return extractions

        


def getAppsList(sessionKey, owner):
   return list(splunk.entity.getEntities('apps/local', search='visible=1 AND disabled=0', namespace=None, owner=owner, count=-1, sessionKey=sessionKey).keys())

def getIndexList(sessionKey, owner):
   indexes = splunk.entity.getEntities('data/indexes',  search='disabled=0 AND totalEventCount>0', namespace=None, owner=owner, count=-1, sessionKey=sessionKey)
   if len(indexes) == 0:
      indexes = []
   else:
       defaultIndex = list(indexes.values())[0]['defaultDatabase'] # all values have duplicate data -- the default index
       indexes = list(indexes.keys())
       if defaultIndex in indexes:
          # move default index to first value in list
          indexes.remove(defaultIndex)
          indexes.insert(0, defaultIndex)
       # make '*' actually be the default index
       indexes.insert(0, '*')            
   return indexes



#######################################################################################################
# WHICH FIELD TO EXTRACT ON.  Used when writing out EXTRACT-foo = <regex> (in <sourcefield>)
def getSourceFields(events):
       if events == None:
           sourceFields = []
           return sourceFields
           
       fieldInfo = {}
       # for each event, for each field, keep a running total of field's length and count
       for event in events:
          for k, v in event.items():
             if not isinstance(v, splunk.util.string_type):
                continue
             vlen = len([ch for ch in v if ch.isalnum()]) # score fields by how many alphanumerics it has

             if k.startswith("_") and k != "_raw":
                fieldInfo[k] = (-1, 1) # put all internal fields at the bottom, except _raw
             elif k not in fieldInfo:
                fieldInfo[k] = (1, vlen)
             else:
                count, total = fieldInfo[k]
                fieldInfo[k] = (count+1, total + vlen)


       fieldsAndStats = list(fieldInfo.items())
       # sort most interesting fields first
       fieldsAndStats.sort(key=lambda x: (100.0 * (float(x[1][1]) * x[1][0])))
       sourceFields = [ fs[0] for fs in fieldsAndStats ]
       return sourceFields



def saveRule(sessionKey, app, owner, make_global, oattribute, regex, source_field, rtype, rval, name):
   if None == re.search("\?P<(.*?)>", regex):
      raise ModelException("Regex '%s' does not contain a named extraction (e.g. '(?P<fieldname>\w+)')" % regex)
   value = _getRegexExtractionValue(regex, source_field)
   stanza = _getStanzaName(rtype, rval)
   _writeStanzaAttributeValue(sessionKey, app, owner, make_global, stanza, oattribute, value, regex, source_field)


def deleteRule(sessionKey, app, owner, make_global, oattribute, regex, source_field, rtype, rval, name):
   # write out empty value
   stanza = _getStanzaName(rtype, rval)
   _writeStanzaAttributeValue(sessionKey, app, owner, make_global, stanza, oattribute, "", regex, source_field)




#######################################################################################################
#######################################################################################################
#######################################################################################################

#RETURN SID,OFFSET,EVENTS

# GET SAMPLE EVENTS BASED ON RESTRICTIONTYPE=RESTRICTIONVALUE
def _getEvents(sessionKey, resultType, index, rtype, rval, source_field, filter, maxLinesPerEvent):
    query = _getResultQuery(resultType, index, rtype, rval, source_field, filter, maxLinesPerEvent)
    if query == None:
        return None, None

    log("getEvents: %s" % query)           
    #print("QUERY:" + query)
    # results = splunk.search.searchAll(query, sessionKey=sessionKey, status_buckets=1, required_field_list='*')
    searchjob = splunk.search.dispatch(query, sessionKey=sessionKey, status_buckets=1, required_field_list='*')
    splunk.search.waitForJob(searchjob)
    results = list(searchjob)
    return searchjob.id, results


def _getResultQuery(resultType, index, rtype, rval, source_field, filter, maxLinesPerEvent):
        
        if resultType == 'latest':
            query = 'search %s="%s" %s="*%s*" index="%s"| head %s | abstract maxlines=%s ' % (rtype, rval, source_field, filter, index, MAX_WILLING_TO_SHOW, maxLinesPerEvent)
        elif resultType in ['diverse', 'outliers']:
            # search 10k events, cluster events, keep latest N of each
            # cluster, sort clusters to keep the most popular
            # clusters, keeping only events from those top clusters,
            # then resort by time.
            #  ... | head 10000 | cluster t=0.8 showcount=true field=_raw labelonly=true
            #      | dedup 5 cluster_label| sort 100 -cluster_count | sort -_time
            if resultType == 'diverse':
                sortDir = '-'
            else:
                sortDir = '+' # outliers
                
            query = 'search %s="%s" %s index="%s"| head %s | cluster t=%s showcount=true field="%s" labelonly=true | dedup %s cluster_label | sort %s %scluster_count | sort -_time | abstract maxlines=%s ' % (rtype, rval, filter, index, MAX_TO_SCAN_FOR_DIVERSE_EVENTS, CLUSTER_THRESHOLD, source_field, MAX_EVENTS_PER_CLUSTER, MAX_WILLING_TO_SHOW, sortDir, maxLinesPerEvent)
        return query
    


# returns true if an extraction is consistent with the
# restrictions and sourcefield and values
# (e.g. host/source/sourcetype) on the sample events.
def _extractionCanRun(extractions_cache, sessionKey, index, stanza, restrictionType, restrictionValue,  sourceField):

        # if extraction is tied to a source, but it's different than
        # the source we're restricting to, extraction is irrelevant
        if stanza.startswith("source::"):
            stanzaType = "source"
            stanzaValue = sourcePattern = _expandRegex(stanza[8:])
            # !!! TODO need to fix ..., ., * for filenames and do regex matching
            
            if restrictionType == "source" and not re.match(sourcePattern, restrictionValue):
                return False

        # if extraction is tied to a host, but it's different than the
        # host we're restricting to, extraction is irrelevant
        elif stanza.startswith("host::"):
            stanzaType = "host"
            stanzaValue = host = stanza[6:]
            # if extraction is limited to a host and 
            if restrictionType == "host" and restrictionValue != host:
                return False
        # sourcetype
        else:
            stanzaType = "sourcetype"
            # if extraction is tied to a sourcetype, but it's
            # different than the sourcetype we're restricting to,
            # extraction is irrelevant
            stanzaValue = sourcetype = stanza
            if restrictionType == "sourcetype" and restrictionValue != sourcetype:
                return False


        # ok, if we made it this far, the stanza (e.g. [host::web])
        # isn't findamentally incompatible with the restrictions
        # (e.g., source=/tmp/db2) but it could be entirely irrelevant
        # because no events in /tmp/db2 have a host=web.
        # run a fast search to see...
        if stanzaType == "source":

            ### !! consider using metadata to get all sources, filter by regex, and then search for any with restrictiontype=restriction value
            ### would give a perfectly accurate list.
            key = (restrictionType, restrictionValue, index)
            log("KEY = %s" % str(key))
            if key not in extractions_cache:
               try:
                  query = 'search %s="%s" index="%s"| head %s | dedup source' % (restrictionType, restrictionValue, index, MAX_TO_SCAN_FOR_MATCHING_SOURCE)
                  log("extractionCanRun: %s" % query)           
                  results = splunk.search.searchAll(query, sessionKey=sessionKey)
                  for result in results:
                     source = str(result['source'])
                     extractions_cache[key].add(source)

               except Exception as e:
                  log("Error running search: %s because %s" % (query, e))
                  return False
                
            mysources = extractions_cache[key]
            for mysrc in mysources:
                if re.search(stanzaValue, mysrc) != None:
                    return True
            return False
        else:
            query = 'search %s="%s" %s="%s" index="%s"| head 1' % (restrictionType, restrictionValue, stanzaType, stanzaValue, index)
        try:
           log("extractionCanRun: %s" % query)           
           results = splunk.search.searchOne(query, sessionKey=sessionKey)
           return results != None and len(results) > 1
        except Exception as e:
           log("Error running search: %s because %s" % (query, e))
           return False



# fix ..., ., * for filenames and do regex matching
# impliment same conversion of short-hand regex notation that allows stanzas to regex match
# for example, a stanza named "source::...(foo...bar|baz)"
# see XMLAndStringUtil.cpp:toRegex()
def _expandRegex(pattern):
        if os.sep != '/':
            dirregex = "[^/]*"
        else:
            dirregex = "[^\\\\]*"
        pattern = pattern.replace("*", dirregex) # pattern = re.sub("\\*",  dirregex, pattern)
        pattern = pattern.replace("...", ".*")   # pattern = re.sub("\\.{3}", ".*", pattern)
        pattern = re.sub("\\.(?!\\*)", "\\\\.", pattern)
        return pattern


def _generateRules(sessionKey, source_field, events, marked_up_events, counter_examples, filter):

#   try:
       # !!!TODO LEARN METHOD ASSUMES DIFFERENT EVENTS, NOT MARK UP IN EVENTS
       learnedRules = fieldlearner.learn(source_field, marked_up_events, events, counter_examples, filter)

       # f = open("/tmp/learned.txt","a")
       # f.write("rules:%s\n" % learnedRules)
       # f.write("source_field: '%s'\n" % source_field)
       # f.write("filter: '%s'\n" % filter)
       # f.write("marked:%s\n" % marked_up_events)
       # f.write("events:%s\n" % events)
       # f.close()

       # empty existing rules
       rules = []
       # for each learned rule
       for lrule in learnedRules:
          pattern = lrule.getPattern()
              
          fieldinfo = lrule.getFieldValues()
          # doesn't match any edited rule
          rule = Rule(pattern, fieldinfo)
          rules.append(rule)
       
       return rules
#   except Exception as e:
#       raise e
       ## import traceback
       ## f = open("/tmp/blah.txt", "a")
       ## f.write("ERROR: %s\n" % e)
       ## f.write("Traceback: %s\n" % traceback.format_exc())           
       ## f.close()
   


def _getRegexExtractionValue(regex, source_field):
       # ewoo doesn't like values ending in "\"
       if regex.endswith("\\\\"):
          regex = regex[:-2] + "[\\\\]"
       # if not using _raw, add "in" specifier
       if source_field != "_raw":
          regex += " in %s" % source_field
       return regex
    

def _getStanzaName(rtype, rval):
   # props.conf weirdness -- [sourcetype::name] doesn't match.
   # need to use [name] only for 'sourcetype'. other attributes: source, host, and eventtype work
   # old quoted dequoted restriction value. not sure if necessary ??? test
   stanza = "%s::%s" % (rtype, rval)
   if rtype == "sourcetype":
      stanza  = rval
   return stanza

def _writeStanzaAttributeValue(sessionKey, app, owner, make_global, stanza, oattribute, value, regex, source_field):
   attribute = "EXTRACT-" + oattribute
   mynamespace = app
   if make_global:
      mynamespace = None
   props = bundle.getConf('props', sessionKey=sessionKey, namespace=mynamespace, owner=owner)
   props.createStanza(stanza)
   props[stanza][attribute] = value


class Rule(object):

   def __init__(self, pattern, fieldinfo):
      self._permissions = "private" # make more complicated
      self._pattern = pattern
      self._extractedValues = fieldinfo
      self.unedit()

   def setPattern(self, pattern):
      self._pattern = pattern
      self._re      = re.compile(pattern)

   def getOriginalPattern(self):
      return self._pattern
   
   def getPattern(self):
      if self.isEdited():
         return self._userRegex      
      return self._pattern

   def saveEdit(self):
      if self.isEdited():
         self._pattern = self._userRegex
         self.unedit()

   def edit(self, userRegex):
      if userRegex == self._pattern:
         self.unedit()
      else:
         try:
            re.compile(userRegex)
            self._userRegex = userRegex         
         except Exception as e:
            raise ModelException("Ignoring invalid regex '%s': %s" % (userRegex, e))

   def unedit(self):
      self._userRegex = None

   def isEdited(self):
      return self._userRegex != None

   def extract(self, events, sourcefield):
      self._extractedValues = {}
      # go through events
      for event in events:
         # extract values
         kvs = self._re.find(event.getValue(sourcefield, "")).groupdict()
         # add extractions to lists of values extracted
         for k, v in kvs.items():
            if k not in self._extractedValues:
               self._extractedValues[k] = []
            self._extractedValues[k].append(v)

   def getExtractions(self):
      return self._extractedValues


class ExistingExtraction(Rule):
   def __init__(self, stanza, attribute, srcfield, pattern, acl):
      Rule.__init__(self, pattern, None)
      self._stanza    = stanza
      self._attribute = attribute
      self._srcfield  = srcfield
      self._acl       = acl

   def __str__(self):
      return "stanza: '%s' attribute: '%s' scrfield: '%s' acl: '%s' pattern: '%s' userRegex:'%s'" % (self._stanza, self._attribute, self._srcfield, self._acl, self._pattern, self._userRegex) 
   def getStanza(self):
      return self._stanza
   def getAttribute(self):
      return self._attribute
   def getSourceField(self):
      return self._srcfield
   def getACL(self):
      return self._acl



def printList(name, values):
   print("-"*80)
   print(name)
   for val in values[:10]:
      print("\t" + str(val))
   if len(values)>10:
      print("\t...")

def test():
   owner = 'admin'
   sessionKey = splunk.auth.getSessionKey('admin', 'changeme')

   apps = getAppsList(sessionKey, owner)
   printList("apps", apps)

   indexes = getIndexList(sessionKey, owner)
   printList("indexes", indexes)

   index = '_internal'
   for rtype in ["source", "sourcetype", "host"]:
      vals = getRestrictionValues(sessionKey, rtype, index)
      printList(rtype, vals)

   app = 'search'
   rtype = 'sourcetype'
   rval = 'splunkd'
   source_field = '_raw'
   results_type = 'latest'
   edited_extractions = []
   marked_up_events = []
   counter_examples = []
   filter = 'INFO'
   existing_regexes = []

   saved_extractions = getSavedExtractions(sessionKey, app, owner, index, rtype, rval, source_field, edited_extractions)
   printList("existing extractions", saved_extractions)

   print("NO EXAMPLES")
   max_lines_per_event = 10
   vals = gtfo(sessionKey, owner, app, index, rtype, rval, source_field, results_type, edited_extractions, marked_up_events, counter_examples, filter, existing_regexes, max_lines_per_event)
   rules = vals["rules"]
   events = vals["events"]
   sid = vals["sid"]
   offset = vals["offset"]
   printList("rules", rules)
   printList("events", events)
   print("sid: " + str(sid))
   print("offset: " + str(offset))

   print("GIVEN AN EXAMPLE")
   marked_up_events = [ { 'id':'0', 'foo': 'INFO', '_event': events[0] } ]
   vals = gtfo(sessionKey, owner, app, index, rtype, rval, source_field, results_type, edited_extractions, marked_up_events, counter_examples, filter, existing_regexes, max_lines_per_event)
   rules = vals["rules"]
   events = vals["events"]
   sid = vals["sid"]
   offset = vals["offset"]
   printList("rules", rules)
   printList("events", events)
   print("sid: " + str(sid))
   print("offset: " + str(offset))

   fields = getSourceFields(events)
   printList("fields", fields)

   make_global = True
   oattribute = 'foo'
   name = 'fooname'
   for rule in rules:
      regex = rule.getPattern()
      print("new regex: " + regex)
      saveRule(sessionKey, app, owner, make_global, oattribute, regex, source_field, rtype, rval, name)
      deleteRule(sessionKey, app, owner, make_global, oattribute, regex, source_field, rtype, rval, name)


if __name__ == '__main__':
   test()
