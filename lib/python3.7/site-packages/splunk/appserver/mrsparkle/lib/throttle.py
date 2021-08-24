"""
CherryPy Tool that crudely simulates a throttled connection

Both connection latency and per-ip bandwidth can be controlled

To set the throttle to 150ms latency and (approximately) a 512Kbit connection:
tools.throttle.on = True
tools.throttle.latency = 150 
tools.throttle.bandwidth = 50

Use this thing only for testing; it'd be pretty inefficient for production use!
"""

from builtins import range
import cherrypy
import threading
import time


class ThrottleTool(cherrypy.Tool):
    def __init__(self):
        self._point = 'before_finalize'
        self._name = 'throttle'
        self._priority = 100  # must run last (after gzip etc) to be useful
        self._iplocks = {}
        self._setargs()

    def _setup(self):
        # hook latency in early as a redirect or exception during a handler
        # will prevent the before_finalize hook from running
        cherrypy.request.hooks.attach('on_start_resource', self._latency, priority=1)
        cherrypy.Tool._setup(self)

    def _latency(self):
        conf = self._merged_args()
        latency = conf.get('latency')
        if latency:
            time.sleep(float(latency)/1000)

    def _trickle(self, body, bandwidth, mtu):
        bandwidth *= 1024
        iplock = self._iplocks.setdefault(cherrypy.request.remote.ip, threading.RLock())
        for chunk in body:
            for offset in range(0, len(chunk), mtu):
                slice = chunk[offset:offset+mtu]
                s = time.time()
                yield slice
                d = time.time()-s
                wait = (float(len(slice)) / bandwidth) - d 
                if wait>0:
                    # ensure only one thread per ip gets to wait at a time so bandwidth 
                    # is "shared" between a user's concurrent connections
                    iplock.acquire() 
                    time.sleep(wait)
                    iplock.release()

    def callable(self, latency=0, bandwidth=None, mtu=576):
        """
        latency - Time in milliseconds to wait before starting to send the response
        bandwidth - Speed of connection to simulate in kilobytes/second
        mtu - Size of chunks of data to send in each pass, in bytes
        """
        if bandwidth:
            cherrypy.response.body = self._trickle(cherrypy.response.body, bandwidth, mtu)


cherrypy.tools.throttle = ThrottleTool()
