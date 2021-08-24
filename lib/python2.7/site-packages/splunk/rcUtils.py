from __future__ import absolute_import

import unittest
import sys
import copy
import re
import time
import types
import stat
import os

import lxml.etree as etree

from splunk.rcCmds import remote_cmds, GLOBAL_ARGS, GLOBAL_ACTIONS, GLOBAL_DEFAULTS
from splunk.entity import buildEndpoint
from splunk.rest import simpleRequest
from splunk.search import dispatch, getJob, listJobs
from splunk.bundle import getConf
import splunk
import splunk.auth as auth
import splunk.rcDisplay
import logging as logger
from splunk import rcHooks

#documentation et all...
__doc__ = """
          utility functions that form the core of the rcBridge
          """
__version__ = "1..0.0"
__copyright__ = """  Version 4.0"""
__author__ = 'Jimmy John'

#display charateristics map
DISPLAY_CHARS = {
                  'settings':splunk.rcDisplay.displaySettings,
                  'user':splunk.rcDisplay.displayUser,
                  'monitor':splunk.rcDisplay.displayMonitor,
                  'tail':splunk.rcDisplay.displayMonitor,
                  'oneshot':splunk.rcDisplay.displayOneshot,
                  'index':splunk.rcDisplay.displayIndex,
                  'udp':splunk.rcDisplay.displayUdp,
                  'tcp':splunk.rcDisplay.displayTcp,
                  'saved-search':splunk.rcDisplay.displaySavedsearch,
                  'forward-server':splunk.rcDisplay.displayForwardServer,
                  'search:search':splunk.rcDisplay.displaySyncSearch,
                  'jobs':splunk.rcDisplay.displayJobs,
                  'search:dispatch':splunk.rcDisplay.displaySyncSearch,
                  'distributed-search':splunk.rcDisplay.displayDistribSearch,
                  'app':splunk.rcDisplay.displayApp,
                  'auth-method':splunk.rcDisplay.displayAuthMethod,
                  'role-mappings':splunk.rcDisplay.displayRoleMappings,
                  'deployments':splunk.rcDisplay.displayDeployment,
                  'distributed-search':splunk.rcDisplay.displayDistSearch,
                  'help':splunk.rcDisplay.displayHelp,
                }

#mapping b/w cmds and their associated endpoints
CMD_ENDPOINT_MAP = {
                   'show:*': 'settings',
                   'set:*': 'settings',
                   'enable:web-ssl': 'settings',
                   'disable:web-ssl': 'settings',
                   'enable:webserver': 'settings',
                   'disable:webserver': 'settings',
                   'login': 'login',
                   '*:user': 'user',
                   'add:oneshot': 'oneshot',
                   '*:monitor': 'monitor',
                   '*:tail': 'monitor',
                   '*:index': 'index',
                   '*:udp': 'udp',
                   '*:tcp': 'tcp',
                   '*:saved-search': 'saved-search',
                   '*:forward-server': 'forward-server',
                   'search:*': 'search',
                   'dispatch:*': 'search',
                   'show:jobs': 'jobs',
                   '*:jobs': 'jobs',
                   '*:local-index': 'forward-server',
                   '*:app': 'app',
                   '*:auth-method': 'auth-method',
                   'reload:auth': 'auth-method',
                   'list:role-mappings': 'role-mappings',
                   '*:search-server': 'distributed-search',
                   '*:dist-search': 'distributed-search',
                   '*:deploy-server': 'deployments',
                   '*:deploy-clients': 'deployments',
                   '*:deploy-client': 'deployments',
                   '*:deploy-poll': 'deployments', 
                   '*:exec': 'scripted',
                   '*:scripted': 'scripted',
                   'help': 'help', #special case even though help is not really an endpoint
                   }

BLACKLIST = ['set:auth-method', 'remove:auth-method', 'set:server-type', 'remove:index', 'list:app', 'add:app', 'edit:forward-server']

