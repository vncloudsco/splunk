from __future__ import absolute_import
from builtins import object

import logging
import os
import re
import time
from future.moves.urllib import parse as urllib_parse

import splunk
import splunk.rest as rest
import splunk.util as util
import splunk.util

logger = logging.getLogger('splunk.entity')

#
# Defines the property name to treat as the unique identifier for specific
# classes of entities.  By default, the entity.id = entity.name; some
# entities require that ID != name, so we can reassign that here
#
ENTITY_ID_MAP = {
#    'saved/searches': 'name'
}

# define system owner name for 'all users'
# TODO: change this to '*' when everybody recognizes this
EMPTY_OWNER_NAME = 'nobody'

# List of params always accepted at an entity endpoint
ENTITY_PARAMS = [
    'namespace',
    'owner',
    'search',
    'count',
    'offset',
    'sort_key',
    'sort_dir'
]

# define the reserved entity name for obtaining property scaffolding for a new
# EAI object
NEW_EAI_ENTITY_NAME = '_new'

# define preset key for literal XML data
EAI_DATA_KEY = 'eai:data'


def entityParams(**kw):
    '''Returns a clean dict of valid entity params'''
    resp = {}
    for key in ENTITY_PARAMS:
        if key in kw: resp[key] = kw[key]
    return resp


def quoteEntity(entity_name):
    '''
    This function purposefully double encodes forward slashes '/'.
    This is because many applications that handle http requests assume a %2F
    encoding of a forward slash actually represents a forward slash. Hence,
    splunkd should always receive double encoded forward slashes when they
    are to appear in entity names.

    e.g. "foo/bar" should be "foo%252Fbar".

    Do not erase this or the unquoteEntity method.
    '''
    return util.safeURLQuote(util.toUnicode(entity_name).replace('/', '%2F'))


def unquoteEntity(entity_name):
    '''
    unquoteEntity reverses the intentional double encoding of
    quoteEntity.

    Do not erase this function.
    '''
    return urllib_parse.unquote(entity_name).replace('%2F', '/')


def quotePath(path_segments, delimiter='/'):
    '''
    Given a list of path segments, pass each one through
    quoteEntity and return a entity encoded string delimited
    by the delimiter.
    '''
    return delimiter.join([quoteEntity(entity) for entity in path_segments])


def buildEndpoint(entityClass, entityName=None, namespace=None, owner=None, hostPath=None, **unused):
    '''
    Returns the proper URI endpoint for a given type of entity
    '''

    # set 'all user' name if none passed
    owner = owner or EMPTY_OWNER_NAME

    if isinstance(entityClass, list):
        entityClass = quotePath(entityClass)
    else:
        # We just use safeURLQuote here because calling quoteEntity
        # would escape any forward slashes.
        # e.g. 'saved/searches' would become 'saved%252Fsearches' if
        # quoteEntity was used
        entityClass = util.safeURLQuote(entityClass.strip('/'))

    if namespace:
        uri = '/servicesNS/%s/%s/%s' % (quoteEntity(owner), quoteEntity(namespace), entityClass)
    else:
        uri = '/services/%s' % entityClass

    if entityName:
        uri += '/' + quoteEntity(entityName)

    if hostPath:
        uri = hostPath + uri

    return uri


