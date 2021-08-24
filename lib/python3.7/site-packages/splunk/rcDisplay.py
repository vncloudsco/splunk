from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

from builtins import range
from builtins import map
from builtins import filter
from builtins import zip
import math
import os
import sys

import splunk
import splunk.rest as rest
import splunk.rest.format as format
import splunk.search as search
import splunk.util as util
from splunk.clilib import literals
import splunk.util
from functools import reduce

import logging as logger

from future.moves.urllib import parse as urllib_parse

#documentation et all...
__doc__ = """
          This contains all the display functions for formatting the data returned from the EAI calls.
          """
__copyright__ = """  Version 4.0"""

#display messages...

#exec
EXEC_ADD            = '''Configuration updated: '%s' has been added for execution.'''
EXEC_REMOVE         = '''Configuration updated: %s is no longer configured for execution.'''
EXEC_LIST           = '''Commands configured for execution:'''
EXEC_EDIT           = '''Configuration updated for '%s'.'''
#monitor/tail
MONITOR_ADD         = '''Added monitor of '%(name)s'.'''
MONITOR_REMOVE      = '''Removed monitor of '%(name)s'.'''
MONITOR_EDIT        = '''Modified monitor of '%(name)s'.'''
MONITOR_ERROR       = '''The data input "%s" is not currently configured.'''
#show
SHOW_WEBPORT        = '''Web port: %s.'''
SHOW_SPLUNKDPORT    = '''Splunkd port: %s.'''
SHOW_HOSTNAME       = '''Default hostname for data inputs: %s.'''
SHOW_MINFREEMB      = '''Indexing of data will stop when free disk space is at or below %s MB.'''
SHOW_SERVERNAME     = '''Server name: %s.'''
SHOW_DATASTOREDIR   = '''Datastore path: %s'''
SHOW_CONFIG_ERROR   = '''An error occurred: Config %s does not exist'''
#set
SET_HOSTNAME        = '''Default hostname set.'''
SET_SPLUNKDPORT     = '''The server\'s splunkd port has been changed. You must restart the server with the command "splunk restart". Until the server restarts, many commands will fail with the error "splunkd is not running."'''
SET_DATASTOREDIR    = '''Datastore path changed to '"%s"'.'''
SET_DEFAULT_INDEX   = '''Default index set to %s.'''
#user
USER_REMOVE         = '''User removed.'''
USER_ADD            = '''User added.'''
USER_EDIT           = '''User %s edited.'''
#index
INDEX_LIST          = '''List databases called'''
INDEX_DISABLED      = '''Index %s has been disabled.'''
INDEX_ENABLED       = '''Index %s has been enabled.'''
INDEX_ERROR         = '''Index %s does not exist.'''
#udp
UDP_ADD             = '''Listening for UDP input on port %(name)s.'''
UDP_EDIT            = '''Updated configuration.'''
UDP_LIST_NONE       = '''Splunk is not listening for input on any UDP input.'''
UDP_LIST            = '''Listening for input on the following UDP ports: %s'''
UDP_LIST_NO_DATA    = '''Splunk has not received input on any UDP input since last server restart.'''
UDP_LIST_DATA       = '''Received input from the following UDP ports: %s'''
UDP_REMOVE          = '''Removed UDP input on port %(name)s.'''
#tcp
TCP_LIST            = '''Splunk is listening for data on ports: %s'''
TCP_LIST_NONE       = '''Splunk is currently not listening to any TCP input.'''
TCP_ADD             = '''Listening for data on TCP port %(name)s.'''
TCP_EDIT            = '''Updated configuration.'''
#help
HELP_NONE           = '''There is no extended help for '%(cmdname)s'.'''
#dispatch
DISPATCH            = '''Job id is: %s'''
SEARCH_ARGS_ERROR   = '''The following required parameters have not been specified: terms.'''
SEARCH_ARGS_TERMS_EMPTY = '''The value passed in for the 'terms' argument is empty'''
#saved-search
SAVED_SEARCH_EDIT   = '''Saved Search '%s' saved.'''
SAVED_SEARCH_ADD    = '''Saved Search '%s' saved.'''
SAVED_SEARCH_REMOVE = '''Saved Search '%s' deleted.'''
SAVED_SEARCH_ERROR  = '''Saved Search '%s' does not exist.'''
#forward-server
FORWARD_SERVER_LIST = '''Active Splunk-2-Splunk Forwards:\n%s\nConfigured but inactive Splunk-2-Splunk Forwards:\n%s'''
FORWARD_COND        = '''Note that this applies only if forwarding is configured.'''
LOCAL_INDEX_NONE    = '''Local indexing is disabled.'''
LOCAL_INDEX_ENABLE  = '''Local indexing is enabled.'''
LOCAL_INDEX_DISABLE = '''Local indexing is now disabled.'''
FORWARD_SERVER_ADD  = '''Added Splunk-2-Splunk forwarding to: %s'''
FORWARD_SERVER_REMOVE = '''Stopped Splunk-2-Splunk forwarding to: %s'''
#deployment server/client
DEPLOYMENT_CLIENT_DISABLED = '''Deployment Client is disabled.'''
DEPLOYMENT_SERVER_DISABLED ='''Deployment Server is disabled.'''
DEPLOYMENT_CLIENT_ENABLED  = '''Deployment Client is enabled.'''
DEPLOYMENT_SERVER_ENABLED  ='''Deployment Server is enabled.'''
RELOAD_DEPLOY_SERVER       = '''Reloading serverclass(es).'''
REFRESH_DEPL_CLIENTS_REMOVED       = '''This command has been removed'''
DEPLOYMENT_CLIENT_NONE     = '''No deployment clients have contacted this server.'''
DEPLOY_POLL_SHOW_NONE      = '''Deployment Server URI is not set.'''
DEPLOY_POLL_SHOW           = '''Deployment Server URI is set to %s.'''
VALIDATE_DEPLOY_SERVER      = '''Validating serverclass.'''
#apps
APP_ALREADY_ENABLED  = '''App '%s' is already enabled.'''
APP_ENABLED          = '''App '%s' is enabled.'''
APP_ALREADY_DISABLED = '''App '%s' is already disabled.'''
APP_DISABLED         = '''App '%s' is disabled.'''
APP_REMOVED          = '''App '%s' is removed.'''
APP_CREATED          = '''App '%s' is created.'''
APP_PACKAGED         = '''App '%s' is packaged.\nPackage location: %s'''
APP_INSTALLED        = '''App '%s' is %s.'''
APP_EDITED           = '''App '%s' is edited.'''
APP_ERROR            = '''App '%s' does not exist.'''
#auth-method
AUTH_METHOD_SHOW  = '''Authentication type is: %s.'''
AUTH_METHOD_NONE1 = '''No authentication type found in data returned from server.'''
AUTH_METHOD_NONE2 = '''The auth method '%s' does not currently exist, and thus cannot be removed.'''
AUTH_METHOD_LIST  = '''Authentication methods:'''
AUTH_METHOD_ADD   = '''Added and activated authentication type '%s'.\nNOTE: This invalidates all existing user sessions.  All users will need to re-login.'''
AUTH_METHOD_RELOAD = '''Authentication system reloaded.'''
#distributed search
SEARCH_SERVER_ADD     = '''Peer added'''
SEARCH_SERVER_ADD_EXISTS = '''The server at '%s' already exists in the distributed search list.'''
SEARCH_SERVER_ADD_ERR = '''Unable to add peer'''
SEARCH_SERVER_REMOVE = '''Peer removed'''
SEARCH_SERVER_REMOVE_ERR = '''Unable to remove peer'''
SEARCH_SERVER_REMOVE_NONE = '''The server at '%s' does not exist in the distributed search list.'''
DIST_SEARCH_ENABLE    = '''Distributed Search enabled'''
DIST_SEARCH_DISABLE   = '''Distributed Search disabled.'''
DIST_SEARCH_DISPLAY_ENABLED   = '''Distributed Search is enabled.'''
DIST_SEARCH_DISPLAY_DISABLED  = '''Distributed Search is disabled.'''
DIST_SEARCH_EDIT = '''Changes saved.'''
DIST_SEARCH_LIST = '''Server at URI "%s" with status as "%s"'''
DIST_SEARCH_LIST_NONE = '''(no servers)'''

