from builtins import object
import cgi
import cherrypy
import logging
import splunk.util
from decorator import decorator

logger = logging.getLogger('splunk.appserver.mrsparkle.lib.message')

QUEUE_SESSION_KEY = 'queue'
QUEUE_INFO_LEVEL = 'info'
QUEUE_ERROR_LEVEL = 'error'



def get_session_queue():
    """
    Creates or returns une pickled session Queue object with a key of QUEUE_SESSION_KEY
    """
    sess = cherrypy.session
    if QUEUE_SESSION_KEY in sess:
        return sess.get(QUEUE_SESSION_KEY)
    else:
        sess[QUEUE_SESSION_KEY] = SessionQueue()
        return sess[QUEUE_SESSION_KEY]

@decorator
def save_to_session(fn, self, *a, **kw):
    '''Simple decorator that ensures cherrypy's session gets re-written.'''
    ret_val = fn(self, *a, **kw)
    cherrypy._test_session_has_changed = True
    if (hasattr(cherrypy, 'session')):
        if self.isChanged():
            cherrypy.session.acquire_lock()
            if hasattr(cherrypy.session, 'changed'):
                cherrypy.session.changed = True
            cherrypy.session[QUEUE_SESSION_KEY] = self
            
    return ret_val


def send_client_message(level, msg):
    '''Mechanism for sending a message to the client from the server.'''
    cherrypy.response.headers['X-Splunk-Messages-Available'] = 1
    get_session_queue().add(level, msg)


class Queue(object):
    """
    A dead simple container for storing temporary system messages categorized by level.
    """

    def __init__(self):
        self.queue = []
        self.changed = False

    def isChanged(self):
        return self.changed

    def add(self, level, message):
        """
        Add a message to a list with a specified level.
        Order is perserved.
        Args:
            level: The level marker for the message.
            message: The message string to store.
        """
        logger.debug('adding level:%s, message:%s' % (level, message))
        self.changed = True
        self.queue.append({'message': message, 'time': splunk.util.getISOTime(), 'level': level})

    def get_level(self, level, delete=True):
        """
        Retrieve a list of messages based on a specified level.
        Args:
            level: The level cagegory for a list of messages.
            delete: Delete the list of messages from this level after retrieval.
        """   
        matches = []
        items = self.queue[:]
        for item in items:
            if item['level'] is level:
                matches.append(item)
                if delete:
                    self.queue.pop(self.queue.index(item))
        if matches:
            self.changed = delete
        else:
            self.changed = False
        return matches      
   
    def get_levels(self):
        """
        Retrieve a sorted list of distinct message levels stored in the queue.
        """   
        levels = []
        for item in self.queue:
            levels.append(item['level'])
        uniques = sorted(set(levels))
        return uniques
        
    def get_len(self, level=None):
        """
        Retrieve the length of messages based on a specified level or the length of all messages combined.
        Args:
            level: The level cagegory for a list of messages.
        """   
        if level is None:
            return len(self.queue)
        else:
            return len(self.get_level(level, delete=False))
    
    def get_all(self, delete=True):
        """
        Retrieve the entire message list.
        Args:
            delete: Delete the entire message list entries after retrieval.
        """   
        self.changed = False
        queue = self.queue[:]
        if delete and self.queue:
            self.changed = True
            self.queue = []
        return queue

    def fifo(self, delete=True):
        """
        First in first out (fifo) - retrieve the first message in the list.
        Args:
            delete: Delete the message list entry after retrieval.
        """
        if len(self.queue) is 0:
            self.changed = False
            return None
        if delete:
            self.changed = True
            queue = self.queue
        else:
            self.changed = False
            queue = self.queue[:]
        return queue.pop(0)
    
    def lifo(self, delete=True): 
        """
        Last in first out (lifo) - retrieve the last message in the list.
        Args:
            delete: Delete the message list entry after retrieval.
        """
        if len(self.queue) is 0:
            self.changed = False
            return None
        if delete:
            self.changed = True
            queue = self.queue
        else:
            self.changed = False
            queue = self.queue[:]
        return queue.pop()