def getEntities(entityPath, namespace=None, owner=None, search=None, count=None, offset=0, sort_key=None, sort_dir=None , sessionKey=None, uri=None, unique_key='title', hostPath=None, **kwargs):
    '''
    Retrieves generic entities from the Splunkd endpoint, restricted to a namespace and owner context.

    @param entityPath: the class of objects to retrieve
    @param namespace: the namespace within which to look for the entities.  default set by splunk.getDefault('namespace')
    @param owner: the owner within which to look for the entity.  defaults to current user
    @param search: simple key=value filter
    @param offset: the starting index of the first item to return.  defaults to 0
    @param count: the maximum number of entities to return.  defaults to -1 (all)
    @param sort_key: the key to sort against
    @param sort_dir: the direction to sort (asc or desc)
    @param uri: force a specific path to the objects
    @param unique_key: specify the uniquifying key
    '''

    if isinstance(entityPath, list):
        entity_path = quotePath(entityPath)
    else:
        entity_path = entityPath

    if entity_path.startswith('data/props/extractions'):
        kwargs.setdefault('safe_encoding', 1)

    atomFeed = _getEntitiesAtomFeed(entityPath, namespace, owner, search, count, offset, sort_key, sort_dir, sessionKey, uri, hostPath, **kwargs)

    offset = int(atomFeed.os_startIndex or -1)
    totalResults = int(atomFeed.os_totalResults or -1)
    itemsPerPage = int(atomFeed.os_itemsPerPage or -1)

    links = atomFeed.links

    messages = atomFeed.messages

    # preserves order of returned elements
    # EntityCollection is a new subclass or util.OrderedDict, it still preserves
    # the order, but it allows some additional params to be added on.
    collection = EntityCollection(None, search, count, offset, totalResults, itemsPerPage, sort_key, sort_dir, links, messages)

    for atomEntry in atomFeed:
        entity = _getEntityFromAtomEntry(atomEntry, entityPath, namespace, hostPath)

        # use the same semantics as in the C++ code: make the first item in the
        # list win if two stanzas with the same name exist
        attr = getattr(atomEntry, unique_key)
        if attr not in collection:
            collection[attr] = entity

    return collection

def getEntitiesList(entityPath, namespace=None, owner=None, search=None, count=None, offset=0, sort_key=None, sort_dir=None , sessionKey=None, uri=None, hostPath=None, **kwargs):
    '''
    Retrieves generic entities from the Splunkd endpoint, restricted to a namespace and owner context.
    Returns a LIST of entities

    @param entityPath: the class of objects to retrieve
    @param namespace: the namespace within which to look for the entities.  default set by splunk.getDefault('namespace')
    @param owner: the owner within which to look for the entity.  defaults to current user
    @param search: simple key=value filter
    @param offset: the starting index of the first item to return.  defaults to 0
    @param count: the maximum number of entities to return.  defaults to -1 (all)
    @param sort_key: the key to sort against
    @param sort_dir: the direction to sort (asc or desc)
    @param uri: force a specific path to the objects
    @param unique_key: specify the uniquifying key
    '''

    atomFeed = _getEntitiesAtomFeed(entityPath, namespace, owner, search, count, offset, sort_key, sort_dir, sessionKey, uri, hostPath, **kwargs)

    l = []

    for atomEntry in atomFeed:
        entity = _getEntityFromAtomEntry(atomEntry, entityPath, namespace, hostPath)
        l.append(entity)

    return l

def _getEntityFromAtomEntry(atomEntry, entityPath, namespace, hostPath):
    contents = atomEntry.toPrimitive()
    entity = Entity(entityPath, atomEntry.title, contents, namespace)
    entity.owner = atomEntry.author
    entity.createTime = atomEntry.published
    entity.updateTime = atomEntry.updated
    entity.summary = atomEntry.summary
    entity.links = atomEntry.links
    entity.id = atomEntry.id
    entity.hostPath = hostPath

    entity.updateOptionalRequiredFields()

    return entity

def _getEntitiesAtomFeed(entityPath, namespace=None, owner=None, search=None, count=None, offset=0, sort_key=None, sort_dir=None , sessionKey=None, uri=None, hostPath=None, **kwargs):
    import splunk.auth as auth
    # fallback to currently authed user
    if not owner:
        owner = auth.getCurrentUser()['name']

    # construct URI to get entities
    if not uri:
        uri = buildEndpoint(entityPath, namespace=namespace, owner=owner, hostPath=hostPath)

    if search:
        kwargs["search"] = search

    if count != None:
        kwargs["count"] = count

    if offset:
        kwargs["offset"] = offset

    if sort_key:
        kwargs["sort_key"] = sort_key

    if sort_dir:
        kwargs["sort_dir"] = sort_dir

    # fetch list of entities
    serverResponse, serverContent = rest.simpleRequest(uri, getargs=kwargs, sessionKey=sessionKey, raiseAllErrors=True)

    if serverResponse.status != 200:
        raise splunk.RESTException(serverResponse.status, serverResponse.messages)

    atomFeed = rest.format.parseFeedDocument(serverContent)
    return atomFeed

