from __future__ import absolute_import
from builtins import object

import cherrypy
import copy
from datetime import datetime
import logging
import random

import splunk.appserver.mrsparkle.lib.decorators as decorators
import splunk.appserver.mrsparkle.lib.util as util
import splunk.auth

__doc__ = """
          This provides a framework for messages to be exchanged b/w diff apps within the same cherrypy process.

          There is a MsgPoolMgr that manages all queues that are created. The MsgPoolMgr acts like a singleton and is attached to the cherrypy session. The idea is that in future we may want to
          break the UI message queue into multiple queues eg. PythonUIMsgPool, JSUIMsgPool etc

          1. You have to provide a name for a queue when you create it. The actual name of the queus becomes <name>.<owner>. Thus if the 'admin' user creates a UI queue it will be called: UIMsgPool.admin
             If user 'foobar' creates the same queue, it will be called: UIMsgPool.foobar. This allows diff users to maintain diff queues.
          2. If you attempt to create a queue which already exists, it will return you a handle to the pre-existing queue.
          3. Sample code for use:

             The simplest way:
             ------------------
             from splunk.appserver.mrsparkle.lib.msg_pool import QMGR_SESSION_KEY, UI_MSG_POOL
             id = cherrypy.session[QMGR_SESSION_KEY][UI_MSG_POOL].push('error', _('err msg'))
             msg_obj = cherrypy.session[QMGR_SESSION_KEY][UI_MSG_POOL].pop(id)
             print(msg_obj.uid)
             print(msg_obj.severity)
             print(msg_obj.text)
             print(msg_obj.timestamp)
             print(msg_obj.pq)

             More involved way:
             -------------------
             from splunk.appserver.mrsparkle.lib.msg_pool import MsgPoolMgr, UI_MSG_POOL
             mgr = MsgPoolMgr.get_poolmgr_instance()

             uiq = mgr.get_msgq(UI_MSG_POOL)
             unique_id1 = uiq.push('error', 'error msg text')
             ...
             ...
             ...
             msg = uiq.pop(unique_id1)


             uiq = mgr.get_msgq(UI_MSG_POOL)
             unique_id2 = uiq.push('warn', 'warn msg text')
             ...
             ...
             ...
             msg = uiq.pop(unique_id2)

          """

logger = logging.getLogger('splunk.appserver.lib.msg_pool')

QMGR_SESSION_KEY = 'q_mgr'
UI_MSG_POOL      = 'UIMsgPool'

# -----------------
# -----------------
class Msg(object):
   """
   this represents a msg object that can be passed around
   """

   # -------------------------------------------------------------------------------
   def __init__(self, id, severity, text, parentQ=None, timestamp=datetime.now()):
      """
      construct the msg object
      """
      self._uid = id
      self._severity = severity
      self._text = text
      self._timestamp = timestamp
      self._pq = parentQ #set automatically when a msg is inserted into a queue

   #Once the msg obj is created, all it's attribs are read-only
   #foll methods enforce that...

   # -------------
   @property
   def uid(self):
      return self._uid

   # ------------------
   @property
   def severity(self):
      return self._severity

   # --------------
   @property
   def text(self):
      return self._text

   # ----------------
   @property
   def timestamp(self):
      return self._timestamp

   # ---------------
   def getpq(self):
      return self._pq

   # -------------------
   def setpq(self, pq):
      self._pq = pq

   pq = property(getpq, setpq)

   # ----------------
   def __str__(self):
      return self.__repr__()

   # ------------------
   def __repr__(self):
      try:
         return 'uid: %s, severity: %s, text: %s, timestamp: %s, parent_queue: %s' % (self.uid, self.severity, self.text, str(self.timestamp), self.pq)
      except AttributeError:
         return 'uid: %s, severity: %s, text: %s, timestamp: %s, parent_queue: None' % (self.uid, self.severity, self.text, str(self.timestamp))

