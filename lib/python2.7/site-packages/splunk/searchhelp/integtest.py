from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import range
from builtins import object

import random
from threading import Thread
import time
import sys

import splunk.auth
from splunk.searchhelp import searchhelper

from future.moves.urllib.parse import urlencode

if sys.version_info >= (3, 0):
    from http.cookies import SimpleCookie
    import http.client as httplib
else:
    from Cookie import SimpleCookie
    import httplib

class HTTPConnection(object):
    def __init__(self, host, port=None):
        self.host = host
        self.port = port
        self.response = None
        self.cookies = SimpleCookie()

    def request(self, method, url, body=None, headers=None):
        h = httplib.HTTPConnection(self.host, self.port)

        headers = headers or {}
        cookies = []
        for cookie in self.cookies:
            cookies.append('{0}={1}'.format(cookie,
                                            self.cookies[cookie].coded_value))

        headers['cookie'] = '; '.join(cookies)

        h.request(method, url, body, headers)
        self.response = h.getresponse()

        self.cookies = SimpleCookie(self.response.getheader('set-cookie'))


def getConn(username, password):

    conn = HTTPConnection('localhost:8000')
    # Get cval, UID and session id
    conn.request('GET', '/en-US/account/login')
    assert conn.response.status == 200
    # Fix the cval cookie, due to a bug in SimpleCookie a trailing , is present
    conn.cookies['cval'] = conn.cookies['cval'].value[:-1]
    data = {
        'username': username,
        'password': password,
        'cval': conn.cookies['cval'].value
        }
    # Log in
    conn.request('POST', '/en-US/account/login', body=urlencode(data), headers={'Content-Type': 'application/x-www-form-urlencoded'})
    assert conn.response.status == 303
    return conn

## conn.request('GET', '/en-US/api/shelper?snippet=true&namespace=search&search=search+index=_internal|%20stats&showCommandHelp=true&showCommandHistory=true&showFieldInfo=true&useAssistant=true&useTypeahead=true')
## assert conn.response.status == 200
## resp = conn.response
## txt = resp.read()
## print(txt)




def multiuserSimulation(usercount, search):
    class UserSimulationThread(Thread):
        def __init__(self, conn, search, username):
            Thread.__init__(self)
            self.conn       = conn
            self.search     = search
            self.username   = username
            self.sessionKey = splunk.auth.getSessionKey(username, 'changeme')
            self.done = False

        def run(self):
            try:
                #time.sleep(0.5)
                search = self.search + " " + str(random.randint(0,20)) #+ " | stats count"
                #print("username: %s sk: %s running search: %s" % (self.username, self.sessionKey, search))
                #print("username: %s sk: %s" % (self.username, self.sessionKey))
                getargs = urlencode({
                                    'snippet':True,
                                    'namespace':'search',
                                    'search': search,
                                    'showCommandHelp':True,
                                    'showCommandHistory':True,
                                    'showFieldInfo':True,
                                    'useAssistant':True,
                                    'useTypeahead':True
                                    })
                #print("MAKING REQ: %s, %s..." % (self.username, getargs[:100]))
                self.conn.request('GET', '/en-US/api/shelper?%s' % getargs)
                assert self.conn.response.status == 200
                resp = self.conn.response
                txt = resp.read()
                resp.close()
                #print("FINISHED REQ: %s, %s..." % (self.username, getargs[:100]))

                #help = searchhelper.help(self.sessionKey, utils.TEST_NAMESPACE(), self.username, search, None, None, None, 10, None, None,
                #       useTypeahead=True, showCommandHelp=True, showCommandHistory=True, showFieldInfo=True)
                #print(help['typeahead'])

            except Exception as e:
                print(e)
            self.done = True

    start = time.time()
    threads = []
    conns = []
    # kick off initial threads
    for i in range(0, usercount):
        username = 'test%s' % (i % 20)
        conn = getConn(username, 'changeme')
        print("Got connection for %s" % username)
        conns.append(conn)
        user = UserSimulationThread(conn, search, username)
        threads.append(user)
        user.start()
    print("All Users Logged in")
    start = time.time()
    count = 0
    # forever
    while True:
        #time.sleep(0.1)
        # if a thread is done, kick off a new search
        for i in range(0, usercount):
            if threads[i].done:
                count += 1
                username = 'test%s' % (i % 20)
                threads[i] = UserSimulationThread(conns[i], search, username)
                threads[i].start()
        spent = time.time() - start
        if count > 0:
            print("Time: %ss Avg: %ss" % (spent, spent / count))