ASYNC_SEARCH_JOBS = 'Asynchronous jobs:'
ASYNC_SEARCH_NONE = 'There are no asynchronous jobs currently.'
ASYNC_SEARCH_ERROR = 'Job id "%s" does not exist'
ASYNC_REMOVE_ALL   = 'Job with id(s) %s have been cancelled'
#oneshot
ONESHOT_ADD        = 'Oneshot "%s" added'
#no info
NO_INFO             = '''No data available'''
#restart
RESTART_SPLUNK      = '''You need to restart the Splunk Server for your changes to take effect.'''

#borrowed from old cli...
# we don't want to report these _internal tails
INTERNAL_TAILS = [
    os.path.join(os.path.sep, 'var', 'log', 'splunk', i) for i in (
      'license_audit.log',
      'metrics.log',
      'searchhistory.log',
      'splunkd.log',
      'splunkSearch.log',
      'web_access.log',
      'web_service.log')]

INDEX_NAME_MAP = {
                   '*': 'All non-internal indexes',
                   '_*': 'All internal indexes',
                 }

# --------------
def debuglog(f):
   """
   prints out a dump of the kwargs if in debug mode
   """
   def wrapper(**kwargs):
      logger.debug('In %s: kwargs: %s' % (f.__name__, str(kwargs)))
      return f(**kwargs)
   return wrapper

# -------------------------------------
#goes only one level deep for now
def encodeWith(f, encodewith='utf-8'):
   """
   encode all args back so we can print them out
   """
   if sys.version_info >= (3,0):  # no-op on Python 3
      return f
   def wrapper(**kwargs):
      for k, v in kwargs.items():
         if isinstance(v, str):
            kwargs[k] = v.encode(encodewith)
         elif isinstance(v, list):
            kwargs[k] = [item.encode(encodewith) for item in v]
         elif isinstance(v, dict):
            for ik, iv in v.items():
               if isinstance(iv, list):
                  v[ik] = [item.encode(encodewith) for item in iv]
               else:
                  v[ik] = iv.encode(encodewith)
            kwargs[k] = v
         return f(**kwargs)
   return wrapper

# -----------
@encodeWith
@debuglog
def displayGenericError(**kwargs):
   """
   display custom error msges needed in particular cases
   """

   if kwargs['cmd'] in ['search', 'dispatch']:
      if 'terms' in kwargs and kwargs['terms'] == None:
         logger.error(SEARCH_ARGS_ERROR)
      elif 'terms' in kwargs and not kwargs['terms'].strip():
         logger.error(SEARCH_ARGS_TERMS_EMPTY)
      sys.exit(4)
   elif kwargs['obj'] == 'search-server':
      if kwargs['cmd'] == 'add':
         logger.error(SEARCH_SERVER_ADD_EXISTS % kwargs['host'])
      elif kwargs['cmd'] == 'remove':
         logger.error(SEARCH_SERVER_REMOVE_NONE % kwargs['host'])
      sys.exit(4)
   elif kwargs['cmd'] in ['set', 'show']:
      logger.error('Invalid subcommand: %s. Please see splunk help %s' % (kwargs['obj'], kwargs['cmd']))
      sys.exit(4)
   elif kwargs['obj'] == 'jobs':
      logger.error(kwargs['err_msg'])
      sys.exit(4)

