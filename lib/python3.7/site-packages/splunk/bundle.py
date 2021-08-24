from __future__ import absolute_import
# /////////////////////////////////////////////////////////////////////////////
#  Bundle property O-R mapping classes
#  see Conf() docstring
# /////////////////////////////////////////////////////////////////////////////

import splunk
import splunk.auth as auth
import splunk.entity as entity
import splunk.rest as rest
import splunk.util as util
import logging

logger = logging.getLogger('splunk.bundle')

def getConf(confName, sessionKey=None, namespace=None, owner=None, overwriteStanzas=False, hostPath=None):
    '''
    Parses a logical bundle file and returns a Conf() object

    If namespace=None, then the behavior is 3.2-style, where all writes are 
    done to conf files in etc/system/local.  All reads will merge every conf
    file that is accessible in etc/system and etc/apps/*.  If a namespace is 
    provided, then writes are done in etc/apps/<namespace>/local/, and reads 
    are restricted to values in etc/apps/<namespace>/(default|local).  If
    overwriteStanzas is true, old keys in edited stanzas will not be preserved.

    For the 3.2-style reading, the endpoint uses the following priority:
        system/local
        apps/<namespace>/local
        apps/<namespace>/default
        system/default
    '''

    # fallback to current user
    if not owner:
        owner = auth.getCurrentUser()['name']
    
    uri = entity.buildEndpoint(entityClass='properties', entityName=confName, namespace=namespace, 
                               owner=owner, hostPath=hostPath)
    
    # the fillcontents arg will push all stanza keys down in 1 request instead
    # of iterating over all stanzas
    serverResponse, serverContent = rest.simpleRequest(uri, getargs={'fillcontents':1}, sessionKey=sessionKey)
    
    if serverResponse.status != 200:
        logger.info('getConf - server returned status=%s when asked for conf=%s' % (serverResponse.status, confName))
        
    # convert the atom feed into dict
    confFeed = rest.format.parseFeedDocument(serverContent)
    stanzas = confFeed.toPrimitive()
    
    # create Conf/Stanzas
    output = Conf(confName, namespace=namespace, owner=owner, overwriteStanzas=overwriteStanzas)
    output.sessionKey = sessionKey
    output.isImportMode = True
    for name in stanzas:
        stanza = output.createStanza(name)
        stanza.needsPopulation = False
        for k in stanzas[name]:
            if stanzas[name][k] == None:
                stanza[k] = ''
            else:
                stanza[k] = stanzas[name][k]
        
    output.isImportMode = False

    return output

def createConf(confName, namespace=None, owner=None, sessionKey=None, hostPath=None):
    '''
    Creates a new conf file.  Returns a conf instance of the newly created
    .conf file.
    '''
    
    uri = entity.buildEndpoint('properties', namespace=namespace, owner=owner, hostPath=hostPath)
    postargs = {'__conf': confName}
    
    status, response = rest.simpleRequest(uri, postargs=postargs, sessionKey=sessionKey, raiseAllErrors=True)
    
    # Expect 201 on creation or 200 on preexisting file (automatic handling of 303 redirect).
    if not ((status.status == 201) or (status.previous is not None and status.status == 200)):
        logger.error('createConf - unexpected server response while creating conf file "%s"; HTTP=%s' % (confName, status.status))
    
    return getConf(confName, namespace=namespace, owner=owner, sessionKey=sessionKey, hostPath=hostPath)

