from builtins import range
from builtins import object

import splunk
import splunk.entity as en
import logging
import random

logger = logging.getLogger('splunk.appserver.mrsparkle.lib.viewstate')

# define EAI endpoint to manage viewstates
VIEWSTATE_ENTITY_CLASS = 'data/ui/viewstates'

# define reserved viewstate hash key name for get/set default prefs
CURRENT_VIEWSTATE_KEY = '_current'

# define the view_id identifier that indicates a global search context
GLOBAL_VIEW_IDENTIFIER = '*'


def buildStanzaName(view, viewstate_id):
    return view + ':' + str(viewstate_id)

def buildParamName(module, *keys):
    return module + '.' + '.'.join(keys)

def parseViewstateHash(viewstate_hash):
    '''
    Parses a viewstate hash and determines if it is an absolute or relative
    identifier.  The viewstate hash can be of the forms:

        // relative identifier; view_id is implied by context
        <viewstate_id>

        // absolute identifier: view_id can be different than context
        <view_id>:<viewstate_id>

        // global identifier: all view_id are searches for viewstate_id
        *:<viewstate_id>

    Returns a tuple:

        ({<view_id> | None}, <viewstate_id>)
    '''

    if not viewstate_hash:
        raise ValueError('viewstate_id cannot be null')

    parts = str(viewstate_hash).split(':', 2)
    if len(parts) > 1:
        return (parts[0], parts[1])
    else:
        return (None, parts[0])


def generateViewstateId(make_universal=False):
    '''
    Returns a random string to be used as a viewstate identifier
    '''
    population = 'abcdefghijklmnopqrstuvwxyz0123456789'
    output = ''.join([random.choice(population) for i in range(8)])
    if make_universal:
        return buildStanzaName(GLOBAL_VIEW_IDENTIFIER, output)
    else:
        return output


def get(view, viewstate_id, namespace, owner, sessionKey=None):
    '''
    Returns a viewstate object that defines a param set
    '''

    logger.debug('get - view=%s viewstate_id=%s namespace=%s owner=%s' % (view, viewstate_id, namespace, owner))

    altView = view

    # empty viewstate means default sticky state
    if viewstate_id == None:
        viewstate_id = CURRENT_VIEWSTATE_KEY

    # otherwise check if viewstate is absolute
    else:
        altView, viewstate_id = parseViewstateHash(viewstate_id)

    logger.debug("Found altView: %s viewstate_id: %s" % (altView, viewstate_id))

    # construct proper stanza search string
    if altView == None:
        stanzaSearch = buildStanzaName(view, viewstate_id)
    else:
        # altView can only be None if a viewstate_id was defined
        # but no view was found when parseViewstateHash was run,
        # thus we almost always get here.
        stanzaSearch = buildStanzaName(altView, viewstate_id)

    # 1) Two part strategy, first try to get the viewstate by name. This usually works.
    # 2) If nothing is returned, run the search in case a generic viewstate
    #    is provided.
    #
    # This turns 1 request into 2 in some edge cases but for 90% of the issues I found
    # it eliminated the slower search requests viewstate was previously making.
    try:
        matchingStanzas = en.getEntities('/'.join([VIEWSTATE_ENTITY_CLASS, stanzaSearch]), namespace=namespace, owner=owner, sessionKey=sessionKey)
    except splunk.ResourceNotFound as e:
        matchingStanzas = en.getEntities(VIEWSTATE_ENTITY_CLASS, namespace=namespace, owner=owner, search="name=%s" % stanzaSearch, sessionKey=sessionKey)

    if len(matchingStanzas) > 1:
        # This looks dangerous, no?
        raise Exception('get - found %s viewstates that match: %s' % (len(matchingStanzas), stanzaSearch))

    # requests for the default sticky state are always optimistic; only
    # error out if a specific viewstate ID is requested
    if (viewstate_id != CURRENT_VIEWSTATE_KEY) and (len(matchingStanzas) == 0):
        raise splunk.ResourceNotFound('Viewstate object not found; view=%s viewstate=%s' % (view, viewstate_id))

    # get first matching stanza, or create new
    if len(matchingStanzas) > 0:
        stanzaName, stanza = list(matchingStanzas.items())[0]
        output = Viewstate(stanzaName)
    else:
        stanza = []
        output = Viewstate()
        output.view = view
        output.id = viewstate_id

    output.namespace = namespace
    output.owner = owner

    # deserialize module key prefs
    for key in stanza:
        if key.startswith('eai:'):
            continue
        keypair = key.split('.', 1)
        if len(keypair) < 2:
            if key != 'disabled':
                logger.warn('Found invalid keyname in viewstate stanza: %s' % key)
            continue

        value = stanza[key]
        if value == None:
            value = ''
        output.modules.setdefault(keypair[0], {})
        output.modules[keypair[0]].setdefault(keypair[1], value)

    return output


def commit(viewstate):
    '''
    Persists a viewstate object.
    '''

    if not isinstance(viewstate, Viewstate):
        raise ValueError('Cannot commit viewstate; Only viewstate objects supported')

    # check required properties
    for k in ['namespace', 'owner', 'view']:
        getattr(viewstate, k)

    # assert that the viewstate_id is not a hash
    if viewstate.id.find(':') > -1:
        raise ValueError('Cannot commit viewstate: viewstate_id contains a colon: %s' % viewstate.id)


    entityWrapper = en.Entity(
        VIEWSTATE_ENTITY_CLASS,
        buildStanzaName(viewstate.view, viewstate.id),
        namespace=viewstate.namespace,
        owner=viewstate.owner
    )
    for module_name in sorted(viewstate.modules):
        for param_name in sorted(viewstate.modules[module_name]):
            entityWrapper[buildParamName(module_name, param_name)] = viewstate.modules[module_name][param_name]
    en.setEntity(entityWrapper)

    return True


def clone(viewstate):
    '''
    Clones a viewstate object
    '''
    viewstate.id = generateViewstateId()
    return commit(viewstate)


def setSharing(viewstate, shareMode):
    '''
    Sets the sharing mode: 'global', 'app', 'user'
    '''

    if not isinstance(viewstate, Viewstate):
        raise ValueError('Cannot update viewstate; Only viewstate objects supported')

    # first fetch all the ACL data
    vsACL = en.getEntity(
        VIEWSTATE_ENTITY_CLASS + '/' + buildStanzaName(viewstate.view, viewstate.id),
        'acl',
        namespace=viewstate.namespace,
        owner=viewstate.owner
    )

    # create new object and update mininum set of properties to support sharing
    aclWrapper = en.Entity(
        VIEWSTATE_ENTITY_CLASS + '/' + buildStanzaName(viewstate.view, viewstate.id),
        'acl',
        namespace=viewstate.namespace,
        owner=viewstate.owner
    )
    aclWrapper['owner'] = viewstate.owner
    aclWrapper['sharing'] = shareMode

    # commit
    en.setEntity(aclWrapper)

    return True



class Viewstate(object):
    '''
    Represents a specific viewstate collection set
    '''

    def __init__(self, viewstate_id=None):
        self.id = None
        self.namespace = None
        self.owner = None
        self.view = None
        self.modules = {}

        if viewstate_id:
            self.view, self.id = parseViewstateHash(viewstate_id)
            if self.view == None:
                self.view = GLOBAL_VIEW_IDENTIFIER


    def update(self, new_viewstate):
        return self.modules.update(new_viewstate.modules)
