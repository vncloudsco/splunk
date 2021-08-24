
#
#  View object search mode enums
#
#  Many view objects can request search data from the backend.  In this view
#  object model, each search aware object must declare a single search
#  mode in which to operate.
#

# define ad-hoc search string mode
from builtins import object
STRING_SEARCH_MODE = 'string'

# define saved search run mode
SAVED_SEARCH_MODE = 'saved'

# define form search template run mode
TEMPLATE_SEARCH_MODE = 'template'

# define search post process mode
POST_SEARCH_MODE = 'postsearch'



class ViewObject(object):
    '''
    Represents the abstract base class for all high-level view objects.  The
    abstract methods declared below assert that an object must be able to
    serialize and deserialize itself from XML, and also transpose itself into
    the module data tree structure.
    '''
    
    matchTagName = None
    '''Defines the XML tag name that identifies this object in an XML document'''
    
    
    def fromXml(self, lxmlNode):
        '''
        Parses an XML node and attempts to convert into a panel object
        '''
        raise NotImplementedError('The %s class has not properly implemented fromXml()' % self.__class__)
    
        
    def toXml(self):
        '''
        Returns an XML string representation of this object
        '''
        raise NotImplementedError('The %s class has not properly implemented toXml()' % self.__class__)


    def toObject(self):
        '''
        Returns a native data structure that represents this object
        '''
        raise NotImplementedError('The %s class has not properly implemented toObject()' % self.__class__)