# ---------------------------------------
@encodeWith
@debuglog
def displayResourceError(**kwargs):
   """
   displays err messages on ResourceNotFound exceptions
   """

   if kwargs['obj'] in ['monitor', 'tail']:
      path = kwargs['uri'].split('/')[-1]
      while path != urllib_parse.unquote(path):
         path = urllib_parse.unquote(path)
      logger.error(MONITOR_ERROR % path)      
   elif kwargs['cmd'] == 'show' and kwargs['obj'] == 'config':
      logger.error(SHOW_CONFIG_ERROR % kwargs['uri'].split('/')[-1])
   elif kwargs['obj'] == 'jobs':
      if kwargs['cmd'] in ['remove', 'show', 'display']:
         logger.error(ASYNC_SEARCH_ERROR % kwargs['uri'].split('/')[-1])
   elif kwargs['obj'] == 'app':
      if kwargs['cmd'] in ['install', 'package']:
         msg = kwargs['serverContent'].get_message_text()
         logger.error(re.sub('^([^:]*: )', '', msg))
      else:
         logger.error(APP_ERROR % kwargs['uri'].split('/')[-1])
   elif kwargs['obj'] == 'index':
      if kwargs['cmd'] in ['enable', 'disable']:
         logger.error(INDEX_ERROR % kwargs['uri'].split('/')[-2]) #uri appears as /services/data/indexes/<index>/enable
      else:
         logger.error(INDEX_ERROR % kwargs['uri'].split('/')[-1]) #uri appears as /services/data/indexes/<index>
   elif kwargs['obj'] == 'saved-search' and kwargs['cmd'] in ['edit', 'remove']:
       logger.error(SAVED_SEARCH_ERROR % kwargs['uri'].split('/')[-1])
   elif kwargs['obj'] == 'deploy-server' and kwargs['cmd'] == 'reload':
       logger.error('Specified server class could not be found. Please make sure that server class is configured in deployment server.')
   else:
      logger.error('%s' % (kwargs['serverContent'].get_message_text()))
      logger.debug('Splunkd server REST interface returned an error: cmd: %s, obj: %s, uri: %s, error_text: %s. Please file a case online at http://www.splunk.com/page/submit_issue' % (kwargs['cmd'], kwargs['obj'], kwargs['uri'], kwargs['serverContent']))

   sys.exit(2)

# ----------------------------------
@encodeWith
@debuglog
def displayRoleMappings(**kwargs):
   """
   list role-mappings
   """
   if kwargs['cmd'] == 'list':
      atom = rest.format.parseFeedDocument(kwargs['serverContent'])

      for entry in atom:
         d = format.nodeToPrimitive(entry.rawcontents)
         if d['roles']:
            print('Splunk role %s maps to : %s' % (entry.title, d['roles']))
         else:
            print('Splunk role %s maps to : (none)' % (entry.title))
     
# ----------------------------
@encodeWith
@debuglog 
def displayOneshot(**kwargs):
      if kwargs['cmd'] == 'add':
            print(ONESHOT_ADD % kwargs['eaiArgsList']['name'])
# ----------------------------
@encodeWith
@debuglog
def displayMonitor(**kwargs):
      """
      called for displaying all monitor related commands.
      """

      if kwargs['cmd'] == 'remove':
            print(MONITOR_REMOVE % kwargs['eaiArgsList'])
      elif kwargs['cmd'] == 'add':
            print(MONITOR_ADD % kwargs['eaiArgsList'])
      elif kwargs['cmd'] == 'edit':
            print(MONITOR_EDIT % kwargs['eaiArgsList'])
      elif kwargs['cmd'] == 'list':

         atom = rest.format.parseFeedDocument(kwargs['serverContent'])
         dir_entries = ''
         file_entries = ''

         for entry in atom:
            d = format.nodeToPrimitive(entry.rawcontents)
            # entry.links is a list of tuples, link name->href.
            if len([x for x in entry.links if x[0] == 'members']) > 0:
               dir_entries += '\n\t%s' % entry.title  
               dir_files = extractTitleFeed([t for t in entry.links if t[0] == 'members'], sessionKey=kwargs['sessionKey'])
               if dir_files:
                  for f in dir_files:
                     dir_entries += '\n\t\t%s' % f 
               else:
                  dir_entries += '\n\t\t[No files in this directory monitored.]'
            else:
               if 'show-hidden' in kwargs['eaiArgsList'] and util.normalizeBoolean(kwargs['eaiArgsList']['show-hidden']):
                  file_entries += '\t%s\n' % entry.title          
               elif not isInternalTail(entry.title):
                  file_entries += '\t%s\n' % entry.title
      
         if not file_entries:
            file_entries = 'Monitored Files:\n\t\t[No files monitored.]'
         else:
            file_entries = 'Monitored Files:\n' + file_entries.encode('utf-8')

         if not dir_entries:
            dir_entries = 'Monitored Directories:\n\t\t[No directories monitored.]'
         else:
            dir_entries = 'Monitored Directories:' + dir_entries.encode('utf-8')

         display = '%s\n%s' % (dir_entries, file_entries)

         print(display)


# --------------------------
@encodeWith
@debuglog
def displayIndex(**kwargs):
      """
      called for displaying all index related commands.
      """
  
      if kwargs['cmd'] == 'add':
         print('Index "%s" added' % kwargs['eaiArgsList']['name'])
         print(RESTART_SPLUNK)
      elif kwargs['cmd'] == 'edit':
         print('Index "%s" edited' % kwargs['eaiArgsList']['name'])
         print(RESTART_SPLUNK)
      elif kwargs['cmd'] == 'remove':
         print('Index "%s" removed' % kwargs['eaiArgsList']['name'])
         print(RESTART_SPLUNK)
      elif kwargs['cmd'] == 'disable':
         print(INDEX_DISABLED % kwargs['eaiArgsList']['name'])
         print(RESTART_SPLUNK)
      elif kwargs['cmd'] == 'enable':
         print(INDEX_ENABLED % kwargs['eaiArgsList']['name'])
         print(RESTART_SPLUNK)
      elif kwargs['cmd'] == 'list':

         atom = rest.format.parseFeedDocument(kwargs['serverContent'])
         display = ''
         for entry in atom:
            d = format.nodeToPrimitive(entry.rawcontents)
            if d['defaultDatabase'] == entry.title:
               display += '%s * Default *' % entry.title
            else:
               display += '%s' % entry.title
            #SPL-27068
            if util.normalizeBoolean(d['disabled']):
               display += ' * Disabled *'
            display += '\n'
            if not kwargs['eaiArgsList']['name']:
               display += '\t%s\n\t%s\n\t%s\n' % (d['homePath_expanded'], d['coldPath_expanded'], d['thawedPath_expanded'])
            else:
               #we have asked about a specific index, so show everything
               for k in d:
                  display += '\t%s : %s\n' % (k, d[k])

         print(INDEX_LIST)
         print(display)