def getEntity(entityPath, entityName, uri=None, namespace=None, owner=None, sessionKey=None, hostPath=None, **kwargs):
    '''
    Retrieves a generic Splunkd entity from the REST endpoint

    @param entityPath: the class of objects to retrieve
    @param entityName: the specific name of the entity to retrieve
    @param namespace: the namespace within which to look for the entities.  if None, then pull from merged
    @param owner: the owner within which to look for the entity.  defaults to current user

    '''
    import splunk.auth as auth

    # get default params
    if not owner: owner = auth.getCurrentUser()['name']

    if not uri:
       if not entityName:
          raise ValueError("entityName cannot be empty")
       uri = buildEndpoint(entityPath, entityName=entityName, namespace=namespace, owner=owner, hostPath=hostPath)

    if isinstance(entityPath, list):
        entity_path = quotePath(entityPath)
    else:
        entity_path = entityPath

    if entity_path.startswith('data/props/extractions'):
        kwargs.setdefault('safe_encoding', 1)

    serverResponse, serverContent = rest.simpleRequest(uri, getargs=kwargs, sessionKey=sessionKey, raiseAllErrors=True)

    if serverResponse.status != 200:
        logger.warn('getEntity - unexpected HTTP status=%s while fetching "%s"' % (serverResponse.status, uri))

    atomEntry = rest.format.parseFeedDocument(serverContent)

    if isinstance(atomEntry, rest.format.AtomFeed):
        try:
            atomEntry = list(atomEntry)[0]
        except IndexError as e:
            # Handle cases where no entry is found
            return None

    # optimistically try to parse as Atom; fall through if just primitive already
    try:
        contents = atomEntry.toPrimitive()
    except:
        logger.debug('getEntity - got entity that is not Atom entry; fallback to string handling; %s/%s' % (entityPath, entityName))
        contents = splunk.util.toDefaultStrings(atomEntry)

    entity = Entity(entityPath, '', contents, namespace)

    try:
        entity.owner = atomEntry.author
        entity.updateTime = atomEntry.updated
        entity.summary = atomEntry.summary
        entity.links = atomEntry.links
        entity.id = atomEntry.id
        entity.name = atomEntry.title
        entity.hostPath = hostPath
        entity.links = atomEntry.links

    except AttributeError as e:
        logger.debug('getEntity - unable to retrieve AtomEntry property: %s' % e)

    entity.updateOptionalRequiredFields()

    return entity



