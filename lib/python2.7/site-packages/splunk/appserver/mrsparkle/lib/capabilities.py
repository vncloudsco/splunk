from builtins import object
import splunk.appserver.mrsparkle.lib.cached as cached

import splunk.entity as en
import lxml.etree as et
import logging
import cherrypy

logger = logging.getLogger('splunk.appserver.mrsparkle.lib.capabilities')

class Capabilities(object):
    """
    Provides an interface to the capabilities system.
    """
    
    def deny_access(self, msg = "Insufficient user permissions"):
        """
        Implements the response behavior for unauthorized requests.
        The request attempt is logged, and a 404 error is raised.
        """
        logger.error('Access denied for path "%s". Returning 404. %s' % (
            cherrypy.request.path_info,
            msg))
        raise cherrypy.HTTPError(404)
        
    # Splunkd Entity Access Queries
    # -----------------------------
    
    def can_create_entity(self, path):
        return self.entity_has_link(path, 'create')
        
    def entity_has_link(self, path, link):
        entities = en.getEntities(path)
        for ln in entities.links:
            if ln[0] == link:
                return True
        return False
    
    # Manager XML Access Queries
    # --------------------------
    
    # When the required capabilities to access a manager page are already
    # defined in the manager-XML file, we can avoid duplicating the knowledge
    # by checking for access to the manager xml itself.
    #
    # This usually happens for interstitial pages that must decide whether
    # to show a link to a particular page. Rather than check for the capabilities
    # themselves, just check if you can access the desired page.
    #
    # Note: This is preferrable to checking splunkd entity access,
    #       since the manage XML checks are cached and do not require
    #       a rest request to determine access.
    
    def can_access_manager_xml_file(self, file_name):
        """
        Same as can_access_manager_xml, but by file_name
        """
        for file in self.each_accessible_xml_file():
            if file == file_name:
                return True
        return False
        
    def each_accessible_xml_file(self):
        helper_en = cached.getEntities('data/ui/manager', count=-1, namespace='search')
        for e in helper_en:
            if len(helper_en[e].get('eai:data')) == 0:
                continue
            yield e
    
    def accessible_endpoints(self):
        """
        Returns the list of endpoint names that the current user can access.
        """
        return list(self.each_accessible_endpoint())
    
    def select_accessible_endpoints(self, wanted):
        """
        Accepts a list of endpoint names, and returns those that are accessible
        to the current user.
        """
        result = []
        for endpoint in self.each_accessible_endpoint():
            if endpoint in wanted:
                result.append(endpoint)
        return result
        
    def can_access_manager_xml(self, endpoint_name):
        """
        Determines whether the current user has the capabilities required to
        access the manager xml page identified by the `endpoint_name` parameter.

        endpoint_name: The name attribute of the <endpoint> tag
                  in the manager xml file.
        """
        for endpoint in self.each_accessible_endpoint():
            if endpoint == endpoint_name:
                return True
        return False
        
    def each_accessible_endpoint(self):
        """
        Generator that yields each endpoint name that is accessible to the
        current user, allowing lazy iteration.
        """
        helper_en = cached.getEntities('data/ui/manager', count=-1, namespace='search')
        for e in helper_en:
            if len(helper_en[e].get('eai:data')) == 0:
                continue
            endpoint = self._get_endpoint_name(helper_en[e].get('eai:data'))
            if endpoint != None:
                yield endpoint
                
    def _get_endpoint_name(self, root_str):
        """
        Private. Gets the endpoint name from the `root_str` of a manager xml file.
        """
        if not root_str: return
        parser = et.XMLParser(remove_blank_text=True, remove_comments=True)
        root = et.XML(root_str, parser)
        if root.tag != 'endpoint':
            return None
        return root.attrib['name']