# -----------------------------
@encodeWith
@debuglog
def displaySettings(**kwargs): 
      """
      called for displaying all settings related commands.
      """

      #SPL-24723
      if kwargs['obj'] == 'license':
         atom = rest.format.parseFeedDocument(kwargs['serverContent'])
         product = licenselevel = expdate = daysRemainingStr = peakUsage = licenseviolations = currentDailyUsageAmount = expirationState = maxViolations = violationPeriod = ''
         for entry in atom:
            d = format.nodeToPrimitive(entry.rawcontents)
            try:
               currentDailyUsageAmount = d['currentDailyUsageAmount']
            except:
               pass

            try:
               expirationState = d['expirationState']
            except:
               pass

            try:
               maxViolations = d['maxViolations']
            except:
               pass

            try:
               violationPeriod = d['violationPeriod']
            except:
               pass

            if 'licenseType' in d:
               if d['licenseType'] == 'pro':
                  product = 'Enterprise'
               else:
                  product = d['licenseType']
            if 'licenseDailyUsageLimit' in d:
               licenselevel = float( d["licenseDailyUsageLimit"] ) / 1048576
            if 'remainingTime' in d:
               secondsRemaining = int(d["remainingTime"])
               daysRemaining = ((secondsRemaining / (24 * 3600)) + 1)
               daysRemainingStr = "expired" if (daysRemaining < 0) else str(daysRemaining) + ( " days" if (daysRemaining > 1) else " day" )
            if 'peakIndexingThroughput' in d:
               peakUsage= float(d["peakIndexingThroughput"]) / 1048576
            if "expirationDate" in d:
               expdate = util.parseISO(d["expirationDate"])
            if "licenseViolations" in d:
               for violation in d["licenseViolations"]:
                  violationDate = violation.split(' ', 1)[0]
                  violationString = violation.split(' ', 1)[1]
                  licenseviolations += '%s at %s\n' % (violationString, util.parseISO(violationDate))

         print('Product: \t\t\t%s' % product)
         print('License level: \t\t\t%s MB' % licenselevel)
         print('Days remaining: \t\t%s' % daysRemainingStr)
         print('Peak usage: \t\t\t%s MB' % peakUsage)
         print('Expiration date: \t\t%s' % expdate)
         print('License violations: \t\t%s' % licenseviolations)
         print('Current Daily Usage Amount: \t%s' % currentDailyUsageAmount)
         print('Expiration State: \t\t%s' % expirationState)
         print('Max Violations: \t\t%s' % maxViolations)
         print('Violation Period: \t\t%s' % violationPeriod)

      elif kwargs['obj'] == 'config':
         display = ''
         for k in kwargs['conf']:
            display += '[%s]\n' % kwargs['conf'][k].name
            for item in kwargs['conf'][k].items():
               display += '%s = %s\n' % (item[0], item[1])
         print(display)
      elif kwargs['cmd'] in ['enable', 'disable'] and kwargs['obj'] in ['web-ssl', 'webserver']:
         print(RESTART_SPLUNK)
      elif kwargs['cmd'] == 'show':
         if kwargs['obj'] == 'default-hostname':
            print(SHOW_HOSTNAME % extractLevel1Feed(serverContent=kwargs['serverContent'], filter=['host']))
         elif kwargs['obj'] == 'datastore-dir':
            print(SHOW_DATASTOREDIR % extractLevel1Feed(serverContent=kwargs['serverContent'], filter=['SPLUNK_DB']))
         elif kwargs['obj'] == 'default-index':
            for ele in kwargs['defIndex']:
               try:
                  print(INDEX_NAME_MAP[ele])
               except KeyError:
                  print(ele)
         else:
            print(NO_INFO)
      elif kwargs['cmd'] == 'set':
         if kwargs['obj'] == 'default-hostname':
            print(SET_HOSTNAME)
            print(RESTART_SPLUNK)
         elif kwargs['obj'] == 'datastore-dir':
            print(SET_DATASTOREDIR % kwargs['eaiArgsList']['SPLUNK_DB'])
            print(RESTART_SPLUNK)
         elif kwargs['obj'] == 'default-index':
            print(SET_DEFAULT_INDEX % kwargs['eaiArgsList']['srchIndexesDefault'])
         else:
            print(NO_INFO)

      else:
         print(NO_INFO)

# -------------------------
@debuglog
def displayUser(**kwargs):
      """
      called for displaying all user related commands.
      """

      if kwargs['cmd'] == 'list':

         atom = rest.format.parseFeedDocument(kwargs['serverContent'])
         display = ''
         for entry in atom:
            d = format.nodeToPrimitive(entry.rawcontents)

            display += 'username:\t\t%s\n' % entry.title
            display += 'full-name:\t\t%s\n' % d['realname']
            try:
               display += 'role:\t\t\t%s\n' % ':'.join(d['roles'])
            #SPL-23772
            except TypeError:
               display += 'role:\t\t\t\n'
            display += '\n'

      elif kwargs['cmd'] == 'remove':
         display = USER_REMOVE
      elif kwargs['cmd'] == 'add': 
         display = USER_ADD
      elif kwargs['cmd'] == 'edit':
         display = USER_EDIT % kwargs['eaiArgsList']['name']

      print(display)