# -------------------------
# -------------------------
class MsgPoolMgr(object):
   """
   class to manage a set of message queues
   """

   _msg_queues = {}

   # ------------------------------
   @staticmethod
   def get_poolmgr_instance():
      """
      static method to be used to obtain a handle to the Pool Manager object.
      only one of these exist.
      """

      try:
         return cherrypy.session[QMGR_SESSION_KEY]
      except KeyError:
         cherrypy.session[QMGR_SESSION_KEY] = MsgPoolMgr()
         return cherrypy.session[QMGR_SESSION_KEY]

   # ---------------------------------------------------------------------
   @decorators.lock_session
   def get_msgq(self, name):
      """
      create a new one or get an existing one if it exists.
      """
      owner = cherrypy.session['user'].get('name')

      qname = '%s.%s' % (name, owner)
      if qname in MsgPoolMgr._msg_queues:
         return MsgPoolMgr._msg_queues[qname]
      else:
         MsgPoolMgr._msg_queues[qname] = _UIMsgPool(name=name, owner=owner)
         return MsgPoolMgr._msg_queues[qname]

   # --------------------------
   def __getitem__(self, key):
      """
      support indexing operation
      """
      return self.get_msgq(key)

   def __contains__(self, qname):
      return qname in MsgPoolMgr._msg_queues

   # ---------------------------------------
   @decorators.lock_session
   def delete_msgq(self, name, force=False):
      try:
         if not force:
            if len(MsgPoolMgr._msg_queues[name]) == 0:
               del MsgPoolMgr._msg_queues[name]
               MsgPoolMgr._msg_queues.pop(name)
            else:
               logger.error('Queue %s is not empty, hence it cannot be deleted.' % name)
         else:
            del MsgPoolMgr._msg_queues[name]
            MsgPoolMgr._msg_queues.pop(name)
      except KeyError:
         logger.error('Queue %s does not exist' % name)

   # -------------------
   @decorators.lock_session
   def list_msgq(self):
      """
      list the queues that have been created
      """
      return ','.join(MsgPoolMgr._msg_queues)

# -----------------------
# -----------------------
class _UIMsgPool(object):

   # ------------------------------------
   def __init__(self, *args, **kwargs):
      self._name = '%s.%s' % (kwargs['name'], kwargs['owner'])
      self._data = {}

   # --------------
   @property
   def name(self):
      return self._name

   # -------------------------
   @decorators.lock_session
   def push(self, severity, text):
      """
      overloaded push method
      """
      #we do not support uuid, so create a random number here. microsec time + random number
      #i think it should suffice...
      uid = str(datetime.now().microsecond) + str(random.random())
      msg = Msg(uid, severity, text, parentQ=self._name)
      self._data[uid] = msg

      return uid

   # ----------------
   @decorators.lock_session
   def flush(self):
      """
      ensuring only one way to clear the dict
      """
      self._data.clear()

   # ------------------
   @decorators.lock_session
   def pop(self, key):
      try:
         return self._data.pop(key)
      except KeyError as e:
         logger.info('msg with id %s does not exist in UI message queue' % key)

   # ------------------
   @decorators.lock_session
   def __len__(self):
     return len(self._data)

   # -------------
   @decorators.lock_session
   def list(self):
      temp = copy.deepcopy(self._data)
      for k in temp:
         temp[k] = str(temp[k])
      return temp


# ---------------------------
if __name__ == '__main__':

   import unittest

   MSG_POOL_UI = 'UIMsgPool'

   class MgrPoolTests(unittest.TestCase):

      test_id = ''


      def setUp(self):
        splunk.auth.getSessionKey('admin', 'changeme')
        class SessionMock(dict):
            def escalate_lock(self):
                pass
        session = SessionMock()
        session['user'] = {'name': 'admin'}
        setattr(cherrypy, 'session', session)

      def testSinletonMgrPool(self):
         mgr1 = MsgPoolMgr.get_poolmgr_instance()
         mgr2 = MsgPoolMgr.get_poolmgr_instance()
         self.assertEquals(id(mgr1), id(mgr2))

      def testUIQCreate(self):
         mgr = MsgPoolMgr.get_poolmgr_instance()
         uiq1 = mgr.get_msgq(MSG_POOL_UI)
         uiq2 = mgr.get_msgq(MSG_POOL_UI)
         self.assertEquals(id(uiq1), id(uiq2))

      def testUIQInsert(self):
         mgr = MsgPoolMgr.get_poolmgr_instance()
         uiq = mgr.get_msgq(MSG_POOL_UI)
         MgrPoolTests.test_id = uiq.push('error', 'msg text')
         self.assertEquals(len(uiq), 1)

      def testUIQPop(self):
         mgr = MsgPoolMgr.get_poolmgr_instance()
         uiq = mgr.get_msgq(MSG_POOL_UI)
         x = uiq.pop(MgrPoolTests.test_id)
         self.assertTrue(isinstance(x, Msg))

      def testUIQFlush(self):
         mgr = MsgPoolMgr.get_poolmgr_instance()
         uiq = mgr.get_msgq(MSG_POOL_UI)
         x = uiq.flush()
         self.assertEquals(len(uiq), 0)

   loader = unittest.TestLoader()
   suites = []
   suites.append(loader.loadTestsFromTestCase(MgrPoolTests))
   unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
