"""
These classes supply custom session lock behaviour

Normally cherrypy acquires an exclusive lock on a session for the duration of a request,
which essentially means requests are handled sequentially for a given client even
if the request handler doesn't make any changes to the session data.

This update causes cherrypy to acquire a shared lock instead by default.  A handler
can acquire an exclusive lock instead by using the @lock_session decorator.

This uses a local shared lock to protect against races between threads
and a file level lock to protect against races between processes
"""

from builtins import object

import logging
import os.path
import time
import threading
from builtins import range

import cherrypy
import cherrypy._cptools
from cherrypy.lib import httputil as http
import splunk.appserver.mrsparkle.lib.portalocker as portalocker

logger = logging.getLogger('splunk.appserver.lib.sessions')


class SessionException(Exception): pass

class SessionTool(cherrypy._cptools.SessionTool):
    def _lock_session(self):
        if not hasattr(cherrypy.request.handler, 'callable') or not getattr(cherrypy.request.handler.callable, 'lock_session', None):
            # default to acquiring a shared lock for sessions unless the handler explicitly requests otherwise with the @lock_session decorator
            try:
                cherrypy.serving.session.acquire_lock(read_lock=True)
                return
            except TypeError:
                pass
        cherrypy.serving.session.acquire_lock()

cherrypy.tools.sessions = SessionTool()


EXLOCK = 1
SHLOCK = 2
class SharedLock(object):
    """
    A non re-entrant shared/exclusive lock
    This version implements a queue so locking requests are handled in order
    preventing requests for exclusive locks being locked out for long periods of time
    by continuous shared lock requests
    """
    def __init__(self):
        self.exlocked = False
        self.mutex = threading.Lock()
        self.shcount = 0
        self.lockq = []
        self.mtime = 0

    def acquire(self, exclusive=False):
        self.mutex.acquire()
        if exclusive:
            while self.shcount or self.exlocked:
                lock = threading.Lock()
                lock.acquire()
                self.lockq.append( (EXLOCK, lock) )
                self.mutex.release()
                lock.acquire()
                self.mutex.acquire()
            self.exlocked = True
        else:
            queue = True
            while self.exlocked or (queue and self.lockq):
                queue = False
                lock = threading.Lock()
                lock.acquire()
                self.lockq.append( (SHLOCK, lock) )
                self.mutex.release()
                lock.acquire()
                self.mutex.acquire()
            self.shcount += 1
        self.mtime = time.time()
        self.mutex.release()

    def release(self):
        self.mutex.acquire()
        if self.exlocked:
            self.exlocked = False
            self._wakenext()
        else:
            self.shcount -= 1
            if self.shcount == 0 and self.lockq:
                self._wakenext()
        self.mutex.release()

    def is_locked(self):
        return self.shcount or self.exlocked

    def _wakenext(self):
        if self.lockq:
            # wake up all queued shared locks or just the first first exlock
            if self.lockq[0][0] == EXLOCK:
                locktype, lock = self.lockq.pop(0)
                lock.release()
            else:
                for i in range(len(self.lockq)):
                    if self.lockq[0][0]  == EXLOCK:
                        break # only wake pending shared locks
                    locktype, lock = self.lockq.pop(0)
                    lock.release()