# ------------------------
@encodeWith
@debuglog
def displayUdp(**kwargs):
      """
      called for displaying all udp related commands.
      """

      if kwargs['cmd'] == 'add':
         print(UDP_ADD % kwargs['eaiArgsList'])
      elif kwargs['cmd'] == 'edit':
         print(UDP_EDIT % kwargs['eaiArgsList'])
      elif kwargs['cmd'] == 'list':
         atom = rest.format.parseFeedDocument(kwargs['serverContent'])
         ports = ''
         for entry in atom:
            d = format.nodeToPrimitive(entry.rawcontents)
            if 'group' in d and d['group'] == 'listenerports':
               ports += '\n\t%s' % entry.title

         if ports:
            print(UDP_LIST % ports)
         else:
            print(UDP_LIST_NONE)
      elif kwargs['cmd'] == 'remove':
         print(UDP_REMOVE % kwargs['eaiArgsList'])


# ------------------------
@encodeWith
@debuglog
def displayTcp(**kwargs):
      """
      called for displaying all tcp related commands.
      """

      if kwargs['cmd'] == 'list':

         atom = rest.format.parseFeedDocument(kwargs['serverContent'])
         display = ''
         for entry in atom:
            d = format.nodeToPrimitive(entry.rawcontents)
            try:
               display += '\n\t%s for data from host %s' % (entry.title, d['restrictToHost'])
            except KeyError:
               display += '\n\t%s for data from any host' % entry.title

         if display: 
            print(TCP_LIST % display)
         else:
            print(TCP_LIST_NONE)
      elif kwargs['cmd'] == 'remove':
         print(str(dict({'removed':['tcp://%s' % kwargs['eaiArgsList']['name']]})))
      elif kwargs['cmd'] == 'add':
         print(TCP_ADD % kwargs['eaiArgsList'])
      elif kwargs['cmd'] == 'edit':
         print(TCP_EDIT)

# ---------------------------
@encodeWith
@debuglog
def displayHelp(**kwargs):
   """
   called for displaying all help text.
   """

   try:
      symbol_name = kwargs['help_text']
      if symbol_name not in literals.__dict__:
          raise SyntaxError
      print(literals.__dict__[symbol_name])
   except SyntaxError:
      #if there is no help for the requested cmd, kwargs['help_text'] will be ''
      print(HELP_NONE % kwargs)
      sys.exit(1)

# --------------------------------
@encodeWith
@debuglog
def displaySavedsearch(**kwargs):
   """
   called for displaying all saved searches.
   """

   if kwargs['cmd'] == 'add':
      display = SAVED_SEARCH_ADD % kwargs['eaiArgsList']['name']
   elif kwargs['cmd'] == 'remove':
      display = SAVED_SEARCH_REMOVE % kwargs['eaiArgsList']['name']
   elif kwargs['cmd'] == 'edit':
      display = SAVED_SEARCH_EDIT % kwargs['eaiArgsList']['name']
   elif kwargs['cmd'] == 'list':
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])

      display = ''
      for atomEntry in atomFeed:
         d = format.nodeToPrimitive(atomEntry.rawcontents)
         alert = event = ''
         display += 'name:\t\t%s\n' % atomEntry.title

         if int(d['is_scheduled']): alert = 'true'
         else: alert = 'false'

         display += 'alert:\t\t%s\n' % alert

   print(display)

# ----------------------------------
@encodeWith
@debuglog
def displayForwardServer(**kwargs):
   """
   called for displaying forward-server stuff.
   """

   if kwargs['cmd'] == 'display' and kwargs['obj'] == 'local-index':
      local_index = extractLevel1Feed(serverContent=kwargs['serverContent'], filter=['indexAndForward'])
      local_index = util.normalizeBoolean(local_index)
      if not local_index:
         print(LOCAL_INDEX_NONE)
      elif local_index:
         print(LOCAL_INDEX_ENABLE)
   elif kwargs['cmd'] == 'enable' and kwargs['obj'] == 'local-index':
      print(LOCAL_INDEX_ENABLE)
      print(FORWARD_COND)
      print(RESTART_SPLUNK)
   elif kwargs['cmd'] == 'disable' and kwargs['obj'] == 'local-index':
      print(LOCAL_INDEX_DISABLE)
      print(FORWARD_COND)
      print(RESTART_SPLUNK)
   elif kwargs['cmd'] == 'list':
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])
      ok_list = nok_list = ''

      for entry in atomFeed:
         d = format.nodeToPrimitive(entry.rawcontents)
         if 'status' in d and d['status'] == 'connect_done':
            ok_list += '\n\t%s' % entry.title
         else:
            nok_list += '\n\t%s' % entry.title
      
      print(FORWARD_SERVER_LIST % (ok_list, nok_list))
   elif kwargs['cmd'] == 'add':
      display = FORWARD_SERVER_ADD % kwargs['eaiArgsList']['name']
      print(display)
      print(RESTART_SPLUNK)
   elif kwargs['cmd'] == 'remove':
      print(FORWARD_SERVER_REMOVE % kwargs['eaiArgsList']['name'])
      print(RESTART_SPLUNK)
   elif kwargs['cmd'] == 'edit':
      print(RESTART_SPLUNK)

