from __future__ import print_function
from builtins import range
from builtins import object
from functools import cmp_to_key

import re
import splunk.auth
import splunk.search
import splunk.mining.MultiFieldLearn as fieldlearner
import splunk.entity as en
import splunk.util

##############################################################################################################################
######### IFX  ###############################################################################################################
##############################################################################################################################
# Goals
#   - improve code, separating ui into html vs api
#   - support multiple values
#   - show existing extractions
#   - extract on fields other than raw 
#   - add regex cheatsheet to edit regex
#   - disable autokv option
#   - set permissions (global?) private/public
#   - edit and delete existing regex
#

##############################################################################################################################

MAX_SAMPLES = 100
MIN_SAMPLES = 20
MAX_LINES = 15

class ModelException(Exception):
   pass

class ModelManager(object):
    def __init__(self):
        self._sessions = {}

    def getModel(self, namespace, owner, sessionKey):

        # if we have a new sessionKey
        if not sessionKey in self._sessions:
            # delete old models
            self.cleanInvalidModels()
            # add new sessionKey->model mapping
            self._sessions[sessionKey] = Model(namespace, owner, sessionKey)

        return self._sessions[sessionKey]


    def cleanInvalidModels(self):
        # clean up old sessionKeys
        old = []
        for sk in self._sessions:
            if not splunk.auth.ping(sessionKey=sk):
                old.append(sk)
        for sk in old:
            del self._sessions[sk]
        