class Conf(util.OrderedDict):
    '''
    Represents a logical .conf group, and provides read/write services to the
    bundle system in splunkd.

    Conf is a direct O-R mapping to the CLI property system, and is able to 
    interact with the individual stanzas and properties on a real-time or 
    deferred basis. The attribute hierarchy matches that of:

        <conf_object>[<stanza_name>][<key_name>]

    Getting and setting stanzas or key/value pairs is the same as any python
    dictionary:

        myConf = getConf('prefs', mysessionKey)

        # get the 'default' stanza in the 'prefs' conf file
        s = myConf['default'] 

        # get the 'color' property in the 'default' stanza of the 'prefs' conf
        color = myConf['default']['color']

        # set the 'color' property in the 'default' stanza of the 'prefs' conf
        # this is an immediate write
        myConf['default']['color'] = 'green'

    If you are doing a large number of writes, you can defer the commit action
    as follows:

        myConf.beginBatch()
        myConf['default']['car1'] = 'honda'
        myConf['default']['car2'] = 'bmw'
        myConf['default']['car3'] = 'lexus'
        myConf['default']['car4'] = 'pinto'
        myConf['default']['car5'] = 'VW'
        myConf.commitBatch()

    '''

    def __init__(self, name, namespace=None, owner=None, overwriteStanzas=False):
        # amrit moved creation of "stanzas" to before calling __init__ from parent
        # (OrderedDict) to avoid a circular init we were seeing. OrderedDict.__init__
        # was calling our __getitem__, resulting in trying to iterate a self.stanzas
        # that had not been defined yet! No idea why this started showing up only
        # during our Python 3 migration, but here we are.
        self.stanzas = StanzaCollection()
        super(Conf, self).__init__(self)
        self.name = name
        self.namespace = namespace
        self.owner = owner
        self.sessionKey = None
        self.queue = []
        self.isAtomic = False
        self.isImportMode = False
        self.overwriteStanzas = overwriteStanzas


    def findStanzas(self, match = '*'):
        '''
        Returns a list of all the stanzas that match a given string. Simple
        wildcard is allowed at the beginning and end of the match string.
        '''

        output = StanzaCollection()
        
        if match == '*':
            output.update(self.stanzas)
        elif match.startswith('*'):
            found = [(x, self.stanzas[x]) for x in self.stanzas if x.endswith(match[1:])]
            output.update(dict(found))
        elif match.endswith('*'):
            found = [(x, self.stanzas[x]) for x in self.stanzas if x.startswith(match[0:-1])]
            output.update(dict(found))
        else:
            found = [(x, self.stanzas[x]) for x in self.stanzas if x == match]
            output.update(dict(found))
            
        return output
        

    def findKeys(self, match = '*'):
        '''
        Returns a dictionary of keys from all stanzas that match the input
        string.  Simple wildcard is allowed at the end of the match string.
        '''

        output = {}
        for stanzaName in self.stanzas:
            output.update(self.stanzas[stanzaName].findKeys(match))
        return output


    def beginBatch(self):
        '''
        Defers all subsequent calls to set attribute values until the
        commitBatch() method is called. If commitBatch() is not
        called, the Python representation will become out of sync until
        the Conf() object is refreshed.
        '''

        self.isAtomic = True


    def commitBatch(self, sessionKey = None):
        '''
        Commits all edits to the bundle since a beginBatch() call.
        Returns false if beginBatch() was not called; true otherwise.
        '''

        if not self.isAtomic or len(self.queue) == 0: return False

        if sessionKey: self.sessionKey = sessionKey

        batchKeys = {}
        stanza = ''
        while len(self.queue):
            item = self.queue.pop(0)
            if stanza and item['stanza'] != stanza:
                self._executeBatch(stanza, batchKeys)
                batchKeys = {}
            stanza = item['stanza']
            batchKeys[item['key']] = item['value']

        self._executeBatch(stanza, batchKeys)

        self.isAtomic = False
        return True


    def createStanza(self, name = 'default'):
        '''
        Initializes a new Stanza object in the current Conf object and 
        assigns a name.
        '''

        if self.isImportMode: needsPopulation = True
        else: needsPopulation = False

        self.stanzas[name] = Stanza(self, name, needsPopulation)
        return self.stanzas[name]


    def _setKeyValue(self, stanza, key, value):
        args = {'stanza': stanza, 'key': key, 'value': value}
        if not self.isAtomic:
            self._executeSingle(**args)
        else:
            self.queue.append(args)
            #print('_setKeyValue: QUEUE %s %s=%s' % (stanza, key, value))


    def getEndpointPath(self, conf=None, stanza=None, key=None):
        '''
        Returns the splunkd URI for the specified combination of conf file,
        stanza, and key name.  The namespace and owner context are pulled from
        the current Conf() instance.
        '''
        
        path = [entity.buildEndpoint('properties', namespace=self.namespace, owner=self.owner)]

        parts = []
        if conf: 
            parts.append(conf)
            if stanza:
                parts.append(stanza)
                if key:
                    parts.append(key)
        
        path.extend([util.safeURLQuote(shard, '') for shard in parts])
        
        return '/'.join(path)
        
        
    def _executeSingle(self, stanza, key, value = ''):
        '''
        Commits a write action on a single key/value pair
        '''

        if self.isImportMode: return

        logger.debug('_executeSingle: stanza=%s => %s=%s' % (stanza, key, value))

        # first check if stanza exists; create if necessary
        try:
            uri = self.getEndpointPath(self.name, stanza)
            rest.simpleRequest(uri, sessionKey=self.sessionKey)
            
        except splunk.ResourceNotFound:
            createUri = self.getEndpointPath(self.name)
            serverResponse, serverContent = rest.simpleRequest(
                createUri, 
                self.sessionKey,
                postargs={'__stanza': stanza}
                )
            
        # now write the key
        serverResponse, serverContent = rest.simpleRequest(
            uri,
            self.sessionKey,
            postargs={key: value},
            method=self._getWriteMethod()
            )

        if serverResponse.status != 200:
            logger.error('_executeSingle - HTTP error=%s server returned: %s' % (serverResponse.status, serverContent))
            raise splunk.RESTException(serverResponse.status, '_executeSingle - server returned: %s' % serverContent)


    def _executeBatch(self, stanza, kvPairs):
        if self.isImportMode: return
        logger.debug('_executeBatch: stanza=%s => %s' % (stanza, kvPairs))

        # first check if stanza exists; create if necessary
        try:
            uri = self.getEndpointPath(self.name, stanza)
            rest.simpleRequest(uri, sessionKey=self.sessionKey)
        except splunk.ResourceNotFound:
            createUri = self.getEndpointPath(self.name)
            serverResponse, serverContent = rest.simpleRequest(
                createUri, 
                self.sessionKey,
                postargs={'__stanza': stanza}
                )

        # now write out the keys
        serverResponse, serverContent = rest.simpleRequest(
            uri,
            self.sessionKey,
            postargs=kvPairs,
            method=self._getWriteMethod()
            )
        
        if serverResponse.status != 200:
            logger.error('_executeBatch - HTTP error=%s server returned: %s' % (serverResponse.status, serverContent))
            raise splunk.RESTException(serverResponse.status, '_executeBatch - server returned: %s' % serverContent)

    def _getWriteMethod(self):
        return self.overwriteStanzas and 'PUT' or 'GET'

    def _refreshStanza(self, stanzaName):
        
        uri = self.getEndpointPath(self.name, stanzaName)
        
        serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=self.sessionKey)
        
        #logger.debug('_refreshStanza - got stanza data back')
        keys = rest.format.parseFeedDocument(serverContent)
        keys = keys.toPrimitive()
        #logger.debug('_refreshStanza - parsed stanza data; got %s keys' % len(keys))
        self.isImportMode = True
        for k in keys:
            self.stanzas[stanzaName][k] = keys[k]
        self.isImportMode = False
            

    def __getitem__(self, key):
        if key not in self.stanzas:
            self.createStanza(key)
            
        if self.stanzas[key].needsPopulation:
            logger.debug('stanza=%s needs loading...' % key)
            self._refreshStanza(key)
            self.stanzas[key].needsPopulation = False
            
        return self.stanzas[key]
        
    def __setitem__(self, key, value):
        raise NotImplementedError('Direct attribute setting is not allowed. Use the createStanza() method instead.')
    def __iter__(self):
        return self.stanzas.__iter__()
    def __len__(self):
        return self.stanzas.__len__()
    def __str__(self):
        return self.stanzas.__str__()
    def __repr__(self):
        o = [x for x in self.stanzas]
        return o.__repr__()
    def __contains__(self, key):
        return self.stanzas.__contains__(key)
    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
    def keys(self):
        try:
            return list(self.stanzas.keys())
        except AttributeError:
            return dict().keys()
            
        



