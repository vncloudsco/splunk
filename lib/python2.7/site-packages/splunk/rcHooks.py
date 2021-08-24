
"""File containing generic functions which as as pre/post hooks for the cli."""

import os
import logging as logger

import splunk.rest as rest
import splunk.util as util
import splunk.rest.format as format
import splunk.clilib.control_exceptions as control_exceptions

thresholdMap = {
  "num-events"  : "number of events",
  "num-sources" : "number of sources",
  "num-hosts"   : "number of hosts",
  "always"      : "always"
}

relationMap = {
  "greater-than"  : "greater than",
  "less-than"     : "less than",
  "equal-to"      : "equal to",
  "rises-by"      : "rises by",
  "drops-by"      : "drops by"
}


def map_args_cli_2_eai(argsmap, eaiArgsList, argList):
   """Map the cli argument names to the appropriate eai argument names.

   Args:
      argsmap: map containing the map of cli arg name <=> eai arg names
      eaiArgsList: the destination dict that will contain keys which are the eai arg names
      argList: the sourse dict that will contain keys which are the cli arg names

   Returns:
      the eaiArgsList which acts as the GET/POST parms of the EAI request
   """
   for k in argList:
      try:
         eaiArgsList[argsmap[k]] = argList[k]
      except:
         eaiArgsList[k] = argList[k]

   return eaiArgsList

def make_path_absolute(cmd, obj, eaiArgsList):
   """Ensures the contents of eaiArgsList['name'] is absolute."""
   logger.debug('In function make_path_absolute, eaiArgsList: %s' % str(eaiArgsList))
   if obj in ['tail', 'monitor']:
       key = 'source'
   else:
       key = 'name'
   try:
      if not os.path.isabs(eaiArgsList[key]):
         eaiArgsList[key] = os.path.abspath(eaiArgsList[key])
   except:
      pass

def conv_to_list(cmd, obj, eaiArgsList):
   """Converts a value in the dict to a list."""
   if '%s:%s' % (cmd, obj) == 'set:default-index':
      if 'value' in eaiArgsList:
         eaiArgsList['value'] = eaiArgsList['value'].split(',')

# ----------------------------
def _parseThreshold(thresh):
  """ 
  Figure out threshold in the format "num-events:rises-by:5".
  """
  try:
    threshType, threshRel, threshVal = thresh.split(':', 2)
  except ValueError:
    raise control_exceptions.ArgError("The argument to 'threshold' must be in the form <threshold type>:<threshold relation>:<threshold value>.")
  if not threshType.lower() in thresholdMap:
    raise control_exceptions.ArgError("Invalid threshold type '%s' specified for 'threshold'.  Valid types are: %s." % (threshType, str.join(str(", "), thresholdMap)))
  if not threshRel.lower() in relationMap:
    raise control_exceptions.ArgError("Invalid threshold relation '%s' specified for 'threshold'.  Valid relations are: %s." % (threshRel, str.join(str(", "), relationMap)))
  if not threshVal.isdigit():
    raise control_exceptions.ArgError("Invalid threshold value '%s' specified for 'threshold'.  Threshold value must be a number." % threshVal)

  return thresholdMap[threshType.lower()], relationMap[threshRel.lower()], threshVal


def parse_saved_search(cmd, obj, eaiArgsList):
   """Funky saved-search argument parsing."""
   action = []

   #alert
   if 'alert' in eaiArgsList and util.normalizeBoolean(eaiArgsList['alert']):
      eaiArgsList['is_scheduled'] = '1'
      eaiArgsList.pop('alert')

   #threshold
   if 'threshold' in eaiArgsList:

      alert_type, alert_comparator, alert_threshold = _parseThreshold(eaiArgsList['threshold'])

      eaiArgsList['alert_type'] = alert_type
      eaiArgsList['alert_comparator'] = alert_comparator
      eaiArgsList['alert_threshold'] = alert_threshold
      eaiArgsList.pop('threshold')

   #email
   if 'email' in eaiArgsList:
      eaiArgsList['action.email.to'] = eaiArgsList['email']
      eaiArgsList.pop('email')
      action.append('email')

   #attach
   if 'attach' in eaiArgsList:
      eaiArgsList['action.email.sendresults'] = '1'
      eaiArgsList.pop('attach')

   #script
   if 'script' in eaiArgsList:
      eaiArgsList['action.script.filename'] = eaiArgsList['script']
      eaiArgsList.pop('script')
      action.append('script')

   #summary_index
   if 'summary_index' in eaiArgsList:
      eaiArgsList['action.summary_index._name'] = eaiArgsList['summary_index']
      eaiArgsList.pop('summary_index')
      action.append('summary_index')

   #action
   # SPL-50101 - only send actions if specified. otherwise, users that have permissions
   # to set actions will get a very unhelpful error about an 'actions'
   # parameter that they never specified.
   if len(action) > 0:
      eaiArgsList['actions'] = ','.join(action)

   #start_time
   if 'start_time' in eaiArgsList:
      eaiArgsList['dispatch.earliest_time'] = eaiArgsList['start_time']
      eaiArgsList.pop('start_time')

   #end_time
   if 'end_time' in eaiArgsList:
      eaiArgsList['dispatch.latest_time'] = eaiArgsList['end_time']
      eaiArgsList.pop('end_time')

   #ttl
   if 'dispatch.ttl' not in eaiArgsList:
      if 'ttl' in eaiArgsList:
         eaiArgsList['dispatch.ttl'] = eaiArgsList['ttl']
         eaiArgsList.pop('ttl')

   #fields
   if 'fields' in eaiArgsList:
      items = eaiArgsList['fields'].split(';')
      for ele in items:
         if len(ele.split(':')) != 2:
            raise control_exceptions.ArgError("Each argument to 'fields' must be in 'key:value' format")
         k, v = ele.split(':')
         eaiArgsList['%s.%s' % ('action.summary_index', k)] = v
      eaiArgsList.pop('fields')

def get_index_app(servResp, argList):
   """"""
   atom = rest.format.parseFeedDocument(servResp)

   for entry in atom:
      d = format.nodeToPrimitive(entry.rawcontents)
      if entry.title == argList['name']:
         return d['eai:acl']['app']
