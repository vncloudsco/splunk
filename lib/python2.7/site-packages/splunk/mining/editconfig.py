from __future__ import absolute_import
from __future__ import print_function
from builtins import range
from functools import cmp_to_key
import logging
import re
import sys
import time
import tempfile
import os
import difflib

import splunk.auth
import splunk.bundle as bundle
import splunk.mining.conf as conf
import splunk.mining.interactiveutils as interactiveutils


logger = logging.getLogger('splunk.editconfig')

INTERNAL_ATTRIBUTE = '_BOOKKEEPING'
HEADER = """
# ----------------------------------------------------------
# You are now editing your Splunk configuration.
# When you are done, save this file and exit the editor.
#
# * DO NOT REMOVE OR CHANGE ANY OF THE "%s" FIELDS.
#
# * When adding a new stanza, however, copy the "%s" field from a 
#   related object and put it on your new object so that it will be 
#   saved to the correct place.
#
# ----------------------------------------------------------
# DEFAULT VALUES
# ----------------------------------------------------------
""" % (INTERNAL_ATTRIBUTE, INTERNAL_ATTRIBUTE)




def delete(filenames, apps, kvs, tags):
    exit("Delete is not implemented. Exiting...")


def match(mystanzaName, stanza, kvs, tags, options):
    # if we're not showing disabled stanzas, and this stanza is disabled, it didn't match!
    if 'showdisabled' not in options and (stanza.get('disabled', 'false').lower()) == "true":
      return False


    print("%s namespace: %s" % (stanza.name, stanza.confRef.namespace))

    mykvs = dict(kvs)
    seenTags = set()
    # find matching k=v's and tags
    for k, v in stanza.items():
        if k in mykvs:
            if v != kvs[k]: # different value
                return False
            del mykvs[k]
        for tag in tags:
            if tag in k or tag in v:
                seenTags.add(tag)
    # find tags in stanzaname
    for tag in tags:
        if tag in mystanzaName:
            seenTags.add(tag)
                
    # we had some k=v's that didn't match, or not all tags were seen    
    if len(mykvs) > 0 or tags != seenTags:
        return False
    return True

    
def getMatchingStanzas(filenames, apps, kvs, tags, options):
    stanzas = {}
    defaultstanza = None
    owner = splunk.auth.getCurrentUser()['name']
    print("Owner: %s" % owner)
    # for each config file type 
    for filename in filenames:
        # for each app
        for app in apps:
            if app == "*" or app == '-':
                app = None
            # get stanzas
            try:
                mystanzas = bundle.getConf(filename, None, app) #, owner)
            except:
                exit("Unable to get configuration for '%s' for the '%s' application. Exiting..." % (filename, app))

            defaultstanza = mystanzas['default']
            # for each stanza
            for mystanzaName in mystanzas:
                if mystanzaName == 'default':
                    continue
                thisstanza = mystanzas[mystanzaName]
                # if it matches the kvs and tag requirements
                if match(mystanzaName, thisstanza, kvs, tags, options):
                    # use a dict rather than actual stanza object, which writes to disk at every change!
                    mystanza = {}
                    for k, v in thisstanza.items():
                        # only specify values that are not on default stanza
                        if k not in defaultstanza or v != defaultstanza[k]:
                            mystanza[k] = v
                    # add on internal bookkeeping attributes so we know where to write the changes back out to
                    # store stanzaname incase the user changes the stanza name
                    mystanza[INTERNAL_ATTRIBUTE] = '"%s" "%s" "%s"' % (filename, app, mystanzaName) 
                    stanzas[mystanzaName] = mystanza
    return stanzas, defaultstanza

def parseInternalValues(val):
    return re.findall('"(.+?)"', val)

def namesort(x, y):
    if x.startswith('_'):
        return 1
    if y.startswith('_'):
        return -1
    return x <= y

def writeOutTempFile(defaultstanza, stanzas):    
    # get temp file
    tmpfilename = tempfile.mkstemp(suffix='.txt', prefix='splunk-config-', dir=None, text=True)[1]
    f = open(tmpfilename, "a")
    # write out standard header text
    f.write(HEADER)
    # write out default values as comments at the top of the file
    for k, v in defaultstanza.items():
        f.write("# %s = %s\n" % (k, v))
    f.write("\n")

    # write out stanzas
    for stanzaname, stanza in stanzas.items():
        f.write("[%s]\n" % stanzaname)
        keys = list(stanza.keys())
        keys.sort(key=cmp_to_key(namesort))
        
        for k in keys:
            f.write("%s = %s\n" % (k, stanza[k]))
        f.write("\n\n")
    f.close()
    return tmpfilename