class StanzaCollection(util.OrderedDict):
    '''
    Represents a collection of stanzas.
    '''
    
    def __init__(self, *args, **kwds):
        super(StanzaCollection, self).__init__(self, *args, **kwds)


    def getMerged(self):
        '''
        Returns a single stanza with all the keys merged according to the 
        bundle merge rules
        '''
        
        namelist = sorted(self.keys())
        namelist.reverse()
        
        output = Stanza()
        for name in namelist:
            output.update(self[name])
            
        return output
        
        
        
class Stanza(util.OrderedDict):
    '''
    Represents a stanza block, as defined by the bundle system.  Contains a 
    dictionary of key/value pairs.
    '''

    def findKeys(self, match = '*'):
        '''
        Returns a dictionary of keys from the curren stanza that match the input
        string.  Simple wildcard is allowed at the end of the match string.
        '''

        if match == '*' or not match:
            return dict(self)
        elif match.endswith('*'):
            o = [(x, self[x]) for x in self if x.startswith(match[0:-1])]
        else:
            o = [(x, self[x]) for x in self if x == match]

        return dict(o)

    def isDisabled(self):
        try:
            val = self["disabled"]
            return (val == "true")
        except:
            return False

    def __init__(self, confRef = None, name = '', needsPopulation=False):
        super(Stanza, self).__init__(self)
        self.confRef = confRef
        self.name = name
        self.needsPopulation = needsPopulation

    def __setitem__(self, key, value):
        if self.confRef:
            self.confRef._setKeyValue(self.name, key, value)
        super(Stanza, self).__setitem__(key, value)

    def __delitem__(self, key):
        raise NotImplementedError('Attribute deletion is not supported. Use an empty value instead.')

    def __str__(self):
        return 'Stanza [%s] %s' % (self.name, super(Stanza, self).__str__())


