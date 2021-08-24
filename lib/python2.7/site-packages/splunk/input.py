from __future__ import absolute_import
from __future__ import print_function
from builtins import object

from future.moves.urllib.parse import urlencode
import lxml.etree as et
import datetime
import time
import socket
import httplib2
try:
    import httplib
except ImportError:
    import http.client as httplib
import splunk
import splunk.rest as rest


___doc___ = """
         This script will allow the python sdk to insert data directly into splunk
"""

#global, don't need to create an instance of this on each call, create once and reuse
h = httplib2.Http(disable_ssl_certificate_validation = True, proxy_info=None)

# ---------------------------
# ---------------------------
class StreamHandler(object):
    """
    class that handles the connection
    """

    # ----------------------------------------------------------
    def __init__(self, dest, endpoint, sessionKey, type='http', ssl=True):
        """
        init the connection and buffer
        lazy evaluation here...don't make a connection until the first write call
        """

        self._dest = dest
        self._endpoint = endpoint
        self._sessionKey = sessionKey
        self._type = type
        self._ssl = ssl
        self._conn = None
        self._sslconn = None

    # -------------------------
    def _make_http_conn(self):
        """
        helper function to make a http connection
        """
        if self._ssl:
            self._conn = httplib.HTTPSConnection(self._dest)
        else:
            self._conn = httplib.HTTPConnection(self._dest)
        self._conn.connect()
        self._conn.putrequest('POST', self._endpoint)
        self._conn.putheader('Authorization', 'Splunk ' + self._sessionKey)
        self._conn.putheader('X-Splunk-Input-Mode', 'Streaming')
        self._conn.endheaders()

    # ------------------------
    def _make_sock_conn(self):
        """
        helper fun to make a socket connection
        """

        self._conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = int(self._dest[self._dest.rfind(':') + 1:])
        host = self._dest[:self._dest.rfind(':')]
        if host.startswith('[') and host.endswith(']'):
            host = host[1:-1]
        self._conn.connect(host, port)
        self._sslconn = socket.ssl(self._conn)
        header = "POST %s HTTP/1.0\r\n" % self._endpoint
        header += "Host: localhost:8089\r\n"
        header += "Accept-Encoding: identity\r\n"
        header += "Authorization: Splunk %s\r\n" % self._sessionKey
        header += "X-Splunk-Input-Mode: Streaming\r\n"
        header += "\r\n"

        self._sslconn.write(header)

    # --------------------
    def write(self, data):
        """
        pump this data into splunkd
        """

        if not self._conn:
            if self._type == 'http':
                self._make_http_conn()
            elif self._type == 'socket':
                self._make_sock_conn()

        #the stream endpoint does not return anything, so we don't either
        if self._type == 'socket':
            try:
                self._sslconn.write(data)
            except socket.error as e:
                #maybe owing to large inactivity the connection was cut by server, so try again once more...
                self._make_sock_conn()
                self._sslconn.write(data)

            #send a new line else data will not be recognized as an individual event
            if len(data) and data[-1]!='\n':
                self._sslconn.write("\n")
        else:
            try:
                self._conn.send(data)
            except Exception as e:
                #can get a variety of exceptions here like HTTPException, NotConnected etc etc etc. Just try again.
                self._make_http_conn()
                self._conn.send(data)

            #send a new line else data will not be recognized as an individual event
            if len(data) and data[-1]!='\n':
                self._conn.send("\n")

    # --------------------------------
    def writelines(self, line_list):
        """
        wrapper around write function to write multiple lines
        """

        for line in line_list:
            self.write(line)

    # --------------------
    def send(self, data):
        """
        wrapper for write function for the socket interface
        """

        self.write(data)

    # ---------------
    def flush(self):
        """
        do nothing function to make this class resemble a file like object
        """
        pass

    # ---------------
    def close(self):
        """
        cleanup
        """

        if self._type == 'http':
            self._conn.close()
        else:
            del self._sslconn
            self._conn.close()


# ---------------------------------------------------------------------------
def submit(event, hostname=None, source=None, sourcetype=None, index=None):
    """
    the interface to the 'simple' receivers endpoint
    """

    global h

    #construct the uri to POST to
    base_uri = splunk.mergeHostPath()
    postargs = {'host': hostname, 'source': source, 'sourcetype' : sourcetype, 'index':index}
    uri = base_uri + '/services/receivers/simple?%s' % urlencode(postargs)

    #get default session key. If none exists, the rest call will raise a splunk.AuthenticationFailed exception
    sessionKey = splunk.getDefault('sessionKey')

    #make the call, we cannot use the rest interface here as it urlencodes the payload
    serverResponse, serverContent = h.request(uri, "POST", headers={'Authorization':'Splunk %s' % sessionKey}, body=event)

    #process results
    root = et.fromstring(serverContent)

    #4xx error messages indicate a client side error e.g. bad request, unauthorized etc so raise a RESTException
    if 400 <= serverResponse.status < 500:

          extractedMessages = rest.extractMessages(root)
          msg_text = []
          for msg in extractedMessages:
                msg_text.append('message type=%(type)s code=%(code)s text=%(text)s;' % msg)
          raise splunk.RESTException(serverResponse.status, msg_text)

    #5xx error messages indicate server side error e.g. Internal server error etc so raise a SplunkdException
    elif serverResponse.status >= 500:
          extractedMessages = rest.extractMessages(root)
          msg_text = []
          for msg in extractedMessages:
              msg_text.append('message type=%(type)s code=%(code)s text=%(text)s;' % msg)
          raise splunk.SplunkdException(serverResponse.status, msg_text)

    #everything is kosher...
    else:
      return serverResponse