def doEdit(tmpfilename):

    # get editor
    editor = os.getenv('SPLUNK_EDITOR')
    if editor == None:
        editor = 'vi'
        print("SPLUNK_EDITOR not defined.  Defaulting to 'vi' for all your hipsters")
        time.sleep(1) # give hipsters time to read

    stanzas = {}
    while (True):
        # user is now editing config
        os.system("%s %s" % (editor, tmpfilename))
        errors = []
        # read the edited config back in 
        stanzas = conf.ConfParser.parse(tmpfilename, True, errors)

        # validate bookkeeping attribute on each stanza
        for name, stanza in stanzas.items():
            if name.lower()!="default" and INTERNAL_ATTRIBUTE not in stanza:
                errors.append("%s attribute not seen on %s stanza." % (INTERNAL_ATTRIBUTE, name))
        
        if len(errors) == 0:
            break
        print("")
        print("-"*80)
        for error in errors:
            print(error.title())
        answer = interactiveutils.askMultipleChoiceQuestion("Fix errors encountered?", ["fix", "abort"], defaultanswer="fix")
        if answer == "abort":
            exit("Aborting...")
        print("\nRe-editing...")
        time.sleep(1)
    return stanzas

def getConfStanzas(stanza):
    mystanzas = None
    try:
        filename, app, origstanzaname = parseInternalValues(stanza[INTERNAL_ATTRIBUTE])
        if app == "None":
            app = None
        mystanzas = bundle.getConf(filename, None, app)

    except Exception as e:
        print("Unable to get stanzas because %s" % e)
    return mystanzas

def addStanza(stanzaname, stanza):
    print("Adding new %s stanza..." % stanzaname)
    try:
        mystanzas = getConfStanzas(stanza)
        mystanzas.createStanza(stanzaname)
        updateStanza(stanzaname, stanza)
    except Exception as e:
        print("Unable to add stanza because %s" % e)

def renameStanza(origstanzaname, stanzaname, stanza):
    print("Renaming %s to %s. also need to update stanza definition" % (origstanzaname, stanzaname))
    try:
        deleteStanza(origstanzaname, stanza)
        addStanza(stanzaname, stanza)
    except Exception as e:
        print("Unable to rename and update stanza because %s" % e)

def updateStanza(stanzaname, stanza, oldstanza=None):
    print("Updating %s stanza..." % stanzaname)
    try:
        mystanzas = getConfStanzas(stanza)
        defaultstanza = mystanzas['default']        
        mystanzas.beginBatch()
        if oldstanza:
            deleteStanza(stanzaname, oldstanza, False)
        updatee = mystanzas[stanzaname]
        # for each attribute on conf on disk that user deleted, set to default value
        for k, v in updatee.items():
            if k in defaultstanza:
                updatee[k] = defaultstanza[k]                
            else: # if no default value, set to empty.  not perfect. but here's not delete functionality
                updatee[k] = ""

        for k, v in stanza.items():
            if k != INTERNAL_ATTRIBUTE:
                updatee[k] = v
        
        mystanzas.commitBatch()

    except Exception as e:
        print("Unable to update stanza because %s" % e)
        
def deleteStanza(stanzaname, stanza, disable=True):
    print("Deleting %s stanza..." % stanzaname)
    try:
        mystanzas = getConfStanzas(stanza)
        defaultstanza = mystanzas['default']
        # ack! we can't really delete stanzas, because they can live all over the place.
        
        mystanzas.beginBatch()
        doomed = mystanzas[stanzaname]        
        # set all value that are different than the default, to the default...
        for k in doomed:
            if k in defaultstanza and doomed[k] != defaultstanza[k]: 
                doomed[k] = defaultstanza[k]
        # disable stanza...
        if disable:
            doomed["disabled"] = "true"
        mystanzas.commitBatch()        
    except Exception as e:
        print("Unable to delete stanza because %s" % e)
        

    
   