class Model(object):

    def __init__(self, namespace, owner, sessionKey):
        self._sessionKey = sessionKey
        self._namespace = namespace
        self._owner = owner
        self._restrictionType = "sourcetype"
        self._restrictionValue = "*"
        self._events = []
        self._eventsDirty = True
        self._id = None
        self._sourceField = "_raw"
        self._sourceFields = [] 
        self._eventsFilter = ""
        self._markedUpEvents = {}
        self._rules = []
        self._counterExamples = {}
        
    def getRestrictionTypes(self):
        return ["sourcetype", "source", "host"]

    def getRestrictionType(self):
        return self._restrictionType
    def setRestrictionType(self, rtype):
        if rtype not in self.getRestrictionTypes():
            raise ModelException("Unknown restriction type: %s" % rtype)
        if self._restrictionType != rtype:
            self._eventsDirty = True
        self._restrictionType = rtype
        
    def getRestrictionValues(self, rtype):
        if rtype not in self.getRestrictionTypes():
            raise ModelException("Unknown restriction type: %s" % rtype)

        results = splunk.search.searchAll("|metadata type=%ss | sort -lastTime | head 50 | table %s" % (rtype, rtype), sessionKey=self._sessionKey)
        return [str(result[rtype]) for result in results]

    def setRestrictionValue(self, val):
        if self._restrictionValue != val:
            self._eventsDirty = True
        self._restrictionValue = val
        
    def getRestrictionValue(self):
        return self._restrictionValue

    #######################################################################################################
    # ATTRIBUTE NAME FOR PROPS.CONF (e.g. EXTRACT-foo)
    def addFieldExtraction(self):
        ## !!! TODO make new extraction id
        self._id = "make a new idea"
    def editFieldExtraction(self, id):
        self._id = id
    def deleteFieldExtraction(self, id):
        ## !!! TODO field extraction
        pass
    def getFieldExtraction(self):
        ## !!! TODO make new extraction id
        return self._id

    def getExistingExtractions(self, constraint=None):
       search = "type=inline"
       if constraint != None:
          search = "%s AND %s" % (search, constraint)
          
       entities = en.getEntities('data/props/extractions', namespace=self._namespace, owner=self._owner,
                                 search=search,  count=-1, sessionKey=self._sessionKey)
       return entities


    #######################################################################################################
    # WHICH FIELD TO EXTRACT ON.  Used when writing out EXTRACT-foo = <regex> (in <sourcefield>)?
    def getSourceFields(self):
       if len(self._sourceFields) > 0:
          return self._sourceFields
    
       events = self.getEvents()
       
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
                count, sum = fieldInfo[k]
                fieldInfo[k] = (count+1, sum + vlen)


       fieldsAndStats = list(fieldInfo.items())
       # ok, change of plans. avg length returns verbose and rare fields. no good.
       #     fieldsAndStats.sort(key=cmp_to_key(lambda x,y: int((100.0 * float(y[1][1]) / y[1][0]) - 100.0 * (float(x[1][1]) / x[1][0]))))
       # instead, return fields that have most occurrances * total length.  we want fields that occur often and with lots of text.
       fieldsAndStats.sort(key=cmp_to_key(lambda x, y: int((100.0 * float(y[1][1]) * y[1][0]) - 100.0 * (float(x[1][1]) * x[1][0]))))
       self._sourceFields = [ fs[0] for fs in fieldsAndStats ]
       return self._sourceFields


    def getSourceField(self):
        return self._sourceField
    def setSourceField(self, fieldname):
        self._sourceField = fieldname

    #######################################################################################################
    # FILTER FIELD FOR LIST OF EVENTS
    def setEventsFilter(self, filter):
        self._eventsFilter = filter
    def getEventsFilter(self):
        return self._eventsFilter

    #######################################################################################################
    # GET SAMPLE EVENTS BASED ON RESTRICTIONTYPE=RESTRICTIONVALUE
    def getEvents(self):
        if self._eventsDirty:
            self._sourceFields = [] # reset sourcefieldinfo

            rtype = self.getRestrictionType()
            rval  = self.getRestrictionValue()

            if rtype == None or rval == None:
               return None

            query = 'search %s="%s" | head %s | abstract maxlines=%s ' % (rtype, rval, MAX_SAMPLES, MAX_LINES)

            results = splunk.search.searchAll(query, sessionKey=self._sessionKey, status_buckets=1, required_field_list='*')

            self._events = []            
            for i, result in enumerate(results):
               event = {}
               for k in result:
                  event["%s" % k] = str(result[k])
               event["id"] = i
               self._events.append(event)
            self._eventsDirty = False

        return self._events

    def getFilteredEvents(self):
        events = self.getEvents()
        filter = self._eventsFilter.strip()
        if filter == "*":
           return events

        # return only those events where the filtertext is contained in an event's sourcefield
        return [event for event in events if self._eventsFilter in event.get(self.getSourceField(), "")]

    
    #######################################################################################################
    # RETURN AND MARKED UP INFORMATION ABOUT AN EVENT
    def getEventMarkup(self, eventID):

        # if event isn't already marked up
        if eventID not in self._markedUpEvents:
            # return markedup values that have empty values for recently used fields
            markup = {}
            event = self._events[eventID]
            # for each field user added for markup, add it
            for field in self.getMarkedUpFields():
                markup[field] = event.get(field, "")
                
            # also store original event fields
            markup["_event"] = event
            self._markedUpEvents[eventID] = markup

        return self._markedUpEvents[eventID]        

    def setEventMarkup(self, eventID, markup):

        markup = dict(markup) # copy
        markup["_event"] = self._events[eventID] # also store original event fields
        self._markedUpEvents[eventID] = markup

    #######################################################################################################
    # RETURN COUNTER EXAMPLES.  SHOULD BE A DICT OF LIST OF COUNTER EXAMPLES
    def setCounterExamples(self, examples):
       self._counterExamples = examples

    def getCounterExamples(self, examples):
       return self._counterExamples

    #######################################################################################################
    # GET LIST OF FIELDS THAT MIGHT BE OF INTEREST TO MARK UP, BASED ON WHAT THE
    # USER PREVIOUSLY MARKED EVENTS UP WITH
    def getMarkedUpFields(self):
       fields = set()

       # for each marked up event, get the fields specified and add them to set of fields
       # these might include user specified fields that aren't on the results, when the user is training a new field.
       for markup in self._markedUpEvents.values():
          for field in markup:
             if field !="" and field != "_event":
                fields.add(field)
       return fields

    #######################################################################################################
    
    def generateRules(self):
       learnedRules = fieldlearner.learn(self._sourceField, self._markedUpEvents, self._counterExamples)

       # keep edited rules
       editedRules = [r for r in self._rules if r.isEdited()]
       # empty existing rules
       self._rules = []
       # for each learned rule
       for lrule in learnedRules:
          pattern = lrule.getPattern()
          fieldinfo = lrule.getFieldValues()
          # for each edited rule, if we have a match with the newly learned rule, don't add it
          for r in editedRules:
             if r._pattern() == pattern:
                break
          else: # add rule that doesn't match any edited rule
             rule = Rule(pattern, fieldinfo)
             self._rules.append(rule)
       self._rules.extend(editedRules)
       #self._rules = learnedRules # !!! not correct.  need to have learned vs edited rules and make proper rule obj


    def getRules(self):
        # some sort of rule object with info about if it's edited.  maybe values extracted
        return self._rules