def setEntity(entity, sessionKey=None, uri=None, msgObj=None, strictCreate=False, filterArguments=None):
    '''
    Commits the properties of a generic entity object
    '''
    import splunk.auth as auth

    logger.debug("entity.setEntity() is deprecated")

    if not entity:
        raise Exception('Cannot set entity; no entity provided')

    if not entity.path:
        raise Exception('Entity does not have path defined')

    if not entity.name:
        raise Exception('Entity does not have name defined')

    if not entity.namespace:
        raise Exception('Cannot set entity without a namespace; %s' % entity.name)

    # if editing entities that were owned by the system name, then convert to
    # to current user
    if not entity.owner:
        entity.owner = auth.getCurrentUser()['name']

    #check if we should filter arguments based on optional/required/wildcardFields
    #only enabled for datamodel and data/ui/views for now
    if filterArguments is None:
        filterArguments = False
        if entity.path.startswith("data/models") or re.match("^\/?data\/ui\/(nav|views)(\/|$)", entity.path) or re.match("^\/?saved\/searches(\/|$)", entity.path):
            filterArguments = True

    tmpEntity = None
    if not uri:
        # This is where we determine edit / create behavior. WoNkY!
        if len(entity.links) > 0:
            for action, link in entity.links:
                if action == 'edit':
                    uri = link

        if uri == None:
            uri = entity.getFullPath()
            if filterArguments:
                tmpEntity = getEntity(entity.path, None, uri=uri + "/_new", sessionKey=sessionKey)

    if entity.path.startswith('data/props/extractions'):
        # SPL-145572 Add the parameter as POST arg and append query string to uri to pass the check in rest.checkResourceExists
        entity.properties['safe_encoding'] = 1
        qs = { 'safe_encoding': entity.properties['safe_encoding'] }
        uri = uri + '?' + urllib_parse.urlencode(qs)

    if filterArguments and tmpEntity == None:
        tmpEntity = getEntity(entity.path, entity.name, uri=uri, sessionKey=sessionKey)

    if filterArguments:
        postargs = entity.getCommitProperties(optionalFields=tmpEntity.optionalFields, requiredFields=tmpEntity.requiredFields, wildcardFields=tmpEntity.wildcardFields, isACL=uri.endswith('/acl'), filterArguments=filterArguments)
    else:
        postargs = entity.getCommitProperties()


    """
    logger.debug("*" * 25)
    logger.debug("entity: %s." % entity)
    logger.debug("uri: %s." % uri)
    logger.debug("postargs: %s." % postargs)
    logger.debug("*" * 25)
    """

    if not postargs:
        logger.warn('setEntity - tried to commit empty entity')
        raise Exception('setEntity - tried to commit empty entity')

    # if exists, then update by POST to own endpoint
    if rest.checkResourceExists(uri, sessionKey=sessionKey) and not strictCreate:

        # EAI sets entity.name to new for the new template...
        # so it will exist and not fall into the else case
        # do any of the endpoints used by Entity post back to
        # a nonexistent name for the create action?
        # EAI posts to the basePath.
        if entity.name == '_new':
            logger.debug("setting properties to create a new guy.")
            uri = entity.getBasePath()
            createName = entity.properties['name']
            logger.debug("creating %s on %s." % (createName, uri))
            entity.name = createName

        serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey, postargs=postargs, raiseAllErrors=True)
        if (serverResponse.status == 201):
            if msgObj:
                msgObj['messages'] = serverResponse.messages

        if serverResponse.status not in [200, 201]:
            logger.warn("Server did not return status 200 or 201.")
        else:
            try:
                atomFeed = rest.format.parseFeedDocument(serverContent)
                entity.id = list(atomFeed)[0].id
            except Exception as e:
                pass

        return True


    # otherwise, create new by POST to parent endpoint
    else:

        # ensure that a name is included in the args
        if entity.name and 'name' not in postargs:
            postargs['name'] = entity.name

        uri = entity.getBasePath()
        serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey, postargs=postargs, raiseAllErrors=True)

        if serverResponse.status == 201:
            if msgObj:
                msgObj['messages'] = serverResponse.messages

            try:
                atomFeed = rest.format.parseFeedDocument(serverContent)
                entity.id = atomFeed[0].id
            except Exception as e:
                pass

            return True

    # if we haven't existed, then raise
    raise splunk.RESTException(serverResponse.status, serverResponse.messages)


def controlEntity(action, entityURI, sessionKey=None):
    if action == 'remove':
        serverResponse, serverContent = rest.simpleRequest(entityURI, sessionKey=sessionKey, method='DELETE', raiseAllErrors=True)
    elif action == 'enable':
        serverResponse, serverContent = rest.simpleRequest(entityURI, sessionKey=sessionKey, method='POST', raiseAllErrors=True)
    elif action == 'disable':
        serverResponse, serverContent = rest.simpleRequest(entityURI, sessionKey=sessionKey, method='POST', raiseAllErrors=True)
    elif action == 'unembed':
        serverResponse, serverContent = rest.simpleRequest(entityURI, sessionKey=sessionKey, method='POST', raiseAllErrors=True)
    elif action == 'quarantine':
        serverResponse, serverContent = rest.simpleRequest(entityURI, sessionKey=sessionKey, method='POST', raiseAllErrors=True)
    elif action == 'unquarantine':
        serverResponse, serverContent = rest.simpleRequest(entityURI, sessionKey=sessionKey, method='POST', raiseAllErrors=True)
    else:
        raise Exception('unknown action=%s' % action)

    if serverResponse.status == 200:
        return True
    else:
        raise Exception('unhandled HTTP status=%s' % serverResponse.status)