if __name__ == '__main__':
    monster = "index=_internal  (( (source=\"*/httpd/access_log*\" OR source=\"*\\httpd\\access_log*\" ) status=200 file=splunk-* NOT ( ( useragent=\"Acoon-*\" ) OR ( useragent=\"AdsBot-Google *\" ) OR ( useragent=\"AISearchBot *\" ) OR ( useragent=\"Baiduspider*\" ) OR ( useragent=\"* BecomeBot/*\" ) OR ( useragent=\"Biz360 spider *\" ) OR ( useragent=\"BlogBridge *\" ) OR ( useragent=\"Bloglines-Images/*\" ) OR ( useragent=\"BlogPulseLive *\" ) OR ( useragent=\"BoardReader/*\" ) OR ( useragent=\"bot/*\" ) OR ( useragent=\"* Charlotte*\" OR useragent=\"*(Charlotte/*)\" ) OR ( useragent=\"ConveraCrawler/*\" ) OR ( useragent=\"* DAUMOA-web\" ) OR ( useragent=\"* discobot*\" ) OR ( useragent=\"* DoubleVerify *\" ) OR ( useragent=\"Eurobot/*\" ) OR ( useragent=\"* Exabot/*\" ) OR ( useragent=\"FeedHub *\" ) OR ( useragent=\"Gigabot*\" ) OR ( useragent=\"* Googlebot/*\" OR useragent=\"Googlebot-*\" ) OR ( useragent=\"Grub*\" ) OR ( useragent=\"gsa-crawler *\" ) OR ( useragent=\"* heritrix/*\" ) OR ( useragent=\"ia_archiver*\" ) OR ( useragent=\"BlogSearch/*\" ) OR ( useragent=\"ichiro/*\" ) OR ( useragent=\"Yeti/*\" ) OR ( useragent=\"Inar_spider *\" ) OR ( useragent=\"kalooga/*\" ) OR ( useragent=KeepAliveClient ) OR ( useragent=\"larbin*\" ) OR ( useragent=\"LinkAider\" ) OR ( useragent=\"McBot/*\" ) OR ( useragent=\"MLBot *\" ) OR ( useragent=\"Morfeus Fucking Scanner\" ) OR ( useragent=\"msnbot*\" ) OR ( useragent=\"MSRBOT *\" ) OR ( useragent=*nagios-plugins* ) OR ( useragent=\"* Netcraft *\" ) OR ( useragent=\"*/Nutch-*\" ) OR ( useragent=\"panscient.com\" ) OR ( useragent=\"Pingdom.com_*\" ) OR ( useragent=\"PrivacyFinder/*\" ) OR ( useragent=\"Snapbot/*\" ) OR ( useragent=\"Sogou *\" ) OR ( useragent=\"Speedy Spider *\" ) OR ( useragent=\"Sphere Scout*\" ) OR ( useragent=\"*(Spinn3r *\" ) OR ( useragent=\"Technoratibot/*\" ) OR ( useragent=\"*/Teoma*\" ) OR ( useragent=\"TurnitinBot/*\" ) OR ( useragent=\"*(Twiceler*\" ) OR ( useragent=\"UtilMind *\" ) OR ( useragent=\"* voilabot *\" ) OR ( useragent=\"WebAlta*\" ) OR ( useragent=\"Splunk webping bundle\" ) OR ( useragent=\"* Yahoo! Slurp*\" OR useragent=\"* Yahoo! * Slurp*\" ) OR ( useragent=\"Yanga *\" ) OR ( useragent=\"YebolBot *\" ) ) NOT ( ( clientip=10.0.0.0/8 OR clientip=172.16.0.0/12 OR clientip=192.168.0.0/16 ) ) NOT ( ( clientip=64.127.105.34 OR clientip=64.127.105.60 OR clientip=206.80.3.67 ) ) ) ) _time<1199000000 _time>1198950000"
    #monster = "*"
    multiuserSimulation(19, 'search %s' % monster)
