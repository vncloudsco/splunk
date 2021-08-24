from __future__ import absolute_import
import defusedxml.lxml as safe_lxml
import logging
import platform
import time

import splunk
import splunk.clilib.cli_common as comm
import splunk.entity as en
import splunk.rest as rest
import splunk.util as util

logger = logging.getLogger('splunk.auth')

import __main__

def getSessionKey(username, password, hostPath=None, newPassword=None):
    '''
    Get a session key from the auth system
    '''

    uri = '/services/auth/login'
    if hostPath:
        uri = splunk.mergeHostPath(hostPath) + uri
    args = {'username': username, 'password': password }
    
    if newPassword:
        args['new_password'] = newPassword

    # To prove the theory of timing issue of Splunkd not in running state
    # in Windows Bamboo tests, sleep for 10 seconds

    # An attempt to fix SPL-37413
    # if platform.system() == 'Windows':
    #     time.sleep(10)

    serverResponse, serverContent = rest.simpleRequest(uri, postargs=args)

    if serverResponse.status != 200:
        logger.error('getSessionKey - unable to login; check credentials')
        rest.extractMessages(safe_lxml.fromstring(serverContent))
        return None
        
    root = safe_lxml.fromstring(serverContent)
    sessionKey = root.findtext('sessionKey')

    splunk.setDefault('username', username)
    splunk.setDefault('sessionKey', sessionKey)
    
    return sessionKey

def getSessionKeyForTrustedUser(username, hostPath=None):
    '''
    Get a session key from the auth system
    '''

    uri = '/services/auth/trustedlogin'
    if hostPath:
        uri = splunk.mergeHostPath(hostPath) + uri
    args = {'username': username}
    
    serverResponse, serverContent = rest.simpleRequest(uri, postargs=args)

    if serverResponse.status != 200:
        logger.error('getSessionKey - unable to login; check credentials')
        rest.extractMessages(safe_lxml.fromstring(serverContent))
        return None
        
    root = safe_lxml.fromstring(serverContent)
    sessionKey = root.findtext('sessionKey')

    splunk.setDefault('username', username)
    splunk.setDefault('sessionKey', sessionKey)
    
    return sessionKey

def getUserPrefs(key):
    '''
    obtain the user specific preference
    '''
    return en.getEntities('data/user-prefs').get('general').get(key)

def getUserPrefsGeneral(key):
    '''
    obtain the global preference
    '''
    return en.getEntities('data/user-prefs').get('general_default').get(key)

    
def ping(hostPath=None, sessionKey=None):
    '''
    Pings services server and returns a bool for a users session. This method is useful for
    synchronizing an applications authentication with Splunk's services authentication.
    '''    
    uri = '/services'
    if hostPath:
        uri = splunk.mergeHostPath(hostPath) + uri
    
    try:
        serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey)
        return True
    except:
        return False
    
    
def listUsers(**kwargs):
    '''
    Returns a list of users.
    '''
    uri = 'authentication/users'
    return en.getEntities(uri, **kwargs)


def getUser(name=None, id=None, **kwargs):
    '''
    Returns a dictionary of user info for a specific user ID.
    '''
    uri = 'authentication/users'
    if name:
        try:
            info = en.getEntity(uri, name, **kwargs)
            info['name'] = name
            return info
        except splunk.ResourceNotFound:
            return None

    elif id:
        raise Exception('User IDs are no longer available; all users must be identified by name')
        
    else:
        raise TypeError('No arguments specified')


def getCurrentUser():
    '''
    Retrieves current user info from cherrypy session
    '''
    cherryname = None
    if hasattr(__main__, 'IS_CHERRYPY'):
        import cherrypy
        cherryname = cherrypy.session.get('user', {}).get('name')
        if cherryname:
            cherryname = cherryname.strip().lower() 
    
    return  {
        'userid': '-1',
        'name': cherryname or splunk.getDefault('username') or 'UNDEFINED_USERNAME',
        'realname': 'UNDEFINED_REALNAME',
        'roles': ['UNDEFINED_ROLES']
    }  


    
def listRoles(**kwargs):
    '''
    Returns a list of roles.
    '''
    uri = 'authorization/roles'
    return en.getEntities(uri, **kwargs)
    

def getRole(name, **kwargs):
    '''
    Returns a dictionary of role info.
    '''
    if not name:
        raise TypeError('Name argument is missing')

    uri = 'authorization/roles' 
    try:
        return en.getEntity(uri, name, **kwargs)
    except splunk.ResourceNotFound:
        return {}
    
        

    
    
#
# unit tests
#
    
if __name__ == '__main__':
    
    import unittest
    
    class MainTest(unittest.TestCase):

        def testSingleWrites(self):
            key = getSessionKey('admin', 'changeme')
            
            self.assert_(key)
            
        def testGetNotExistUserByName(self):
            key = getSessionKey('admin', 'changeme')

            info = getUser('idontexist', sessionKey=key)
            self.assertEquals(info, None)
            
        def testGetUserByName(self):
            key = getSessionKey('admin', 'changeme')
            
            info = getUser('admin', sessionKey=key)
            self.assertEquals(info['name'], 'admin')
            self.assertEquals(info['realname'], 'Administrator')
            self.assert_('admin' in info['roles'])
            self.assert_('system' in info['eai:acl']['owner'])

        def testGetRole(self):
            key = getSessionKey('admin', 'changeme')
            
            info = getRole('admin', sessionKey=key)
            self.assert_('main' in info['imported_srchIndexesDefault'])
            self.assert_('power' in info['imported_roles'])
            self.assert_('system' in info['eai:acl']['sharing'])
            self.assert_('search' in info['imported_capabilities'])
            
        def testGetListUsers(self):
            key = getSessionKey('admin', 'changeme')
            
            users = listUsers(sessionKey=key)
            self.assert_(len(users) > 0)
            self.assert_('admin' in users)
            
        def testGetListRoles(self):
            key = getSessionKey('admin', 'changeme')
            
            roles = listRoles(sessionKey=key)
            self.assert_(len(roles) > 0)
            self.assert_('admin' in roles)

        def testGetRemoteUserByName(self):
            key = getSessionKey('admin', 'changeme')
            
            info = getUser('admin', sessionKey=key)
            self.assertEquals(info['name'], 'admin')
            self.assertEquals(info['realname'], 'Administrator')
            self.assert_('admin' in info['roles'])
            self.assert_('system' in info['eai:acl']['owner'])            
            
        def testGetRemoteListUsers(self):
            key = getSessionKey('admin', 'changeme')

            users = listUsers(sessionKey=key)
            self.assert_(len(users) > 0)
            self.assert_('admin' in users)       
            
        def testGetRemoteListRoles(self):        
            key = getSessionKey('admin', 'changeme')
            
            roles = listRoles(sessionKey=key)
            self.assert_(len(roles) > 0)
            self.assert_('admin' in roles)
            

    suite = unittest.TestLoader().loadTestsFromTestCase(MainTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