# -------------------------
@encodeWith
@debuglog
def displayApp(**kwargs):
   """
   called for displaying applications stuff.
   """

   if kwargs['cmd'] == 'display':
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])

      print('\n')
      for atomEntry in atomFeed:
         d = format.nodeToPrimitive(atomEntry.rawcontents)
         appName = atomEntry.title
         enabled = 'DISABLED' if util.normalizeBoolean(d['disabled']) else 'ENABLED'
         visible = 'VISIBLE' if util.normalizeBoolean(d['visible']) else 'INVISIBLE'         
         configured = 'CONFIGURED' if util.normalizeBoolean(d['configured']) else 'UNCONFIGURED'

         print('  %-25s  %-8s  %-9s  %-12s\n' % (appName, enabled, visible, configured))

   elif kwargs['cmd'] == 'enable':
      print(APP_ENABLED % kwargs['eaiArgsList']['name'])
      print(RESTART_SPLUNK)

   elif kwargs['cmd'] == 'disable':
      print(APP_DISABLED % kwargs['eaiArgsList']['name'])
      print(RESTART_SPLUNK)
      
   elif kwargs['cmd'] == 'remove':
      print(APP_REMOVED % kwargs['eaiArgsList']['name'])
      
   elif kwargs['cmd'] == 'create':
      print(APP_CREATED % kwargs['eaiArgsList']['name'])

   elif kwargs['cmd'] == 'edit':
      print(APP_EDITED % kwargs['eaiArgsList']['name'])
      print(RESTART_SPLUNK)
      
   elif kwargs['cmd'] == 'package':
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])
      d = format.nodeToPrimitive(atomFeed[0].rawcontents)
      print(APP_PACKAGED % (d['name'], d['path']))
      
   elif kwargs['cmd'] == 'install':
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])
      d = format.nodeToPrimitive(atomFeed[0].rawcontents)
      print(APP_INSTALLED % (d['name'], d['status']))


# -------------------------------
@encodeWith
@debuglog
def displayAuthMethod(**kwargs):
   """
   called for displaying auth-method stuff
   """

   if kwargs['cmd'] == 'show':

      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])

      for entry in atomFeed:
         if entry.title == 'active_authmodule':
            d = format.nodeToPrimitive(entry.rawcontents)

            try:
               print(AUTH_METHOD_SHOW % d['active_authmodule'])
            except KeyError:
               print(AUTH_METHOD_NONE1)

   elif kwargs['cmd'] == 'reload':
      print(AUTH_METHOD_RELOAD)

   elif kwargs['cmd'] == 'add':
      print(AUTH_METHOD_ADD % kwargs['eaiArgsList']['authType'])

   elif kwargs['cmd'] == 'list':

      print(AUTH_METHOD_LIST)
 
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])

      for entry in atomFeed:

         if entry.title == 'services':
            continue

         print('\nSettings for %s:' % entry.title)
         d = format.nodeToPrimitive(entry.rawcontents)
         for k, v in d.items():
            print('  %-30s%s' % (k + ':', ((v != '') and v or '(empty)')))
   
#--------------------------------
@encodeWith
@debuglog   
def displayDistSearch(**kwargs):
   """
   called for distributed search stuff
   """

   if kwargs['cmd'] == 'enable' and kwargs['obj'] == 'dist-search':
      print(DIST_SEARCH_ENABLE)
      print(RESTART_SPLUNK)
   elif kwargs['cmd'] == 'disable' and kwargs['obj'] == 'dist-search':
      print(DIST_SEARCH_DISABLE)
      print(RESTART_SPLUNK)
   elif kwargs['cmd'] == 'display' and kwargs['obj'] == 'dist-search':
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])

      for entry in atomFeed:

         if entry.title == 'distributedSearch':
            d = format.nodeToPrimitive(entry.rawcontents)
            if not util.normalizeBoolean(d['disabled']):
               print(DIST_SEARCH_DISPLAY_ENABLED)
               return

      print(DIST_SEARCH_DISPLAY_DISABLED)
 
   elif kwargs['cmd'] == 'add':
      print(SEARCH_SERVER_ADD)
   elif kwargs['cmd'] == 'remove':
      print(SEARCH_SERVER_REMOVE)
   elif kwargs['cmd'] == 'edit':
      print(DIST_SEARCH_EDIT)
   elif kwargs['cmd'] == 'list' and kwargs['obj'] == 'search-server':
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])

      servers_present = False

      for entry in atomFeed:
         d = format.nodeToPrimitive(entry.rawcontents)
         if 'status' in d:
            servers_present = True
            print(DIST_SEARCH_LIST % (entry.title, d['status']))
         if 'status_details' in d:
            for msg in d['status_details']:
               print("\tWARN: %s" % msg)

      if not servers_present:
         print(DIST_SEARCH_LIST_NONE)

# ----------------------------------
@encodeWith
@debuglog
def displayDeployment(**kwargs):
   """
   called for displayin deployment client/server stuff
   """

   if kwargs['cmd'] == 'refresh' and kwargs['obj'] == 'deploy-clients':
      print(REFRESH_DEPL_CLIENTS_REMOVED)
   elif kwargs['cmd'] == 'show' and kwargs['obj'] == 'deploy-poll':
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])
      if not atomFeed.entries:
         print(DEPLOY_POLL_SHOW_NONE)
      else:
         d = {}
         for entry in atomFeed:
            if entry.title == 'deployment-client':
               d = format.nodeToPrimitive(entry.rawcontents)
               try:
                  print(DEPLOY_POLL_SHOW % d['targetUri'])
               except KeyError:
                  print(DEPLOY_POLL_SHOW_NONE)
               break
   elif kwargs['cmd'] == 'list' and kwargs['obj'] == 'deploy-clients':
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])
      if not atomFeed.entries:
         print(DEPLOYMENT_CLIENT_NONE)
      else:
         for entry in atomFeed:
            print("\nDeployment client: %s" % entry.title)
            d = format.nodeToPrimitive(entry.rawcontents)
            for k in d:
               if k.startswith('eai:acl'):
                  continue
               print("\t\t %s:       %s" % (k, d[k]))

   elif kwargs['cmd'] == 'reload' and kwargs['obj'] == 'deploy-server':
      if 'validate-only' in kwargs['eaiArgsList']:
         print(VALIDATE_DEPLOY_SERVER)
      else:
         print(RELOAD_DEPLOY_SERVER)

      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])
      if not atomFeed.entries:
          print('empty atomFeed; BUG!')
          sys.exit(21)
      else:
         for entry in atomFeed: # there will be only 1 entry
            d = format.nodeToPrimitive(entry.rawcontents)
            for k in d:
               if k == 'requireRestart':
                   print(RESTART_SPLUNK)

   elif kwargs['cmd'] == 'set' and kwargs['obj'] == 'deploy-poll':
      print('Configuration updated.')
   elif kwargs['cmd'] == 'enable' and kwargs['obj'] == 'deploy-server':
      print(DEPLOYMENT_SERVER_ENABLED)
   elif kwargs['cmd'] == 'disable' and kwargs['obj'] == 'deploy-server':
      print(DEPLOYMENT_SERVER_DISABLED)
   elif kwargs['cmd'] == 'enable' and kwargs['obj'] == 'deploy-client':
      print(DEPLOYMENT_CLIENT_ENABLED)
   elif kwargs['cmd'] == 'disable' and kwargs['obj'] == 'deploy-client':
      print(DEPLOYMENT_CLIENT_DISABLED)
   elif kwargs['cmd'] == 'display':
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])

      d = {}

      for entry in atomFeed:

         if kwargs['obj'] == 'deploy-server' and entry.title == 'default':
            d = format.nodeToPrimitive(entry.rawcontents)
            try:
               if not util.normalizeBoolean(d['disabled']):
                  print(DEPLOYMENT_SERVER_ENABLED)
                  return 
            except:
               break

         if kwargs['obj'] == 'deploy-client' and entry.title == 'default':
            d = format.nodeToPrimitive(entry.rawcontents)
            try:
               if not util.normalizeBoolean(d['disabled']):
                  print(DEPLOYMENT_CLIENT_ENABLED)
                  return 
            except:
               break

      if kwargs['obj'] == 'deploy-server':
         print(DEPLOYMENT_SERVER_DISABLED)
      elif kwargs['obj'] == 'deploy-clients':
         print(DEPLOYMENT_CLIENT_DISABLED)