def deleteEntity(entityPath, entityName, namespace, owner, sessionKey=None, hostPath=None):
    '''
    Deletes an entity
    '''

    uri = buildEndpoint(entityPath, entityName, namespace=namespace, owner=owner, hostPath=hostPath)
    serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey, method='DELETE', raiseAllErrors=True)

    if serverResponse.status == 200:
        logger.info('deleteEntity - deleted entity=%s' % uri)
        return True
    else:
        raise Exception('deleteSearch - unhandled HTTP status=%s' % serverResponse.status)


def refreshEntities(entityPath, **kwargs):
    '''
    Forces a content refresh on the specified entityPath; not all entities support a refresh

    **kwargs represents the complete parameter spec of getEntities()

    NOTE: currently, splunkd endpoints implement refresh in 2 ways:
        a)  by appending a URI param: /foo/bar?refresh=1
        b)  by calling a subendpoint: /foo/bar/_reload

    TODO: at some point, all endpoints need to be normalized to 1 method
    '''

    # TODO: this extra call is to determine which refresh mode
    # should be attempted
    collection = getEntities(entityPath, **kwargs)

    # check on endpoints that auto-register refreshes
    isEAI = False
    for link in collection.links:
        if link[0] == '_reload':
            isEAI = True
            break

    if isEAI:
        getEntity(entityPath, '_reload', **kwargs)
    else:
        kwargs['refresh'] = "1"
        getEntities(entityPath, **kwargs)


class EntityCollection(util.OrderedDict):
    '''
    Represents a generic splunkd collection of entities
    '''

    def __init__(self, dict=None, search=None, count=0, offset=0, totalResults=None, itemsPerPage=None, sort_key=None, sort_dir=None, links=[], messages=[]):
        super(EntityCollection, self).__init__(dict)

        self.search = search
        self.count = count
        self.offset = offset
        self.totalResults = totalResults
        self.itemsPerPage = itemsPerPage
        self.sort_key = sort_key
        self.sort_dir = sort_dir
        self.links = links
        self.messages = messages
        self.actions = {}


