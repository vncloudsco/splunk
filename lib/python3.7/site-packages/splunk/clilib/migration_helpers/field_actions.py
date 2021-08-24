__doc__ = '''
This script migrates the old field actions in 3.x to the new 4.x
field actions. To run against a given conf file:

from splunk.clilib.migration_helpers import field_actions as fa
fa.migrateFieldActions(<path to 3.x file>, <path to 4.x file>)
'''

import os
import errno
import re
from future.moves.urllib import parse as urllib_parse
import logging
from splunk.clilib import cli_common as comm

logger = logging.getLogger('splunk.clilib.migration_helpers.field_actions')

# These are keys that have straight mapping equivalents
mappings = {
    'metaKeys': 'fields',
    'target': 'target',
    'label': 'label'
}

oldVarPattern = re.compile(r'\{\$([\w\s]+)\}')

def migrateFieldActionStanza(stanza):
    '''Given a field action stanza, migrate it to a new field action stanza.'''

    output = {}
    
    if 'label' not in stanza:
        logger.warn('No label is defined in the following field action stanza, so it cannot be transformed  "%s"' % stanza)
        return None

    # Handle the generic mappings
    for key in stanza:
        if key in mappings:
            output[mappings[key]] = stanza[key]
    
    # Build the types
    if 'search' in stanza or 'term' in stanza:
        output.update(buildSearchType(stanza))
        
    elif 'uri' in stanza:
        output.update(buildLinkType(stanza))
    
    # If there is no indicator of what the type should be return None
    else:
        return None
    
    return output

def replaceOldFieldActionVars(string):
    return oldVarPattern.sub(r"$\1$", string)

def buildSearchType(stanza):
    '''Builds a dictionary map representing the search field action.'''
    
    output = {'type': 'search'}
    
    if 'term' in stanza:
        output['search.search_string'] = replaceOldFieldActionVars(stanza['term'])
    elif 'search' in stanza:
        output['search.search_string'] = replaceOldFieldActionVars(stanza['search'])
    
    return output


def buildLinkType(stanza):
    '''Builds a dictionary map representing the link field action.'''
    
    output = {'type': 'link'}
    
    uri = stanza.get('uri')
    output['link.uri'] = replaceOldFieldActionVars(uri)
    
    method = stanza.get('method')
    if method and method.lower() == 'post':
        output['link.method'] = 'post'
        
        payload = stanza.get('payload')
        if payload:
            payload = replaceOldFieldActionVars(payload)
            # The True here retains unset keys in the qs. For example foo=bar&baz=,
            # where baz is retained for explicitness.
            parsed = urllib_parse.parse_qsl(payload, True)
            for i, part in enumerate(parsed):
                key_field = 'link.postargs.%i.key' % (i+1)
                val_field = 'link.postargs.%i.value' % (i+1)
                output[key_field] = part[0]
                output[val_field] = part[1]
                
    return output
    
        
def migrateFieldActions(infile, outfile):
    '''
    The general function that takes an input file path and an output file path
    generates the migration and writes it out.
    
    infile => the file to read in from
    outfile => the file to write out to. 
    '''
    parsed_infile = comm.readConfFile(infile)
    
    output = {}
    for stanza in parsed_infile:
        if "default" == stanza:
            continue
        new_stanza = migrateFieldActionStanza(parsed_infile[stanza])
        if new_stanza != None:
            output[stanza] = new_stanza
    
    outdir = os.path.abspath(os.path.dirname(outfile))
    try:
        os.makedirs(outdir, 0o755)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            logger.warn("Could not create the directory specified in '%s'." % outfile)
            raise

    comm.writeConfFile(outfile, output)
    return
    
def migFieldActions_4_1(infile, outfile, isDryRun=False):
    '''
    THIS FUNCTION SHOULD NOT BE CALLED MANUALLY. IT IS USED BY THE
    MIGRATION SCRIPT.
    '''
    migrateFieldActions(infile, outfile)
    comm.removeItem(infile, isDryRun)

if __name__ == '__main__':


    def run_tests():
        import unittest
        
        TEST_FA_CONF = '''    
        # This example searches an IP on Google:
        [googleExample]
        metaKeys=ip
        uri=http://google.com/search?q={$ip}
        label=Google this ip
        method=GET

        # This example runs a custom search in SplunkWeb:
        [some_custom_search]
        metaKeys = ruser,rhost
        term=authentication failure | filter ruser={$ruser} rhost={$rhost}
        label=Search for other breakin attempts by this user
        alwaysReplace=true

        # This example looks up your event on SplunkBase
        [SplunkBaseLookup]
        metaKeys=_raw, host
        uri=http://apps.splunk.com/
        label=Search SplunkBase
        target=splunkbase
        method=POST
        payload= event={$_raw}&myhost={$host}
        '''
        
        class FieldActionMigrationTest(unittest.TestCase):
            
            def getConf(self):
                lines = TEST_FA_CONF.split('\n')
                return comm.readConfLines(lines)
                
                
            def testLinkGetGeneration(self):
                conf = self.getConf()

                self.assert_('googleExample' in conf, "The googleExample field action should be in the conf.")
                
                output = migrateFieldActionStanza(conf['googleExample'])
                
                expect = {
                    'type': 'link',
                    'fields': 'ip',
                    'link.uri': 'http://google.com/search?q=$ip$',
                    'label': 'Google this ip'
                }
                self.assertEqual(output, expect, 'The field actions should be transformed as expected.')
                
                
            def testLinkPostGeneration(self):
                conf = self.getConf()
                self.assert_('SplunkBaseLookup' in conf, "The SplunkBaseLookup field action should be in the conf.")
                
                output = migrateFieldActionStanza(conf['SplunkBaseLookup'])
                
                expect = {
                    'type': 'link',
                    'fields': '_raw, host',
                    'link.uri': 'http://apps.splunk.com/',
                    'link.method': 'post',
                    'label': 'Search SplunkBase',
                    'target': 'splunkbase',
                    'link.postargs.1.key': 'event',
                    'link.postargs.1.value': '$_raw$',
                    'link.postargs.2.key': 'myhost',
                    'link.postargs.2.value': '$host$'
                }
                self.assertEqual(output, expect, 'The field actions should be transformed as expected.')
                
                
            def testSearchTypeGeneration(self):
                conf = self.getConf()
                self.assert_('some_custom_search' in conf, "The some_custom_search field action should be in the conf.")
                
                output = migrateFieldActionStanza(conf['some_custom_search'])
                
                expect = {
                    'type': 'search',
                    'fields': 'ruser,rhost',
                    'search.search_string': 'authentication failure | filter ruser=$ruser$ rhost=$rhost$',
                    'label': 'Search for other breakin attempts by this user'
                }
                self.assertEqual(output, expect, 'The field actions should be transformed as expected.')

        # run tests
        suite = unittest.TestLoader().loadTestsFromTestCase(FieldActionMigrationTest)
        unittest.TextTestRunner(verbosity=2).run(suite)


    import sys

    if '-t' in sys.argv or '--test' in sys.argv or len(sys.argv) == 1:
        run_tests()

    elif len(sys.argv) >= 3:
        logger.addHandler(logging.StreamHandler())
        migrateFieldActions(sys.argv[1], sys.argv[2])