WHITELIST = {
              'set': ['datastore-dir', 'default-hostname', 'default-index', 'server-type',                                             'deploy-poll'],
              'show': ['datastore-dir', 'default-hostname', 'default-index', 'server-type', 'jobs', 'auth-method', 'config', 'license', 'deploy-poll'],
            }

RE_HANDLER_ERR_MSG = re.compile("In handler '.*?':")

# -----------------------------
# -----------------------------
class CliException(Exception):
   """
   base class for all cli exceptions. 
   """
   pass

# --------------------------
# --------------------------
class CliArgError(CliException):
   """
   thrown when enough args not present to construct the complete uri
   """
   pass

# ---------------------------------
# ---------------------------------
class NoEndpointError(CliException):
   """
   thrown when no endpoint exists
   """
   pass

# ---------------------------------------
# ---------------------------------------
class InvalidStatusCodeError(CliException):
   """
   if create did not return 201
   if edit/list/delete did not return 200
   """
   pass

# --------------------------
def checkStatus(**kwargs):
   """
   checks the returned HTTP status code, if it is desired for the 'type' of action performed.
   """
   etype = kwargs['type']
   server_response = kwargs['serverResponse']

   logger.debug('In checkStatus: type: %s, server_response: %s' % (etype, server_response))

   #when listing, editing or deleting we should get 200 / when creating we should get 201
   if (etype in ['list', 'remove', 'edit'] and server_response.status != 200) or (etype == 'create' and server_response.status != 201):
      err_txt = ''
      for err in server_response.messages:

         #err messages look like: "In handler '<some name>': <some msg>". Need to get rid of the first part to display better
         if RE_HANDLER_ERR_MSG.match(err['text']):
            err['text'] = re.sub(RE_HANDLER_ERR_MSG, '', err['text'])

         err_txt = (err['text'])

      raise InvalidStatusCodeError(err_txt)

# --------------------------------------------------
def layeredFind(endpoint, cmd, obj, target, parm=''):
   """
   goes through the inheritance heirarchy as determined by the remote_cmds dict and returns the final value of the target.
   """
   
   #first look in _common
   try:
      target_val = remote_cmds['_common'][cmd][target]
   except:
      target_val = '' # no target to be inherited

   #then look in the base...
   try:
      target_val = remote_cmds[endpoint]['_common'][target]
   except:
      pass # no target to be inherited

   #now check the next level i.e cmd
   try:
      target_val = remote_cmds[endpoint]['%s' % cmd][target]
   except:
      pass

   try:
      #now check level, i.e. cmd:object eg. show:license
      if ('%s:%s' % (cmd, obj)) in remote_cmds[endpoint]:
         try:
            target_val = remote_cmds[endpoint]['%s:%s' % (cmd, obj)][target]
         except:
            pass
   except:
      pass

   logger.debug('layeredFind:%s: %s' % (target, target_val))

   return target_val

# -------------------------------------
def handleHelp(endpoint, restArgList):
   """
   takes care of the help cmd
   """

   if 'cmdname' not in restArgList: #in case they type ./splunk help
      restArgList['cmdname'] = 'help'

   help_text = layeredFind('help', 'help', '', restArgList['cmdname']) #the target appears with key as cmdname

   if not help_text:
      #not a common help text, so dig through the dict to see if you can find the appropriate one
      #find the bugger using a one line list comprehension...haha...

      try:
         l = [remote_cmds[k]['_common']['help'][restArgList['cmdname']] for k in remote_cmds if k != '_common' if 'help' in remote_cmds[k]['_common'] if restArgList['cmdname'] in remote_cmds[k]['_common']['help']]
      except:
        l = '' #if something blows up here, just show no help rather than blowing up with a stacktrace

      try:
         help_text = l[0]
      except IndexError:
         help_text = ''

   #Call the appropriate display function...
   try:
      DISPLAY_CHARS[endpoint](help_text = help_text, cmdname=restArgList['cmdname'])
   except KeyError as e:
      raise

   return

