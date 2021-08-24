from __future__ import absolute_import
from builtins import object

import logging
import os
from threading import Lock
import time

try:
    import cherrypy
    import cherrypy.process.plugins as plugins
except ImportError:
    cherrypy = None
    plugins = None

from decorator import decorator

import splunk.entity

logger = logging.getLogger('splunk.appserver.mrsparkle.cached')


# define the duration (in seconds) to cache the function output
MAX_CACHE_AGE = 5

# how often to clean the cache in seconds
CLEAN_FREQ = 30


class Memoizer(object):
    '''
    Decorator helper that caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned, and
    not re-evaluated.

    Memoized methods do not share cache data between different instances of the same class
    The arguments of a function to be memoized must be hashable to use this routine.

    The default lifetime of the cache is defined in MAX_CACHE_AGE but it can be set per function.

    Usage:
    @memoized()
    def foo(...):
       pass

    or
    @memoized(cache_age=30) # in seconds
    def foo(...):
      pass

    Callers can force a function's cache to be flushed immediately by passing the function
    an argument of __memoized_flush_cache=1
    '''
    cache = {} # cachekey: (lock, expiretime, data)
    clean_thread = None

    def __init__(self, cache_age=MAX_CACHE_AGE):
        self.cache_age = cache_age

    @classmethod
    def clean_up(cls):
        timenow = time.time()
        cache = cls.cache
        # as we don't lock inside this loop there's a small chance we may
        # throw out an expired item that's been updated during the loop
        # i can live with that risk; at worst we'll just regenerate the data again
        for cachekey, entry in list(cache.items()): # Cannot remove item while iterating on a dictionary in Py3
            if timenow > entry[1]:
                logger.debug('Memoizer expired cachekey=%s' % (cachekey,))
                del cache[cachekey]

    def __call__(self, func, *args, **kwargs):
        cache = self.cache
        if '__memoized_flush_cache' in kwargs:
            flush_cache = kwargs['__memoized_flush_cache']
            del kwargs['__memoized_flush_cache']
        else:
            flush_cache = False

        try:
            # create an unmutable cache key from sessionKey, positional and keyword args
            # as the first positional arg will be self/cls for methods, this also binds the cache to an object or class
            cachekey = (cherrypy.session.get('sessionKey'), func, args, frozenset(kwargs.items()))
            lock, expire, data = cache.setdefault(cachekey, (Lock(), 0, None))
            # cachentry's lock remains valid even if the clean thread has now deleted the cache entry
        except TypeError as e:
            # It is expected that if an argument of the function is not hashable,
            # e.g. mutable ([1, 2, [1,2,3]], {'a': {'foot': 'bar'}}) or __hash__
            # not defined, its result cannot be cached. Call the function directly.
            logger.debug("memoized decorator used on function %s with non hashable arguments" % (func, ))
            # import traceback
            #tb = "".join(traceback.format_stack())
            #logger.debug("memoized decorator used on function %s with non hashable arguments %s.  Traceback:\n%s" % (func, (args, kwargs), tb))
            return func(*args, **kwargs)

        timenow = time.time()
        if timenow < expire and not flush_cache:
            # cache hit
            return data

        cls = self.__class__
        if not cls.clean_thread:
            # start a background thread to remove stale data periodically
            # this technique is borrowed from Cherrypy's session lib
            cls.clean_thread = t = cherrypy.process.plugins.Monitor(cherrypy.engine, cls.clean_up, CLEAN_FREQ)
            t.subscribe()
            t.start()

        with lock: # may block
            # maybe someone who just held the lock we acquired updated the data
            dum, expire, data = cache.get(cachekey, (lock, 0, None))
            if timenow < expire and not flush_cache:
                # yup; it got updated; cache hit
                return data

            # else it's expired
            # if func raises an exception then the cache won't be updated
            data = func(*args, **kwargs)
            self.cache[cachekey] = (lock, time.time()+self.cache_age, data)
            return data


def memoized(cache_age=MAX_CACHE_AGE):
    """The actual memoized decorator"""
    helper = Memoizer(cache_age)
    @decorator
    def dec(fn, *a, **kw):
        if cherrypy is None:
            return fn(*a, **kw)
        else:
            return helper(fn, *a, **kw)
    return dec



@memoized()
def getEntity(*args, **kwargs):
    '''
    Memoized version of splunk.entity.getEntity
    '''
    return splunk.entity.getEntity(*args, **kwargs)


@memoized()
def getEntities(*args, **kwargs):
    '''
    Memoized version of splunk.entity.getEntities
    '''
    return splunk.entity.getEntities(*args, **kwargs)


@memoized()
def isModSetup(app):
    """
    Determines if the specified app had modsetup config files and memorize result.
    Memorizing here would help not accessing the disk multiple times
    :param app:
    :return:
    """
    import splunk.appserver.mrsparkle.lib.util as util
    temp_json_path = util.make_splunkhome_path(['etc', 'apps', app, 'appserver', 'static', 'setup.json'])
    temp_html_path = util.make_splunkhome_path(['etc', 'apps', app, 'appserver', 'static', 'setup.html'])
    logger.info(temp_json_path)
    if os.path.exists(temp_json_path) and os.path.exists(temp_html_path):
        return True
    return False