class FileSession(cherrypy.lib.sessions.FileSession):
    locks = {}
    masterlock = threading.Lock()

    def _delete(self):
        try:
            path = self._get_file_path()
            os.unlink(path)
            self.delete_lock(path)
        except OSError:
            pass

    def __init__(self, *a, **kw):
        self._changed = False
        self.locktype = None
        super(FileSession, self).__init__(*a, **kw)

    def __get_changed(self):
        return self._changed

    def __set_changed(self, val):
        if val:
            self._ensure_ex_lock()
        self._changed = val

    changed = property(__get_changed, __set_changed)

    @classmethod
    def get_session_lock(cls, session_id):
        """Return a SharedLock object for a given session id, creating one if required"""
        lock = cls.locks.get(session_id)
        if lock:
            return lock
        cls.masterlock.acquire()
        lock = cls.locks.get(session_id)
        if not lock:
            lock = cls.locks[session_id] = SharedLock()
        cls.masterlock.release()
        return lock

    def __setitem__(self, key, value):
        self.changed = True
        super(FileSession, self).__setitem__(key, value)

    def __delitem__(self, key):
        self.changed = True
        super(FileSession, self).__delitem__(key)

    def _ensure_ex_lock(self):
        if self.locktype == portalocker.LOCK_EX:
            return
        if not self.locked:
            return self.acquire_lock(read_lock=False)
        logger.info('Attempted to update session data while holding a shared lock - Consider using @lock_session - request_path=%s' % (cherrypy.request.path_info))
        self.escalate_lock()

    def _touch_session(self):
        try:
            os.utime(self._get_file_path(), None)
        except OSError:
            pass # file doesn't exist which is normal if it's already expired and hasn't been updated

    def save(self):
        if self._changed and self.loaded:
            self._save(self.timeout) # specify relative minutes for timeout instead of absolute time
        elif self.loaded:
            self._touch_session()

    def load(self):
        data = self._load()
        if data is None:
            self._data = {}
        else:
            mtime = os.path.getmtime(self._get_file_path())
            if time.time() - mtime > data[1]*60:

                self._data = {} # expired!
                self._changed = True

                logger.debug('Session expired mtime=%d time=%s path=%s' % (mtime, time.time(), self._get_file_path()))
            else:
                self._data = data[0]
        self.loaded = True

        # Stick the clean_thread in the class, not the instance.
        # The instances are created and destroyed per-request.
        cls = self.__class__
        if self.clean_freq and not cls.clean_thread:
            # clean_up is an instance method and not a classmethod,
            # so that tool config can be accessed inside the method.
            t = cherrypy.process.plugins.Monitor(cherrypy.engine, self.clean_up, (self.clean_freq * 60))
            t.subscribe()
            cls.clean_thread = t
            t.start()

    def clean_up(self):
        """Clean up expired sessions."""
        logger.debug("cleaning stale sessions")
        now = time.time()
        suffix_len = len(self.LOCK_SUFFIX)
        # Iterate over all session files in self.storage_path
        lockfiles = set()
        active_sessions = set()
        for fname in os.listdir(self.storage_path):
            if fname.startswith(self.SESSION_PREFIX):
                path = os.path.join(self.storage_path, fname)
                if not fname.endswith(self.LOCK_SUFFIX):
                    # We have a session file: lock and load it and check
                    #   if it's expired. If it fails, nevermind.
                    active_sessions.add(path)
                    self.acquire_lock(path)
                    try:
                        contents = self._load(path)
                        # _load returns None on IOError
                        if contents is not None:
                            mtime = os.path.getmtime(path)
                            data, expiration_time = contents
                            if (now - mtime) > (expiration_time * 60):
                                # Session expired: deleting it
                                try:
                                    username = data['user']['name']
                                    session = data['sessionKey']
                                    logger.info('user=%s action=logout status=success reason=session-timeout' % (username))
                                except (KeyError, AttributeError) as e:
                                    # User wasn't logged in, but had session
                                    pass
                                os.unlink(path)
                                self.release_lock(path)
                                active_sessions.discard(path)
                    except Exception as e:
                        logger.debug("Exception trying to clean up session path: %s e: %s" % (path, e))
                        active_sessions.discard(path) # make sure lock file gets deleted
                    finally:
                        self.release_lock(path)
                else:
                    session_path = path[:-suffix_len]
                    lockfiles.add(session_path)

        # find entries in lockfiles that aren't in session_files are delete them
        for session_path in lockfiles.difference(active_sessions):
            self.delete_lock(session_path)

        # find any currently unused lock objects and remove them to avoid leaking memory
        self.masterlock.acquire()
        try:
            unset = []
            t = time.time()
            for sid, lock in list(self.locks.items()):
                if not lock.is_locked() and lock.mtime is not None and t-lock.mtime > 60:
                    logger.debug("Purging idle lock for sid %s" % sid)
                    unset.append(sid)
            for sid in unset:
                del self.locks[sid]
        except Exception as e:
            logger.error("Trapped exception during lock cleanup: %s" % e)
        finally:
            self.masterlock.release()

    def acquire_lock(self, path=None, read_lock=False):
        """Acquire an exclusive or read lock on the currently-loaded session data."""
        if self.locked:
            return
        start = time.time()
        self.lock = lock = self.get_session_lock(self.id)
        lock.acquire(exclusive=not read_lock)
        try:
            if path is None:
                path = self._get_file_path()

            if not os.path.exists(path):
                lock.release()
                self.lock = None
                self.release_lock()
                return

            lockpath = path + self.LOCK_SUFFIX
            lockfile = open(lockpath, 'a+')

            locktype = portalocker.LOCK_SH if read_lock else portalocker.LOCK_EX
            self.locktype = locktype
            portalocker.lock(lockfile, locktype)

            self.locked = True
            self.lockfile = lockfile
            end = time.time()
            logger.debug('Session lock acquired delayms=%d read_lock=%s' % ((end-start)*1000, read_lock))
        except Exception as e:
            logger.exception(e)
            lock.release()
            self.lock = None
            raise

    def release_lock(self, path=None):
        if not self.locked:
            return
        if path is None:
            path = self._get_file_path()

        if self.lockfile:
            # portalocker unlocks when the file handle is closed
            self.lockfile.close()
        else:
            # we are releasing a stale lock that we don't have a file handle for anymore
            self.delete_lock(path)
        self.locked = False
        self.lockfile = None
        self.lock.release()
        self.lock = None
        logger.debug('Session lock released: %s' % path)

    def delete_lock(self, path):
        try:
            path += self.LOCK_SUFFIX
            os.unlink(path)
        except OSError:
            pass

    def escalate_lock(self):
        """
        Convert a read lock into a write lock - will reload the session first
        to avoid any possible race conditions
        """
        start = time.time()
        if not self.locked:
            self.acquire_lock(read_lock=False)
            self.load()
            end = time.time()
            logger.debug('Session lock acquired delayms=%d read_lock=False' % ((end-start)*1000))
            return
        if self.locktype == portalocker.LOCK_EX:
            return
        self.release_lock()
        self.acquire_lock(read_lock=False)
        self.load()
        end = time.time()
        logger.debug('Session lock upgraded delayms=%d read_lock=False' % ((end-start)*1000))




cherrypy.lib.sessions.FileSession = FileSession