class Entity(object):
    '''
    Represents a generic splunkd entity object.
    '''

    def __init__(self, entityPath, entityName, contents=None, namespace=None, owner=None):
        self.namespace = namespace
        self.name = entityName
        self.owner = owner
        self.updateTime = 0
        self.createTime = 0
        self.properties = {}
        self.value = None
        self.id = None
        self.summary = None
        self.links = []
        self.requiredFields = []
        self.optionalFields = []
        self.wildcardFields = []

        self.actions = {}

        # by default, id=name; change if necessary
        self.id = entityName

        self.hostPath = None

        # Handle case where entityPath may be a list
        if isinstance(entityPath, list):
            self.path = quotePath(entityPath)
        else:
            self.path = entityPath

        if contents:
            self._parseContents(contents)

    def __getitem__(self, key):
        return self.properties[key]

    def __setitem__(self, key, value):
        self.properties[key] = value

    def __iter__(self):
        return self.properties.__iter__()

    def __contains__(self, key):
        return self.properties.__contains__(key)

    def __repr__(self):
        return "<splunk.entity.Entity object - path=%s'>" % (self.path + '/' + self.name)

    def __str__(self):
        if self.value != None:
            return splunk.util.toDefaultStrings(self.value)
        elif len(self.properties) > 0:
            return splunk.util.toDefaultStrings(self.properties)
        else:
            return ''

    def get(self, key, df=None):
        return self.properties.get(key, df)

    def getFullPath(self):
        owner = self.owner
        try:
            if self['eai:acl']['sharing'] != 'user':
                owner = EMPTY_OWNER_NAME
        except KeyError:
            pass

        return buildEndpoint(self.path, self.name, namespace=self.namespace, owner=owner, hostPath=self.hostPath)

    def getBasePath(self):
        return buildEndpoint(self.path, None, namespace=self.namespace, owner=self.owner, hostPath=self.hostPath)

    def items(self):
        return self.properties.items()

    def iteritems(self):
        return iter(self.properties.items())

    def keys(self):
        return self.properties.keys()


    def getLink(self, linkName):
        '''
        Returns the URI associated with the entity link with rel=<linkName>.
        Entity links are used to refer to other resources that are related
        to the current entity, i.e. job assets or EAI actions.

        If multiple links exist for the same <linkName>, only the first one
        specified in the Atom feed will be returned.
        '''
        for pair in self.links:
            if pair[0] == linkName:
                return pair[1]
        return None

    def updateOptionalRequiredFields(self, optionalFields=None, requiredFields=None, wildcardFields=None):

        if optionalFields is None:
            optionalFields = []
        if requiredFields is None:
            requiredFields = []
        if wildcardFields is None:
            wildcardFields = []

        self.requiredFields = requiredFields
        self.optionalFields = optionalFields
        self.wildcardFields = wildcardFields

        #get optional/required args
        if 'eai:attributes' in self:
            #only replace if we have the eai:attributes
            if 'requiredFields' in self['eai:attributes']:
                self.requiredFields += self['eai:attributes']['requiredFields']
            if 'optionalFields' in self['eai:attributes']:
                self.optionalFields += self['eai:attributes']['optionalFields']
            if 'wildcardFields' in self['eai:attributes']:
                self.wildcardFields += self['eai:attributes']['wildcardFields']

    def _parseContents(self, contents):
        '''
        Read in the additional payload associated with an entity (usually
        generated by a toPrimitive() method) and insert into the correct location.
        '''

        if isinstance(contents, dict):
            self.properties = contents

            # set the entity ID, if specified in the ID mapping of ENTITY_ID_MAP
            if self.path in ENTITY_ID_MAP:
                if ENTITY_ID_MAP[self.path] not in contents:
                    logger.debug('_parseContents - unable to set entity ID; key=%s not found' % ENTITY_ID_MAP[self.path])
                    return
                self.id = contents[ENTITY_ID_MAP[self.path]]

        # TODO: should be handle list objects here too?

        else:
            self.value = splunk.util.toDefaultStrings(contents)


    def getCommitProperties(self, optionalFields=None, requiredFields=None, wildcardFields=None, isACL=False, filterArguments=False):

        # get existing props
        props = self.properties.copy()

        #try to update the optional and required fields, just in case
        self.updateOptionalRequiredFields(optionalFields, requiredFields, wildcardFields)

        if filterArguments:
            if isACL:
                #just don't filter ACL properties; they work differently
                pass
            #filter out args not in optional or required args
            elif len(self.requiredFields) + len(self.optionalFields) + len(self.wildcardFields) > 0:
                regexList = [re.compile(field) for field in (self.wildcardFields)]
        
                for k in list(props.keys()):  # keys() for Py2 and list() for Py3 required here as dictionary is modified during iteration
                    didMatch = False
                    if k in self.requiredFields or k in self.optionalFields:
                        didMatch = True
                    else:
                        #In a perfect world, we'd replace this for-loop with a wildcardmatcher-style trie implementation
                        for r in regexList:
                            if re.match(r, k):
                                didMatch = True
                                break

                    if not didMatch:
                        del props[k]

        else:
            #if no required or optional fields availabe, resort to Amrit's megahack
            # only propagate ACL information if accessing the ACL sub-endpoint, otherwise delete all eai:* attributes
            # open an issue about this. filtering out imported_capabilities for now, but that list will grow as other
            # yes this is mega hack and please to remove when SPL-26543 is resolved
            for k in list(props.keys()):  # keys() for Py2 and list() for Py3 required here as dictionary is modified during iteration
                if k.startswith('eai:') and k != 'eai:data' and (self.name != 'acl' or k != 'eai:acl') \
                 or k.startswith('imported_capabilities') or k.startswith('imported_srchFilter') or \
                 k.startswith('imported_srchIndexesAllowed') or k.startswith('imported_srchIndexesDefault') \
                 or k.startswith('imported_srchTimeWin'):
                    del props[k]

        return props