# ----------------------------------------------------------------
def dispatchJob(search, sessionKey, namespace, owner, argList):
   """
   helpers fun used by both sync/async search
   """

   search = search.strip()

   argListRem = copy.deepcopy(argList)

   if len(search) == 0 or search[0] != '|':
      search = "search " + search

   #the remaining keys if any need to be passed in to the dispatch call so the endpoint can handle it. eg. the 'id' arg
   for remove_key in ['maxout', 'buckets', 'maxtime', 'authstr', 'terms']:
      try:
         argListRem.pop(remove_key)
      except:
         pass

   #rename the maxout/buckets/maxtime args - SPL-20794/SPL-20916
   argListRem['max_count'] = argList.get('maxout', 100)
   argListRem['status_buckets'] = argList.get('buckets', 0)
   argListRem['max_time'] = argList.get('maxtime', 0)

   argListRem['sessionKey'] = sessionKey
   argListRem['namespace'] = namespace
   argListRem['owner'] = owner

   try:
      searchjob = dispatch(search, **argListRem)
   except splunk.SearchException as e:
      raise
   except:
      raise #maybe somebody pressed Ctrl-C

   return searchjob

# -------------------------------------------------------------------------------
def handleAsyncSearch(search, sessionKey, namespace, owner, argList, dotSplunk):
   """
   handles the async search, TODO by S&I 
   """

   try:
      searchjob = dispatchJob(search, sessionKey, namespace, owner, argList)

      DISPLAY_CHARS['search:search'](detach='true', jid=searchjob.id)
   except KeyboardInterrupt as e:
      try:
         searchjob.cancel()
         logger.debug('Async Search job with id "%s" cancelled due to KeyboardInterrupt' % searchjob.id)
      except NameError:
         pass #no job to cancel

# --------------------------------------------------------------------
def handleSyncSearch(search, sessionKey, namespace, owner, argList):
   """
   handles the search cmd
   """

   try: 
      searchjob = dispatchJob(search, sessionKey, namespace, owner, argList) 


      sleep_time = 0.01
      while not (searchjob.isDone): 
         if searchjob.isZombie:
             logger.error('The search process seems to have crashed...')
             sys.exit(1)

         time.sleep(sleep_time)
         if sleep_time >= 1:
            sleep_time = 1
         else:
            sleep_time = sleep_time * 2

      DISPLAY_CHARS['search:search'](searchjob = searchjob, detach='false', **argList)
      #SPL-23022
      if 'timeout' not in argList:
         searchjob.cancel()
   except KeyboardInterrupt as e:
      try:
         searchjob.cancel()
         logger.error('Sync Search job with id "%s" cancelled due to KeyboardInterrupt' % searchjob.id)
      except NameError:
         pass #no job to cancel
 
# -----------------------------------------------------------
def handleShowConf(confName, sessionKey, namespace, owner):
   """
   handles the show config <confName> cmd
   """
   conf = getConf(confName, sessionKey=sessionKey, namespace=namespace, owner=owner) 
   DISPLAY_CHARS['settings'](conf=conf, cmd='show', obj='config')

# ------------------------------------------------------
def handleRemoveJobsAll(sessionKey, namespace, owner):
   """
   current hack for removing all asyn jobs - to be removed when EAI endpoint gets written to do this...
   """

   jobs = listJobs(sessionKey=sessionKey, namespace=namespace, owner=owner)
   cancelled_jobs = []
   for job in jobs:
      j = getJob(job['sid'])
      j.cancel()
      cancelled_jobs.append(job['sid'])
  
   #Call the appropriate display function...
   try:
      DISPLAY_CHARS['jobs'](cmd='remove', obj='jobs', eaiArgsList={'jobid':cancelled_jobs})
   except KeyError as e:
      logger.debug('endpoint: jobs')
      logger.debug(str(e))
      raise