class Rule(object):

   def __init__(self, pattern, fieldinfo):
      self._permissions = "private" # make more complicated
      self._pattern = pattern
      self._extractedValues = fieldinfo
      self.unedit()

   def setPattern(self, pattern):
      self._pattern = pattern
      self._re      = re.compile(pattern)

   def getPattern(self):
      if self.isEdited():
         return self._userRegex
      
      return self._pattern

   def edited(self, userRegex):
      self._userRegex = userRegex

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

def getCompressionSize(datastring):
   import zlib, bz2
   return len(zlib.compress(bz2.compress(datastring)))

   

   
def test():
   mgr = ModelManager()
   owner = "admin"
   namespace = "search"
   sessionKey = splunk.auth.getSessionKey(owner, "changeme")
   model = mgr.getModel(namespace, owner, sessionKey)

   existingExtractions = model.getExistingExtractions()
   for ex in existingExtractions:
      print("EX: %s" % ex)

   print("restriction types: %s" % model.getRestrictionTypes())
   print("restriction type:  %s" % model.getRestrictionType())
   try:
      model.setRestrictionType("blah")
      print("accepted bogus model!")
   except:
      pass
   model.setRestrictionType("source")
   print("restriction type: %s" % model.getRestrictionType())
   assert(model.getRestrictionType() == "source")

   for rtype in model.getRestrictionTypes():
      print("restriction values for %s: %s" % (rtype, model.getRestrictionValues(rtype)))

   sampleVal = model.getRestrictionValues(model.getRestrictionType())[-1]
   model.setRestrictionValue(sampleVal)
   print("restriction %s=%s " % (model.getRestrictionType(), model.getRestrictionValue()))
   assert(model.getRestrictionValue() == sampleVal)

   model.editFieldExtraction("31415")
   assert(model.getFieldExtraction() == "31415")

   for i in range(0, 5):
      model.addFieldExtraction()
      print("new extraction id: %s" % model.getFieldExtraction())

   try:
      model.deleteFieldExtraction("nonexistant")
      print("!! should error over non-existant extraction")
   except:
      pass

   print("possible source fields to extract from: %s" % model.getSourceFields()[:10])
   print("source field to extract from: %s" % model.getSourceField())
   
   model.setSourceField("ip")
   assert(model.getSourceField() == "ip")
   model.setSourceField("_raw")
   


   events = model.getEvents()
   print("event count:  %u" % len(events))

   model.setEventsFilter("*")
   assert(model.getEventsFilter() == "*")
   print("filtered event count: %u" % len(model.getFilteredEvents()))
   assert(len(events) == len(model.getFilteredEvents()))

   model.setEventsFilter("00")
   print("filtered (%s) events count: %s" % (model.getEventsFilter(), len(model.getFilteredEvents())))

   events = model.getFilteredEvents()

   # !! TODO need to make sure that getEvents returns ID's on events
   for event in events:
      print("EVENT: %s" % event[model.getSourceField()])
      id = event["id"]
      markup = model.getEventMarkup(id)
      markup["host"] = "10.1.1.228"
      markup["type"] = "GET"
      markup["code"] = "200"
      markup["bytes"] = "1103"

      model.setEventMarkup(id, markup)
      markup2 = model.getEventMarkup(id)
      assert(markup == markup2)
      
   suggestedFields = model.getMarkedUpFields()
   print("suggested markup fields on events: %s" %suggestedFields)
   assert("host" in suggestedFields)
      

   model.generateRules()
   
   rules = model.getRules()
   print("RULES:")
   for rule in rules:
      print(rule.getPattern())



if __name__ == '__main__':
   test()