# tests
if __name__ == '__main__':
    
    import unittest
    import time
    
    #logging.basicConfig(level=logging.DEBUG)

    class MainTest(unittest.TestCase):

        def setUp(self):
            self.sessionKey = auth.getSessionKey('admin', 'changeme')
            
        def test1_SingleWrites(self):
            
            bun = getConf('web', sessionKey=self.sessionKey)
            bun['delete_me_1']['test_key1'] = 'single write 1'
            bun['delete_me_1']['test_key2'] = 'single write 2'
            
            verify = getConf('web', sessionKey=self.sessionKey)
            
            self.assertEqual(verify['delete_me_1']['test_key1'], 'single write 1')
            self.assertEqual(verify['delete_me_1']['test_key2'], 'single write 2')
            
            
        def test2_BatchWrites(self):
    
            bun = getConf('web', sessionKey=self.sessionKey)

            bun.beginBatch()
            bun['delete_me_1']['test_key1'] = 'batch write 1'
            bun['delete_me_1']['test_key3'] = 'batch write 2'
            bun['delete me 2']['test_key4'] = 'batch write 3'
            bun['delete me 2']['test_key5'] = 'batch write 4'
            bun.commitBatch()
            
            verify = getConf('web', sessionKey=self.sessionKey)
            self.assertEqual(verify['delete_me_1']['test_key1'], 'batch write 1')
            self.assertEqual(verify['delete_me_1']['test_key3'], 'batch write 2')
            self.assertEqual(verify['delete me 2']['test_key4'], 'batch write 3')
            self.assertEqual(verify['delete me 2']['test_key5'], 'batch write 4')
            
            
        def test3_StanzaCollection(self):
            '''
            test the ordered dictionary nature of StanzaCollection
            '''
            
            sc = StanzaCollection()
            
            keys = 'abcdefghijklmnopqrstuvwxyz'
            
            for char in keys:
                sc[char] = 'foo'

            for i, k in enumerate(sc):
                self.assertEquals(k, keys[i])
            

        def test4_NamespaceWrite(self):
            '''
            Check write, and subsequent read of key value sent to the 
            debug namespace
            '''

            # check that namespace is set
            conf = getConf('web', namespace='testing', sessionKey=self.sessionKey)
            self.assertEqual(conf.namespace, 'testing')

            # add value to 'testing' NS only
            conf['delete_me_3']['test_key6'] = 'ns_write_1'
            conf = getConf('web', namespace='testing', sessionKey=self.sessionKey)
            self.assertEqual(conf['delete_me_3']['test_key6'], 'ns_write_1')

            # verify that value is not available in different NS
            conf = getConf('web', namespace='search', sessionKey=self.sessionKey)
            self.assertRaises(KeyError, conf['delete_me_3'].__getitem__, 'test_key6')
            
            # verify presence using legacy non-namespace mode
            #
            # TODO: should this be valid?
            #
            #conf = getConf('web', sessionKey=self.sessionKey)
            #self.assertNotEqual(conf['settings'].get('delete_me_3'), None, 'Failed to find delete_me_3 stanza')


        def test_createConf(self):
            '''
            Check creating new conf file
            '''

            confName = 'testconf_%s' % round(time.time())

            newConf = createConf(confName, namespace="testing", sessionKey=self.sessionKey)
            self.assert_(isinstance(newConf, Conf))
            
            challenge = getConf(confName, namespace="testing", sessionKey=self.sessionKey)
            self.assertEquals(challenge.name, confName)


        def test_findStanzaPrefix(self):
            
            conf = getConf('indexes', namespace='search', sessionKey=self.sessionKey)
            stanzas = conf.findStanzas('_block*')
            
            self.assertEquals(len(stanzas), 1)
            self.assertEquals(list(stanzas.keys())[0], '_blocksignature')


        def test_findStanzaSuffix(self):

            conf = getConf('indexes', namespace='search', sessionKey=self.sessionKey)
            stanzas = conf.findStanzas('*bucket')

            self.assertEquals(len(stanzas), 1)
            self.assertEquals(list(stanzas.keys())[0], '_thefishbucket')

            
        def test_emptyValueWrite(self):
            '''
            setting a new key to an empty value will not get persisted
            '''

            # try write of empty value
            conf = getConf('web', namespace='search', sessionKey=self.sessionKey)
            stanza = conf['test']
            stanza['emptyKey'] = ''

            # confirm empty value
            conf = getConf('web', namespace='search', sessionKey=self.sessionKey)
            stanza = conf['test']
            self.assert_('emptyKey' not in stanza, '"emptyKey" key was written when it was not expected to')
        
        def test_remote_hostpath(self):
            conf = getConf('web', namespace='search', sessionKey=self.sessionKey)
            self.assert_(isinstance(conf, Conf), "The optional argument hostPath works when ignored")
            
            conf = getConf('indexes', namespace='search', sessionKey=self.sessionKey, hostPath=splunk.getLocalServerInfo())
            self.assert_(isinstance(conf, Conf), "The optional argument hostPath works when used")
            
            confName = 'testconf_%s' % round(time.time())
            newConf = createConf(confName, namespace="testing", sessionKey=self.sessionKey, hostPath=splunk.getLocalServerInfo())
            self.assert_(isinstance(newConf, Conf), "The optional argument hostPath works when used in createConf")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(MainTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