# -----------------------------------------------
def sanitizeArgs(target, argsMap, argsDict):
   """
   takes a dictionary which are the get/post args and removes any keys within this which was used to construct the uri
   """

   logger.debug('In sanitizeArgs: target: %s, argsMap: %s, argsDict: %s' % (target, argsMap, argsDict))

   remove_key = re.findall('%\((.*?)\)s', target)
   if remove_key:
      try:
              for k in remove_key:
                 try:
                    #first check if this arg name has been mapped to an eai name
                    argsDict.pop(argsMap[k])
                 except KeyError:
                    #ok, maybe this argument name did not need any mapping ie. it was the same
                    argsDict.pop(k)
                 except KeyError:
                    #there is something in the eai_id that has not been converted. Bail out...
                    raise CliArgError('%s parameter not provided' % k)

      except Exception as e:
              logger.debug(str(e))
              pass

# --------------------------------------
def _validateURI(target, restArgList):
   """
   ensures that all %(<key>)s in the uri/eai_id can be honoured
   """
   if not isinstance(target, dict):
      eai_key_list = re.findall('%\((.*?)\)s', target)
      logger.debug('eai_key_list: %s' % str(eai_key_list))
      if eai_key_list:
         for k in eai_key_list:
            if k not in restArgList:
               raise CliArgError('%s parameter not provided' % k)