# tests
if __name__ == '__main__':

    import unittest

    #logging.basicConfig(level=logging.DEBUG)

    class EntityGettersTest(unittest.TestCase):

        def testEndpointConstruct(self):

            self.assertEquals(
                buildEndpoint('myclass'),
                '/services/myclass'
            )

            self.assertEquals(
                buildEndpoint('my/class'),
                '/services/my/class'
            )

            self.assertEquals(
                buildEndpoint('my/class', 'objname'),
                '/services/my/class/objname'
            )

            self.assertEquals(
                buildEndpoint('my/class', namespace='virtualNS'),
                '/servicesNS/%s/virtualNS/my/class' % EMPTY_OWNER_NAME
            )

            self.assertEquals(
                buildEndpoint('my/class', namespace='virtualNS', owner='mildred'),
                '/servicesNS/mildred/virtualNS/my/class'
            )

            self.assertEquals(
                buildEndpoint('my/class', entityName='everything (*&^%%$$', namespace='virtual space NS', owner='mildred user'),
                '/servicesNS/mildred%20user/virtual%20space%20NS/my/class/everything%20%28%2A%26%5E%25%25%24%24'
            )

    class EntityTest(unittest.TestCase):

        def testConstructor(self):

            x = Entity('test/path/here', 'test_name')

            self.assertEquals(x.path, 'test/path/here')
            self.assertEquals(x.name, 'test_name')
            self.assertEquals(x.id, 'test_name')

        def testContentParseString(self):

            x = Entity('the/path', 'the_name', 'I am plain string')

            self.assertEquals(x.value, 'I am plain string')
            self.assertEquals(x.properties, {})


            x = Entity('the/path', 'the_name', u"abc_\u03a0\u03a3\u03a9.txt".encode('UTF-8'))

            self.assertEquals(x.value, u'abc_\u03a0\u03a3\u03a9.txt')
            self.assertEquals(x.value, 'abc_\xce\xa0\xce\xa3\xce\xa9.txt')
            self.assertEquals(x.properties, {})

        def testContentParseDict(self):

            x = Entity('the/path', 'the_name', {'a':1, 'b':u'abc_\u03a0\u03a3\u03a9.txt'.encode('UTF-8'), u'\u03a0c':3})

            self.assertEquals(x.value, None)
            self.assertEquals(x.properties, {'a':1, 'b':u'abc_\u03a0\u03a3\u03a9.txt'.encode('UTF-8'), u'\u03a0c':3})
            self.assertEquals(x['a'], 1)
            self.assert_('a' in x)
            self.assertEquals(x[u'\u03a0c'], 3)

    class SavedSearchTest(unittest.TestCase):

        def setUp(self):
            import splunk.auth as auth
            self.sessionKey = auth.getSessionKey('admin', 'changeme')
            self.owner = 'admin'

        def testListing(self):

            listing = getEntities('saved/searches', namespace=splunk.getDefault('namespace'), sessionKey=self.sessionKey, owner=self.owner)
            self.assert_('Errors in the last hour' in listing)

            entityList = getEntitiesList('saved/searches', namespace=splunk.getDefault('namespace'), sessionKey=self.sessionKey, owner=self.owner)
            listContainsSearch = False
            for entity in entityList:
                if entity.name == 'Errors in the last hour':
                    listContainsSearch = True
                    break
            self.assert_(listContainsSearch)

        """
        def testFilterListing(self):

            filters = {
            'viewstate.resultView': 'reportView'
            }
            listing = getEntities('saved/searches', namespace=splunk.getDefault('namespace'), sessionKey=self.sessionKey, filters=filters, owner=self.owner)

            self.assert_('Messages by minute last 3 hours' in listing)
            self.assert_('Splunk errors last 24 hours' not in listing)
        """

        def testSearchFilterListing(self):

            filters = 'access_*'
            listing = getEntities('saved/searches', namespace=splunk.getDefault('namespace'), sessionKey=self.sessionKey, search=filters, owner=self.owner)

            self.assert_('Splunk errors last 24 hours' not in listing)
            self.assert_('Errors in the last 24 hours' in listing)

        def testSingle(self):

            entity = getEntity('saved/searches', 'Errors in the last 24 hours', namespace=splunk.getDefault('namespace'), sessionKey=self.sessionKey, owner=self.owner)

            self.assert_(isinstance(entity, Entity))

            self.assertEquals(entity.name, 'Errors in the last 24 hours')
            self.assertEquals(entity['search'], 'error OR failed OR severe OR ( sourcetype=access_* ( 404 OR 500 OR 503 ) )')



        def testNonExistent(self):

            self.assertRaises(splunk.ResourceNotFound, getEntity, 'whoa_nellie', self.sessionKey)

        def testCreateAndDelete(self):

            name = 'test_saved_search_' + str(int(time.time()))
            string = '| search foo'
            #namespace = 'samples'
            #namespace = 'debug' #samples app no longer included in build, see SPL-18783
            namespace = 'search' #apparently debug isn't either... just do it in the search app.

            search = Entity('saved/searches', name, namespace=namespace, owner=self.owner)
            search['search'] = string
            setEntity(search)

            challenge = getEntity('saved/searches', name, namespace=namespace, owner=self.owner)
            self.assertEqual(challenge.name, name)
            self.assertEqual(challenge.namespace, namespace)
            self.assertEqual(challenge['search'], string)

            deleteEntity('saved/searches', name, namespace=namespace, owner=self.owner)
            self.assert_(not rest.checkResourceExists(buildEndpoint('/saved/searches/', name, namespace=namespace)))


        def testUpdate(self):

           search = getEntity('saved/searches', 'Messages by minute last 3 hours', namespace=splunk.getDefault('namespace'), sessionKey=self.sessionKey, owner=self.owner)

           testvalue = 'test subject %s' % str(time.time())
           search['action.email.subject'] = testvalue
           setEntity(search)

           challenge = getEntity('saved/searches', 'Messages by minute last 3 hours', namespace=splunk.getDefault('namespace'), sessionKey=self.sessionKey, owner=self.owner)

           self.assertEquals(challenge['action.email.subject'], testvalue)


    class IndexTest(unittest.TestCase):

        def setUp(self):
            import splunk.auth as auth
            self.sessionKey = auth.getSessionKey('admin', 'changeme')

        def testListing(self):

            listing = getEntities('data/indexes', sessionKey=self.sessionKey)
            self.assert_('main' in listing)
            self.assert_('_audit' in listing)
            self.assert_('history' in listing)

        def testSearchFilter(self):
            '''
            Test the generic ability for EAI endpoints to provide searching
            capability
            '''

            listing = getEntities('data/indexes', sessionKey=self.sessionKey, search='audit')

            self.assert_('_audit' in listing)

        def testSingle(self):

            index = getEntity('data/indexes', 'main', sessionKey=self.sessionKey)

            self.assert_('homePath' in index)
            self.assert_('blockSignSize' in index)


    class MiscTest(unittest.TestCase):
        pass


    # exec all tests
    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(EntityGettersTest))
    suites.append(loader.loadTestsFromTestCase(SavedSearchTest))
    suites.append(loader.loadTestsFromTestCase(IndexTest))
    suites.append(loader.loadTestsFromTestCase(EntityTest))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
