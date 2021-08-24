from __future__ import division
# override CherryPy's default log manager to redirect it's internal messages to splunk's logging infrastructure
import logging
import cherrypy
from cherrypy._cplogging import LogManager
from cherrypy import _cperror
import splunk.appserver.mrsparkle.lib.util as util
import splunk.util
import datetime
import time
import sys

class SplunkedLogManager(LogManager):
    """ Subclass LogManager to pass access and error messages to splunks logging """

    # it's a shame it's necessary to duplicate this entire method to add a request id to the log format
    # I considered hooking into the logger's foratter instead but that's even more of a hack
    def access(self):
        """Write to the access log (in Apache/NCSA Combined Log format).
        
        Like Apache started doing in 2.0.46, non-printable and other special
        characters in %r (and we expand that to all parts) are escaped using
        \\xhh sequences, where hh stands for the hexadecimal representation
        of the raw byte. Exceptions from this rule are " and \\, which are
        escaped by prepending a backslash, and all whitespace characters,
        which are written in their C-style notation (\\n, \\t, etc).
        """
        request = cherrypy.request
        remote = request.remote
        response = cherrypy.serving.response
        outheaders = response.headers
        inheaders = request.headers

        try:
            username = cherrypy.session['user']['name']
        except:
            username = None

        atoms = {'h': remote.name or remote.ip,
                 'l': '-',
                 'u': username or "-",
                 't': self.access_time(response.time),
                 'r': request.request_line,
                 's': response.status.split(" ", 1)[0],
                 'b': outheaders.get('Content-Length', '') or "-",
                 'f': inheaders.get('Referer', ''),
                 'a': inheaders.get('User-Agent', ''),
                 }
        for k, v in list(atoms.items()):
            if sys.version_info < (3, 0) and isinstance(v, unicode):
                v = v.encode('utf8')
            elif sys.version_info >= (3, 0) and isinstance(v, bytes):
                v = v.decode(errors="backslashreplace")
            elif not isinstance(v, str):
                v = str(v)
            # Fortunately, repr(str) escapes unprintable chars, \n, \t, etc
            # and backslash for us. All we have to do is strip the quotes.
            v = repr(v)[1:-1]
            # Escape double-quote.
            atoms[k] = v.replace('"', '\\"')
        
        try:
            # the dash before the request id in this line represents a virtual host name that
            # we're not currently logging, but might in the future.  
            # Some web log analysis tools expect the combined log format to have a vhost name in it.
            if sys.version_info >= (3, 0):
                base_msg = self.access_log_format.format(**atoms)
            else:
                base_msg = self.access_log_format % atoms
            self.access_log.log(logging.INFO, base_msg + (' - %s %dms' % (util.get_request_id(), round((time.time() - response.time)*1000))))
        except:
            self(traceback=True)

    def access_time(self, req_time):
        now = datetime.datetime.fromtimestamp(req_time)
        monthnames = [ 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec' ]
        month = monthnames[now.month - 1]
        return ('[%02d/%s/%04d:%02d:%02d:%02d.%03d %s]' %
                (now.day, month, now.year, now.hour, now.minute, now.second, 
                 now.microsecond//1000, splunk.util.format_local_tzoffset(req_time)))