def quick_and_dirty_call(uri, type, getargs, postargs, namespace, owner, method='GET', sessionKey=''):
   """"""
   qad_uri = buildEndpoint(uri, entityName='', namespace=namespace, owner=owner)

   try:
      serverResponse, serverContent = simpleRequest(qad_uri, sessionKey=sessionKey, getargs=getargs, postargs=postargs, method=method)
   except Exception as e:
      logger.debug('Could not construct quick_and_dirty uri: %s, %s' % (str(qad_uri), str(e)))
      raise CliArgError('Could not get app context')

   #check the returned status code if it is ok
   try:
      checkStatus(type=type, serverResponse=serverResponse)
   except Exception as e:
      logger.debug('Could not construct quick_And_dirty uri: %s, %s' % (str(qad_uri), str(e)))
      raise CliArgError('Could not get app context')

   return serverContent


   
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def makeRestCall(cmd=None, restArgList=None, obj=None, sessionKey=None, entityName=None, search=None, count=None, offset=None, sort_key=None, sort_dir=None, dotSplunk=None, timeout=None, token=False):
   """
   main entry point for the outside world. Will make the REST call and return the results after formatting etc 
   """

   logger.debug('cmd: %s, obj: %s, restArgList: %s' % (cmd, obj, str(restArgList)))

   #if blacklisted i.e not to be run remotely, exit immediately
   if '%s:%s' % (cmd, obj) in BLACKLIST:
      raise NoEndpointError
   elif cmd in WHITELIST:
      if obj not in WHITELIST[cmd]:
         splunk.rcDisplay.displayGenericError(cmd=cmd, obj=obj)

   #look for the endpoint
   try:
      endpoint = CMD_ENDPOINT_MAP['%s:%s' % (cmd, obj)] #first try a key match with cmd and obj
   except KeyError:
      try:
         endpoint = CMD_ENDPOINT_MAP['*:%s' % obj] #now with *:obj i.e for all commands of this obj eg. add user, edit user, remove user, list user etc
      except KeyError:
         try:
            endpoint = CMD_ENDPOINT_MAP['%s:*' % cmd] #now with cmd:* i.e for all objects of this cmd eg. show web-port, show servername, show splunkd-port etc
         except KeyError:
            try:
               endpoint = CMD_ENDPOINT_MAP['%s' % cmd] #finally with only cmd
            except KeyError:
               raise NoEndpointError

   logger.debug('endpoint: %s' % endpoint)

   #the argList is used to construct the arguments to the POST/GET. We don't need the auth credential in there. So pop it out, if present.

   #if there are any default parms that need to be included for this eai request, tag them on
   argList = {}
   try:
      argList.update(layeredFind(endpoint, cmd, obj, 'default_eai_parms'))
   except:
      pass

   argList.update(restArgList)

   if 'authstr' in argList:
      argList.pop('authstr')
      logger.debug('authstr poped from argList')

   #get namespace/owner, if present
   try:
      #SPL-22621
      namespace = argList['app']
      #this arg should not go to the endpoint
      argList.pop('app')
   except:
      #requirements out of SPL-24442
      #check if there is a app_context is required
      app_context = layeredFind(endpoint, cmd, obj, 'app_context')

      if app_context:
         ac_uri = app_context['uri']
         ac_helper = app_context['helper']
         ac_type = app_context['type']

         #make a GET request to the uri
         servResp = quick_and_dirty_call(ac_uri, ac_type, {'count':'-1'}, {}, '', '', method='GET', sessionKey=sessionKey)
         #print servResp
         try:
             namespace = rcHooks.__dict__[app_context['helper']](servResp, argList)
         except Exception as e:
            logger.debug('ERROR:' + str(e))

      elif obj in ['saved-search', 'dist-search', 'search-server', 'jobs']:
         namespace = 'search'
      else:
         namespace = ''

   logger.debug('namespace: %s' % namespace)

   try:
      owner = argList['owner']
      #this arg should not go to the endpoint
      argList.pop('owner')
   except:
      owner = 'admin'

   #Building the uri...
   uri = layeredFind(endpoint, cmd, obj, 'uri')
   lf_eai_id = layeredFind(endpoint, cmd, obj, 'eai_id')

   required = layeredFind(endpoint, cmd, obj, 'required')
   
   #if u cannot build the uri/eai_id, bail out...
   _validateURI(uri, argList)
   _validateURI(lf_eai_id, argList)

   for field in required:
      if field not in argList:
         logger.error("Required field '%s' missing" % field)
         sys.exit(1)
      
   #used later on to ensure the key in %(key)s is removed from the list of args sent to the endpoint
   uri_copy = uri

   #the help is a special case. No rest call etc required currently
   if cmd == 'help':
      return handleHelp(endpoint, restArgList)
   #extraction of properties has already been written for us, so reuse it
   elif '%s:%s' % (cmd, obj) == 'show:config':
      try:
         return handleShowConf(restArgList['name'], sessionKey, namespace, owner)
      except splunk.ResourceNotFound:
         #can throw this error if we try and show a non-existent config
         splunk.rcDisplay.displayResourceError(cmd=cmd, obj=obj, uri=restArgList['name'], serverContent=None)
         return 
   #show:default-index has already been done for us, reuse it
   elif '%s:%s' % (cmd, obj) == 'show:default-index':
      defIndexList = []
      try:
         #first get the role associated with this user
         roles = auth.getUser(auth.getCurrentUser()['name'], sessionKey=sessionKey)['roles']
         #get details of each role
         for role in roles:
            indexes = auth.getRole(role, sessionKey=sessionKey)['srchIndexesDefault']
            for index in indexes:
               defIndexList.append(index)
      except:
         pass  
      DISPLAY_CHARS[endpoint](cmd=cmd, obj=obj, sessionKey=sessionKey, defIndex=defIndexList)
      
   #handle sync/async search
   elif cmd in ['search', 'dispatch']:
      if not restArgList['terms'].strip():
        splunk.rcDisplay.displayGenericError(cmd=cmd, terms='')
        return  
      if 'detach' in restArgList and restArgList['detach'] == 'true':
         return handleAsyncSearch(restArgList['terms'], sessionKey, namespace, owner, restArgList, dotSplunk)
      else:
         return handleSyncSearch(restArgList['terms'], sessionKey, namespace, owner, restArgList)
   #hack for removing all async jobs, to be removed when an EAI endpoint is provided to do this
   elif cmd == 'remove' and obj == 'jobs' and ('jobid' in restArgList) and restArgList['jobid'] == 'all':
     return handleRemoveJobsAll(sessionKey, namespace, owner)
   else:

      #Building the args taking into account the cli/eai mapping if required...

      #args contains the mapping b/w cli/eai names
      args = layeredFind(endpoint, cmd, obj, 'args') or {}

      #start with the pre-hooks...

      #eaiArgsList will eventually become the getargs or postargs to send as part of the REST call

      prehooks = layeredFind(endpoint, cmd, obj, 'prehooks') or []

      for ph in prehooks:
         rcHooks.__dict__[ph](cmd, obj, argList)

      eaiArgsList = rcHooks.map_args_cli_2_eai(args, {}, argList)

      logger.debug('after prehooks, eaiArgsList: %s' % str(eaiArgsList))


      #first check if the eai_id needs to be obtained by another request!!!
      if isinstance(lf_eai_id, dict):
         #oh crappp...
         eai_id_uri = buildEndpoint(lf_eai_id['uri'], entityName='', namespace=namespace, owner=owner, search=search, count=count, offset=offset, sort_key=sort_key, sort_dir=sort_dir)
         eai_id_method = GLOBAL_ACTIONS['%s' % lf_eai_id['type']]

         try:
            eai_id_serverResponse, eai_id_serverContent = simpleRequest(eai_id_uri, sessionKey=sessionKey, getargs='', postargs='', method=eai_id_method)
         except Exception as e:
            logger.debug('Could not construct eai_id: %s, %s' % str(lf_eai_id), str(e))
            raise CliArgError('Could not construct eai_id')

         #check the returned status code if it is ok
         try: 
            checkStatus(type=lf_eai_id['type'], serverResponse=eai_id_serverResponse)
         except Exception as e:
            logger.debug('Could not construct eai_id: %s, %s' % (str(lf_eai_id), str(e)))
            raise CliArgError('Could not construct eai_id')

         eai_id = splunk.rcDisplay.extractLevel1Feed(serverContent=eai_id_serverContent, filter=[lf_eai_id['filter']])

      #this essentially means %(name)s % argList i.e the contents of key 'name' in dict argList
      elif lf_eai_id:
         try:
            eai_id_tmp = '%s' % lf_eai_id
            eai_id = eai_id_tmp % argList
            #hack for auth-method ldap, allowing users to type lower case as well
            if eai_id == 'ldap' and obj == 'auth-method':
               eai_id = 'LDAP'
         except:
            eai_id = lf_eai_id
      else:
         eai_id = ''

      try:
         uri_tmp = '%s' % uri
         uri = uri_tmp % argList
      except:
         pass

      logger.debug('Before buildEndpoint uri: %s' % uri)
      logger.debug('Before buildEndpoint entityName: %s' % eai_id)

      uri = buildEndpoint(uri, entityName=eai_id, namespace=namespace, owner=owner, search=search, count=count, offset=offset, sort_key=sort_key, sort_dir=sort_dir)
      logger.debug('uri: %s' % uri)

      etype = layeredFind(endpoint, cmd, obj, 'type')
      if not etype:
         try:
            etype = GLOBAL_DEFAULTS[cmd]
         except KeyError:
            raise NoEndpointError('No endpoint with cmd: %s, obj: %s' % (cmd, obj))
         logger.debug('Using default value of type: %s' % etype)

      method = GLOBAL_ACTIONS['%s' % etype]

      logger.debug('eaiArgsList: %s', eaiArgsList)

      postargs = getargs = {}
      if method == 'POST':
         postargs = copy.deepcopy(eaiArgsList)
      elif method == 'GET':
         getargs = copy.deepcopy(eaiArgsList)
         #hack for list monitor cmd, to allow it to show internal log files as well...
         if cmd == 'list' and obj in ['monitor', 'tail'] and 'show-hidden' in eaiArgsList:
            getargs.pop('show-hidden')

      #if the postargs/getargs contain any parameter that was used to build the uri, pop them out as they do not need to be sent 
      if not isinstance(lf_eai_id, dict):
         sanitizeArgs(lf_eai_id, args, postargs)
         sanitizeArgs(lf_eai_id, args, getargs)
         sanitizeArgs(uri_copy, args, postargs)
         sanitizeArgs(uri_copy, args, getargs)

      logger.debug('postargs: %s', postargs)
      logger.debug('getargs: %s', getargs)

      try:
         serverResponse, serverContent = simpleRequest(uri, sessionKey=sessionKey, getargs=getargs, postargs=postargs, method=method, timeout=timeout, token=token)
      except splunk.ResourceNotFound as e:
         #will reach here if we try to POST to a non existent url. eg. edit a non-existent monitor, show a non-existent config etc
         splunk.rcDisplay.displayResourceError(cmd=cmd, obj=obj, uri=uri, serverContent=e)
         return 
      except Exception as e:
         raise

      #check the returned status code if it is ok
      try:
         checkStatus(type=etype, serverResponse=serverResponse)
      except InvalidStatusCodeError as e:
         raise
   
      #Call the appropriate display function...
      try:
         DISPLAY_CHARS[endpoint](cmd=cmd, obj=obj, type=etype, serverResponse=serverResponse, serverContent=serverContent, sessionKey=sessionKey, eaiArgsList=eaiArgsList)
      except KeyError as e:
         logger.debug('endpoint: %s' % endpoint)
         logger.debug(str(e))
         raise
   