class SessionQueue(Queue):
    '''
    A mirror of the Queue object that ensures if it's stored in a modified
    Cherrypy session, the session is properly rewritten when necessary.
    '''

    def __init__(self):
        Queue.__init__(self)

    @save_to_session
    def add(self, level, message):
        super(SessionQueue, self).add(level, message)

    @save_to_session
    def get_level(self, level, delete=True):
        return super(SessionQueue, self).get_level(level, delete)
    
    @save_to_session
    def get_all(self, delete=True):
        return super(SessionQueue, self).get_all(delete)

    @save_to_session
    def fifo(self, delete=True):
        return super(SessionQueue, self).fifo(delete)
    
    @save_to_session 
    def lifo(self, delete=True): 
        return super(SessionQueue, self).lifo(delete)


if __name__ == '__main__':

    import unittest
    
    class QueueTests(unittest.TestCase):

        def testQueue(self):
            queue = Queue()
            queue.add("notice", "notice string1")
            queue.add("notice", "notice string2")
            queue.add("notice", "notice string3")

            self.assert_(len(queue.get_levels()) is 1)
            self.assert_(queue.get_levels()[0] is "notice")
            self.assert_(queue.get_len(level="notice") is 3)
            self.assert_(queue.get_len() is 3)
            self.assert_(len(queue.get_level("notice")) is 3)
            self.assert_(len(queue.get_level("notice")) is 0)
            self.assert_(queue.get_len(level="notice") is 0)
            self.assert_(queue.get_len() is 0)
    
            queue.add("notice", "notice string1")
            queue.add("notice", "notice string2")
            queue.add("notice", "notice string3")

            self.assert_(len(queue.get_level("notice", delete=False)) is 3)
            self.assert_(len(queue.get_level("notice")) is 3)
            self.assert_(len(queue.get_level("notice")) is 0)

            queue.add("notice", "notice string1")
            queue.add("notice", "notice string2")
            queue.add("notice", "notice string3")
            queue.add("message", "message string1")
            queue.add("message", "message string2")
            queue.add("message", "message string3")
            queue.add("message", "message string4")

            self.assert_(len(queue.get_levels()) is 2)
            self.assert_(queue.get_levels().index("notice") is 1)
            self.assert_(queue.get_levels().index("message") is 0)
            self.assert_(queue.get_len(level="notice") is 3)
            self.assert_(queue.get_len(level="message") is 4)
            self.assert_(queue.get_len() is 7)

            messages = queue.get_all()

            self.assert_(queue.get_len(level="notice") is 0)
            self.assert_(queue.get_len(level="message") is 0)
            self.assert_(queue.get_len() is 0)
            self.assert_(len(messages) is 7)
            self.assert_(len(queue.get_level("notice")) is 0)
            self.assert_(len(queue.get_level("message")) is 0)

            queue.add("notice", "notice string1")
            queue.add("notice", "notice string2")
            queue.add("notice", "notice string3")
            queue.add("message", "message string1")
            queue.add("message", "message string2")
            queue.add("message", "message string3")
            queue.add("message", "message string4")

            self.assert_(queue.get_len(level="notice") is 3)
            self.assert_(queue.get_len(level="message") is 4)
            self.assert_(queue.get_len() is 7)

            messages = queue.get_all(delete=False)

            self.assert_(queue.get_len(level="notice") is 3)
            self.assert_(queue.get_len(level="message") is 4)
            self.assert_(queue.get_len() is 7)
            self.assert_(len(messages) is 7)
            self.assert_(len(queue.get_level("notice")) is 3)
            self.assert_(len(queue.get_level("message")) is 4)

            queue = Queue()
            queue.add("notice", "notice string1")
            queue.add("notice", "notice string2")
            queue.add("notice", "notice string3")

            self.assert_(queue.fifo(delete=False)['message'] is "notice string1")
            self.assert_(queue.fifo(delete=True)['message'] is "notice string1")
            self.assert_(queue.fifo(delete=True)['message'] is "notice string2")
            self.assert_(queue.fifo(delete=True)['message'] is "notice string3")
            self.assert_(queue.fifo(delete=True) is None)

            queue = Queue()
            queue.add("notice", "notice string1")
            queue.add("notice", "notice string2")
            queue.add("notice", "notice string3")

            self.assert_(queue.lifo(delete=False)['message'] is "notice string3")
            self.assert_(queue.lifo(delete=True)['message'] is "notice string3")
            self.assert_(queue.lifo(delete=True)['message'] is "notice string2")
            self.assert_(queue.lifo(delete=True)['message'] is "notice string1")
            self.assert_(queue.lifo(delete=True) is None)

    class QueueTestsChanged(unittest.TestCase):
        
        def setUp(self):
            self.queue = Queue()
            self.assert_(self.queue.isChanged() is False)

            self.queue.add("notice", "notice string1")
            self.assert_(self.queue.isChanged() is True)

        def testQueueChangedGetLevel(self):
            #get_level
            self.queue.get_level("notice", False)
            self.assert_(self.queue.isChanged() is False)
            self.queue.get_level("notice", True)
            self.assert_(self.queue.isChanged() is True)
            self.queue.get_level("notice")
            self.assert_(self.queue.isChanged() is False)

            self.queue.add("notice", "notice string1")
            self.assert_(self.queue.isChanged() is True)
            self.queue.get_level("message", True)
            self.assert_(self.queue.isChanged() is False)
            self.queue.get_level("notice", True)
            self.assert_(self.queue.isChanged() is True)

        def testQueueChangedGetAll(self):
            #get_level
            self.queue.get_all(False)
            self.assert_(self.queue.isChanged() is False)
            self.queue.get_all(True)
            self.assert_(self.queue.isChanged() is True)
            self.queue.get_all()
            self.assert_(self.queue.isChanged() is False)

        def testQueueChangedFifo(self):
            #get_level
            self.queue.add("notice", "notice string2")
            self.queue.add("notice", "notice string3")

            self.assert_(self.queue.fifo(delete=False)['message'] == "notice string1")
            self.assert_(self.queue.isChanged() is False)
            self.assert_(self.queue.fifo(delete=True)['message'] == "notice string1")
            self.assert_(self.queue.isChanged() is True)
            self.assert_(self.queue.fifo(delete=True)['message'] == "notice string2")
            self.assert_(self.queue.isChanged() is True)
            self.assert_(self.queue.fifo(delete=True)['message'] == "notice string3")
            self.assert_(self.queue.isChanged() is True)
            self.assert_(self.queue.fifo(delete=True) is None)
            self.assert_(self.queue.isChanged() is False)

        def testQueueChangedLifo(self):
            #get_level
            self.queue.add("notice", "notice string2")
            self.queue.add("notice", "notice string3")

            self.assert_(self.queue.lifo(delete=False)['message'] == "notice string3")
            self.assert_(self.queue.isChanged() is False)
            self.assert_(self.queue.lifo(delete=True)['message'] == "notice string3")
            self.assert_(self.queue.isChanged() is True)
            self.assert_(self.queue.lifo(delete=True)['message'] == "notice string2")
            self.assert_(self.queue.isChanged() is True)
            self.assert_(self.queue.lifo(delete=True)['message'] == "notice string1")
            self.assert_(self.queue.isChanged() is True)
            self.assert_(self.queue.lifo(delete=True) is None)
            self.assert_(self.queue.isChanged() is False)


    class SessionQueueTests(unittest.TestCase):
        
        def setUp(self):
            self.queue = SessionQueue()

            cherrypy._test_session_has_changed = False

        def tearDown(self):
            self.assert_(cherrypy._test_session_has_changed is True)
            self.queue = None

        def testSessionQueueAdding(self):
            self.queue.add('error', 'foo')

        def testSessionQueueGetLevel(self):
            self.queue.get_level('error')

        def testSessionQueueGetAll(self):
            self.queue.get_all()

        def testSessionQueueFifo(self):
            self.queue.fifo()
                
        def testSessionQueueLifo(self):
            self.queue.lifo()


    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(QueueTests))
    suites.append(loader.loadTestsFromTestCase(QueueTestsChanged))
    suites.append(loader.loadTestsFromTestCase(SessionQueueTests))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))