# -----------------------------------------------------------------------------
def open(hostname=None, source=None, sourcetype=None, index=None, type='http', sessionKey=None, host_regex=None, host_segment=None):
    """
    the interface to the 'stream' receivers endpoint
    """

    #construct the uri to POST to
    base_uri = splunk.mergeHostPath()
    postargs = {'source': source, 'sourcetype' : sourcetype, 'index':index}
    if host_regex:
        postargs['host_regex'] = host_regex
    elif host_segment:
        postargs['host_segment'] = host_segment
    elif hostname:
        postargs['host'] = hostname
    endpoint = '/services/receivers/stream?%s' % urlencode(postargs)

    #get default session key. If none exists, the rest call will raise a splunk.AuthenticationFailed exception
    if not sessionKey:
        sessionKey = splunk.getSessionKey()

    ( proto, host_colon_port ) = base_uri.split("://", 1);
    return StreamHandler(host_colon_port, endpoint, sessionKey, type, proto != 'http')

# --------------------------------------------------------------------
def connect(hostname=None, source=None, sourcetype=None, index=None):
    """
    wrapper for the open to work with sockets
    """

    return open(hostname, source, sourcetype, index, type='socket')


# ---------------------
# utility function
# ---------------------

# --------------------------------------------------
def _get_final_count(host, keyi, fail_msg, ok_msg):
    """
    utility function to see if we inserted into the index properly
    """

    time.sleep(60)
    job = splunk.search.dispatch('search index=default host=%s | stats count' % host, sessionKey=key)

    start = datetime.datetime.now()

    while not job.isDone:
         time.sleep(1)
         now = datetime.datetime.now()
         if int((now - start).seconds) > 20:
              print("REST response took more than 20 seconds, timing out...")
              break

    count = 0
    for ele in job.events:
        count += 1
    job.cancel()

    assert count == 3, fail_msg % count
    print(ok_msg)

# -------------------------
# -------------------------
if __name__ == '__main__':

    import splunk.auth as au
    import splunk.search

    splunk.mergeHostPath('localhost:8089', True)
    key = au.getSessionKey('admin', 'changeme')

    raw_data = """Apr 29 19:11:54  AAA\nApr 29 19:12:54  BBB\nApr 29 19:13:54  CCC\n"""

    # ------------------------------- #
    # test simple receivers endpoint  #
    # ------------------------------- #
    resp = submit(raw_data, sourcetype='http-receivers', index='default', source='http-test', hostname='simple-receivers-test')
    print('insertion for simple receivers complete...querying splunk...waiting 60 seconds...')

    try:
        _get_final_count('simple-receivers-test', key, 'inserted 3 events via simple receivers end point, but found %d', 'insert via simple receivers endpoint - OK')
    except AssertionError as e:
        #test failed, continue to next
        print(e)

    # --------------------------------------- #
    # test stream receivers endpoint via http #
    # --------------------------------------- #
    stream = open(sourcetype='http-receivers', index='default', source='http-test', hostname='stream-http-receivers-test')
    stream.write('Apr 29 18:11:54  AAA')
    stream.writelines(['Apr 29 18:12:54  BBB', 'Apr 29 18:13:54  CCC'])
    stream.close()
    print('insertion for stream http receivers complete...querying splunk...waiting 60 seconds...')

    try:
        _get_final_count('stream-http-receivers-test', key, 'inserted 3 events via stream http receivers end point, but found %d', 'insert via stream http receivers endpoint - OK')
    except AssertionError as e:
        #test failed, continue to next
        print(e)

    # ------------------------------------------ #
    # test stream receivers endpoint via sockets #
    # ------------------------------------------ #
    socket_stream = connect(sourcetype='http-receivers', index='default', source='http-test', hostname='stream-socket-receivers-test')
    socket_stream.send('Apr 29 17:11:54  AAA')
    socket_stream.send('Apr 29 17:12:54  BBB')
    socket_stream.send('Apr 29 17:13:54  CCC')
    socket_stream.close()

    print('insertion for stream socket receivers complete...querying splunk...waiting 60 seconds...')

    try:
        _get_final_count('stream-socket-receivers-test', key, 'inserted 3 events via stream socket receivers end point, but found %d', 'insert via stream socket receivers endpoint - OK')
    except AssertionError as e:
        #test failed, continue to next
        print(e)