# --------------------------
# --------------------------
if __name__ == '__main__':
    
   # -----------------------------------------
   class LayeredFindTests(unittest.TestCase):
      """
      tests cases for the layeredFind function
      """

      # ---------------------------
      def testLayeredFind1(self):
         """
         check if the uri for the login endpoint is extracted correctly
         """
         self.assertEqual(layeredFind('login', 'login', '', 'uri'), '/auth/login/') 

   # -------------------------------------------
   class MakeRestCallTests(unittest.TestCase):
      """
      tests cases for the makeRestCall function
      """

      # ---------------
      def setUp(self):
         """
         init stuff like getting the session key for requests
         """
         self.sessionKey = auth.getSessionKey(username='admin', password='changeme')
      
      # ---------------------------------------
      def testMakeRestCall_no_endpoint(self):
         """
         this endpoint better not exist
         """
         self.assertRaises(NoEndpointError, makeRestCall, cmd='test', obj='testing', restArgList={}, sessionKey=self.sessionKey)
         
      # --------------------------------------
      def testMakeRestCall_show_config(self):
         """
         show config inputs
         """
         retVal = makeRestCall(cmd='show', obj='config', restArgList={'name':'inputs'}, sessionKey=self.sessionKey)      
         self.assertTrue(retVal != '')

      # ---------------------------------------
      def xtestMakeRestCall_show_license(self):
         """
         show license
         THIS HAS BEEN COMMENTED OUT AS THE '/license' ENDPOINT NO LONGER EXISTS - SPL-34139
         THIS COMMAND HAS NOW BEEN DEPRECATED
         THE NEW COMMAND IS 'list license'. THE CODE/UNIT TESTS HAVE BEEN MOVED TO C-LAND
         SEE 'list license' INSTEAD
         """
         retVal = makeRestCall(cmd='show', obj='license', restArgList={}, sessionKey=self.sessionKey)
         self.assertTrue(retVal != '')

      # -------------------------------------------------
      def testMakeRestCall_show_default_hostname(self):
         """ 
         show default-hostname
         """
         retVal = makeRestCall(cmd='show', obj='default-hostname', restArgList={}, sessionKey=self.sessionKey)
         self.assertTrue(retVal != '')

      # ----------------------------------------------
      def testMakeRestCall_show_datastore_dir(self):
         """
         show datastore-dir
         """
         retVal = makeRestCall(cmd='show', obj='datastore-dir', restArgList={}, sessionKey=self.sessionKey)
         self.assertTrue(retVal != '')

   suite1 = unittest.TestLoader().loadTestsFromTestCase(LayeredFindTests)
   suite2 = unittest.TestLoader().loadTestsFromTestCase(MakeRestCallTests)
   
   alltests = unittest.TestSuite([suite1, suite2])
   unittest.TextTestRunner(verbosity=2).run(alltests)