# ----------------
@encodeWith
@debuglog
def displayJobs(**kwargs):
   """
   """
  
   if kwargs['cmd'] == 'list':
      atomFeed = rest.format.parseFeedDocument(kwargs['serverContent'])
      if atomFeed:
         print(ASYNC_SEARCH_JOBS)
         for entry in atomFeed:
            d = format.nodeToPrimitive(entry.rawcontents)
            print('\tJob id: %s, ttl: %s\n' % (d['sid'], d['ttl']) )
      else:
         print(ASYNC_SEARCH_NONE)
   elif kwargs['cmd'] == 'remove':
      if isinstance(kwargs['eaiArgsList']['jobid'], list):
         #we have tried to do a remove jobs all
         if kwargs['eaiArgsList']['jobid']:
            print(ASYNC_REMOVE_ALL % ','.join(kwargs['eaiArgsList']['jobid']))
         else:
            print(ASYNC_SEARCH_NONE)
      else:
         print('Job id "%s" removed.' % kwargs['eaiArgsList']['jobid'])
   elif kwargs['cmd'] == 'show':
      atom = rest.format.parseFeedDocument(kwargs['serverContent'])
      d = format.nodeToPrimitive(atom.rawcontents)
      print(atom.title)
      print('-'*len(atom.title))
      print('\n'.join(['%s:%s' % (x[0], x[1]) for x in d.items()]))
   elif kwargs['cmd'] == 'display':
      try:
         searchjob = search.getJob(kwargs['eaiArgsList']['jobid'], sessionKey=kwargs['sessionKey'])
      except:
         displayGenericError(cmd=kwargs['cmd'], obj='jobs', err_msg='Job id "%s" not found' % kwargs['eaiArgsList']['jobid'])
         return
      displaySyncSearch(searchjob=searchjob, **kwargs)

# ----------------------------------
@encodeWith
@debuglog
def displayAsyncSearch(**kwargs):
   """
   called for displaying async search results. 
   """
 
   print('Job id: %s' % kwargs['jid'])
 

# SEARCH FORMATTING CODE BEGIN

import operator
import re
import sys
if sys.version_info >= (3, 0):
    from io import StringIO
else:
    from cStringIO import StringIO


def indent(rows, hasHeader=False, headerChar='-', delim='  ', justify='left',
           separateRows=False, prefix='', postfix='', wrapfunc=lambda x:x):
    """Indents a table by column.

    >>> indent([['count'], [u'0']], hasHeader=False, separateRows=False)
    count
    -----
    0

    :param rows: Sequence of sequences of items, one sequence per row.
    :param hasHeader: True if the first row consists of the columns' names.
    :param headerChar: Character to be used for the row separator line
        (if hasHeader==True or separateRows==True).
    :param delim: The column delimiter.
    :param justify: Determines how are data justified in their column.
        Valid values are 'left','right' and 'center'.
    :param separateRows: True if rows are to be separated by a line
        of 'headerChar's.
    :param prefix: String prepended to each printed row.
    :param postfix: String appended to each printed row.
    :param wrapfunc: Function f(text) for wrapping text; each element in
        the table is first wrapped by this function.

    :returns String representing a formatted table

    """
    # closure for breaking logical rows to physical, using wrapfunc
    def rowWrapper(row):
        newRows = [wrapfunc(item).split('\n') for item in row]
        
        ml = max(map(len, newRows))
        newNewRows = []
        for i in range(ml):
            row = []
            for item in newRows:
                if i < len(item):
                    row.append(item[i])
                else:
                    row.append('')

            newNewRows.append(row)

        return newNewRows


    # break each logical row into one or more physical ones
    logicalRows = [rowWrapper(row) for row in rows]

    # columns of physical rows
    # we'll iterate over columns multiple times, so convert from iterator to list
    columns = list(zip(*reduce(operator.add, logicalRows)))
    # get the maximum of each column by the string length of its items
    maxWidths = [max([len(str(item)) for item in column]) for column in columns]
    rowSeparator = prefix + delim.join([headerChar*w for w in maxWidths]) + postfix

    # select the appropriate justify method
    justify = {'center':str.center, 'right':str.rjust, 'left':str.ljust}[justify.lower()]

    numre = re.compile("^-?\d+\.?\d*$")
    # Next line is meant to be floating point division
    numCols = [sum([(numre.match(str(item)) and 1 or 0) for item in column])*1.5 / len(column) for column in columns]
    jbycol = [(column > 1 and str.rjust or justify) for column in numCols]

    output=StringIO()
    if separateRows: output.write("%s\n" % rowSeparator)
    for physicalRows in logicalRows:
        for row in physicalRows:
            output.write( \
                prefix \
                + delim.join([jfn(str(item), width) for (item, width, jfn) in zip(row, maxWidths, jbycol)]) \
                + postfix + "\n")
        if hasHeader:
            output.write("%s\n" % rowSeparator)
            hasHeader = False
        elif separateRows:
            output.write("%s\n" % rowSeparator)
    return output.getvalue()


