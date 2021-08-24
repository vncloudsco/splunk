from __future__ import absolute_import
#   Version 4.0
import logging as logger
import copy

import splunk.clilib.cli_common as comm
from splunk.clilib.control_exceptions import ArgError

import splunk.clilib._internal as _internal
import splunk.clilib.info_gather as info_gather

import splunk.clilib.apps as apps
import splunk.clilib.bundle as bundle
import splunk.clilib.bundle_paths as bundle_paths
import splunk.clilib.deploy as deploy
import splunk.clilib.exports as exports
import splunk.clilib.index as index
import splunk.clilib.migration as migration
import splunk.clilib.module as module
import splunk.clilib.manage_search as ms
import splunk.clilib.clilib_tst_artifact as test
import splunk.clilib.train as train
import splunk.clilib.i18n as i18n

def newFunc(func):
  def wrapperFunc(args, fromCLI = False):
    if not isinstance(args, dict):
      raise ArgError("Parameter 'args' should be a dict (was %s)." % type(args))
    dictCopy = copy.deepcopy(args)
    return func(dictCopy, fromCLI)
  return wrapperFunc


#### ----- MANAGE_SEARCH -----
getUIVersion = newFunc(ms.getUIVersion)
setUIVersion = newFunc(ms.setUIVersion)
get_servername = newFunc(ms.getInstanceName)
setServerName = newFunc(ms.setInstanceName)

### ----- TEST -----

testDates  = newFunc(test.testDates)
testFields = newFunc(test.testFields)
testStypes = newFunc(test.testSourcetypes)

### ----- TRAIN -----

trainDates  = newFunc(train.trainDates)
trainFields = newFunc(train.trainFields)


### ----- INDEXES -----

get_defIndex = newFunc(index.getDef)
set_defIndex = newFunc(index.setDef)

### ----- DEPLOYMENT CLIENT SETTINGS -----

deplClient_disable = newFunc(module.deplClientDisable)
deplClient_enable = newFunc(module.deplClientEnable)
deplClient_status = newFunc(module.deplClientStatus)
deplClient_edit = newFunc(deploy.editClient)
get_depPoll = newFunc(deploy.getPoll)
set_depPoll = newFunc(deploy.setPoll)

### ----- BUNDLE MANAGEMENT -----

bundle_migrate = newFunc(bundle_paths.migrate_bundles)

### ----- DIRECT CONFIG INTERACTION -----

showConfig = newFunc(bundle.showConfig)

### ----- EXPORTING DATA ----- # the rest of export & import should be here too.. TODO

export_eventdata = newFunc(exports.exEvents)

### ----- INTERNAL SETTINGS -----

def set_uri(uri, fromCLI = False):
  comm.setURI(uri)


### ----- MIGRATION -----
mig_winSavedSearch = newFunc(migration.migWinSavedSearches)


### ----- SOME LOCAL FILESYSTEM FUNCTIONS -----
local_moduleStatus  = newFunc(module.localModuleStatus)
local_moduleEnable  = newFunc(module.localModuleEnable)
local_moduleDisable = newFunc(module.localModuleDisable)
local_appStatus     = newFunc(apps.localAppStatus)
local_appEnable     = newFunc(apps.localAppEnable)
local_appDisable    = newFunc(apps.localAppDisable)


### ----- I18N -----
i18n_extract = newFunc(i18n.i18n_extract)

### ----- OTHER INTERNALISH STUFF -----

checkXmlFiles   = newFunc(_internal.checkXmlFiles)
firstTimeRun    = newFunc(_internal.firstTimeRun)
preFlightChecks = newFunc(_internal.preFlightChecks)
diagnose        = newFunc(info_gather.pclMain)