def edit(filenames, apps, kvs, tags, options):
    # get stanzas
    oldStanzas, defaultstanza = getMatchingStanzas(filenames, apps, kvs, tags, options)
    tmpfilename = writeOutTempFile(defaultstanza, oldStanzas)

    editedStanzas = doEdit(tmpfilename)

    oldStanzaNamesSeen = set(editedStanzas.keys())
    for stanzaname, stanza in editedStanzas.items():
        # skip default stanz
        if stanzaname == "default":
            continue

        # if no change, skip
        if stanzaname in oldStanzas and stanza == oldStanzas[stanzaname]:
            if len(stanzaname) > 40:
                stanzaname = stanzaname[:40] + "..."
            print("%s is the same" % stanzaname)
            continue
        
        if INTERNAL_ATTRIBUTE in stanza:
            filename, app, origstanzaname = parseInternalValues(stanza[INTERNAL_ATTRIBUTE])
        # a new stanza name.  is it an additional stanza, or a rename?
        if stanzaname not in oldStanzas:
            if INTERNAL_ATTRIBUTE not in stanza:
                addStanza(stanzaname, stanza)
            else:
                oldStanzaNamesSeen.add(origstanzaname)
                renameStanza(origstanzaname, stanzaname, stanza)
            continue
        # existing stanza that is missing it's internal data. bad user, bad!
        if INTERNAL_ATTRIBUTE not in stanza:
            print("%s attribute not seen on %s stanza. Ignoring change on this stanza" % (INTERNAL_ATTRIBUTE, stanzaname))
            continue
        updateStanza(stanzaname, stanza, oldStanzas[stanzaname])

    oldstanzas = set(oldStanzas.keys())
    deletedStanzas = oldstanzas.symmetric_difference(oldStanzaNamesSeen).intersection(oldstanzas)    
    for deletedStanza in deletedStanzas:
        deleteStanza(deletedStanza, oldStanzas[deletedStanza])


def checkFiles(confFiles):
    for conf in confFiles:
        if conf not in PUBLIC_CONFS:
            sys.stdout.write("Unknown config '%s'." % conf)
            filematches = difflib.get_close_matches(conf, PUBLIC_CONFS, cutoff=0.7)
            if len(filematches) > 0:
                print("Perhaps you meant %s." % ", ".join(filematches))
            print("")
            return False
    return True






PUBLIC_CONFS = ['alert_actions', 'app', 'authentication', 'authorize', 'commands', 'crawl', 'datatypesbnf', 'decorations', 'default-mode', 'deployed-fwd-mode', 'deployment', 'distsearch', 'eaitest', 'event_renderers', 'eventdiscoverer', 'eventtypes', 'field_actions', 'fields', 'indexes', 'inputs', 'ldap', 'limits', 'literals', 'macros', 'nodegraph', 'outputs', 'prefs', 'props', 'restmap', 'savedsearches', 'searchbnf', 'segmenters', 'server', 'source-classifier', 'sourcetypes', 'splunk-launch', 'streams', 'tags', 'tenants', 'times', 'transactiontypes', 'transforms', 'user-prefs', 'user-seed', 'viewstates', 'web']


files = []
def main():
    global files
    
    try:
        sessionKey = splunk.auth.getSessionKey('admin', 'changeme')
    except Exception as e:
        exit("Unable to log into splunk. Exiting...")
    argc = len(sys.argv)
    if argc < 3:
        print("\nAt least one configuration file must be specified: %s\n" % ", ".join(PUBLIC_CONFS))
        printUsage()
        exit(1)
    if argc > 2:
        apps = ['*']
        tags = set()
        kvs = {}
        options = set()
        command = sys.argv[1].lower()        
        if command not in ["edit"]: # possibly support more commands in future
            printUsage()
            exit(1)
        files = sys.argv[2].split(",")

        if not checkFiles(files):
            exit(1)
        
        if argc > 3:
            apps = sys.argv[3].split(",")
        if argc > 4:
            for i in range(4, argc):
                val = sys.argv[i]
                if val.startswith("--"):
                    options.add(val[2:])
                elif '=' in val:
                    k, v = val.split('=', 1)
                    kvs[k] = v
                else:
                    tags.add(val)
        if command == "edit":
            edit(files, apps, kvs, tags, options)
        else:
            print("not supported")
    else:                
        printUsage()

def printUsage():
    print('Usage:    <invokation> edit (file,...) [app,...| - ] [tag|attr=val]* [--showdisabled]')
    print('')
    print('Examples:')
    print('              edit props                              -- edit all props.conf')
    print('              edit props -                            -- edit all props.conf ("-" matches all apps)')
    print('              edit props search,unix                  -- edit all props.conf in the search and unix apps')
    print('              edit props - CHARSET=UTF-8 error      -- edit all props an any app where the stanza has CHARSET=UTF-8')

    

if __name__ == '__main__':
    main()