# written by Mike Brown
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/148061
def wrap_onspace(text, width):
    """
    A word-wrap function that preserves existing line breaks
    and most spaces in the text. Expects that existing line
    breaks are posix newlines (\n).
    """
    return reduce(lambda line, word, width=width: '%s%s%s' %
                  (line,
                   ' \n'[(len(line[line.rfind('\n')+1:])
                         + len(word.split('\n', 1)[0]
                              ) >= width)],
                   word),
                  text.split(' ')
                 )

def wrap_truncate(text, width):
    sublines = text.split('\n')

    tlines = []
    for line in sublines:
        if len(line) > width:
            tlines.append("%s..." % line[0:width])
        else:
            tlines.append(line)

    return "\n".join(tlines)
            
def wrap_onspace_strict(text, width):
    """Similar to wrap_onspace, but enforces the width constraint:
       words longer than width are split."""
    wordRegex = re.compile(r'\S{'+str(width)+r',}')
    return wrap_onspace(wordRegex.sub(lambda m: wrap_always(m.group(), width), text), width)

def wrap_always(text, width):
    """A simple word-wrap function that wraps text on exactly width characters.
       It doesn't split the text in words."""
    return '\n'.join([ text[width*i:width*(i+1)] \
                       for i in range(int(math.ceil(1.*len(text)/width))) ])

# SEARCH FORMATTING CODE END






# ----------------------------------
@encodeWith
@debuglog  
def displaySyncSearch(**kwargs):
   """
   called for displaying sync search results.
   """

   if 'detach' in kwargs and util.normalizeBoolean(kwargs['detach']):
      return displayAsyncSearch(**kwargs)

   job = kwargs['searchjob']

   if job.messages:
      for mtype in job.messages:
         for msg in job.messages[mtype]:
            sys.stderr.write("%s: %s\n" % (mtype.upper(), msg))

   if not job.resultCount:
      return

   format = kwargs.get('output', job.reportSearch and 'table' or 'rawevents')
   time_format = kwargs.get('time_format', '%+')

   if format == 'rawevents' and '_raw' in job.results.fieldOrder:
      job.setFetchOptions(fieldList='_raw')
      for result in job.results:
         print(splunk.util.unicode(result['_raw']))
      return

   if format == 'raw':
      first = True
      for result in job.results:
         if not first:
            print('-'*80)
         first = False
         for field in result:
            print("\t%s = %s" % (field, result[field]))
      return
   
   fields = list(filter((lambda x: x[0] != '_' or x == '_raw' or x == '_time'),
                   job.results.fieldOrder))

   job.setFetchOption(fieldList=fields, time_format=time_format)

   if format == 'csv':
      print(job.getFeed('results', outputMode='csv'))
      return

   hasHeader = util.normalizeBoolean(kwargs.get('header', 'true'))

   if hasHeader:
      results = [fields]
   else:
      results = []
   
   for result in job.results:
      resultLine = [splunk.util.unicode(result.get(field, None)) for field in fields]
      results.append(resultLine)
      
   print(indent(rows=results, hasHeader=hasHeader, separateRows=False))


# ----------------------------------
@encodeWith
@debuglog
def displayDistribSearch(**kwargs):
   """
   """
   pass

# ----------------------------------------
def extractLevel1Feed(**kwargs):
   """
   we need only the contents of the feed returned possibly with it being filtered

   serverContent > response from the server (assuming the status is 200)
   filter        > a list of all the cli field names to filter on eg. ['web-port', 'splunkd-port', 'minfreemb']
                   With the above list the returned feed is filtered to display only the 'web-port', 'splunkd-port', 'minfreemb' values.
                   Mapping b/w cli-eai field names happens in the background.
   """

   atom = rest.format.parseFeedDocument(kwargs['serverContent'])
   if isinstance(atom, format.AtomEntry):
      d = format.nodeToPrimitive(atom.rawcontents)
   elif isinstance(atom, format.AtomFeed):
      d = format.nodeToPrimitive(atom[0].rawcontents)

   display = ''

   #logger.debug(str(d))
   #logger.debug(kwargs['filter'])

   if 'filter' in kwargs:
      try:
         display += d[kwargs['filter'][0]] 
      except TypeError:
         display = NO_INFO #if the contents of the desired tag in the returned feed is empty, the dict will contain None. Will get TypeError if a '+' op is attempted. So return NO_INFO.
   else:
      for k, v in d.items():
         display += '%s:\t%s\n' % (k, v)

   return display

# ------------------------------------------------
def extractTitleFeed(link_tuple_list, **kwargs):
   """
   """

   if link_tuple_list:

      logger.debug('In extractTitleFeed: link_list: %s' % str(link_tuple_list))

      serverResponse, serverContent = format.simpleRequest(link_tuple_list[0][1], sessionKey=kwargs['sessionKey'],  method='GET')

      if serverResponse.status != 200:
         raise splunk.RESTException(serverResponse.status, serverResponse.messages)

      atomFeed = rest.format.parseFeedDocument(serverContent)

      file_name = []

      for atomEntry in atomFeed:

         file_name.append(atomEntry.title)

      logger.debug(file_name)

      return file_name

# -----------------------
def isInternalTail(file):
  """
  borrowed function from old cli
  """
  # only match the files at the known part of the path cuz remote splunkds can have different splunk_homes
  return file[file.rfind(os.path.join(os.path.sep, "var", "log")):] in INTERNAL_TAILS
