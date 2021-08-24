from __future__ import print_function
from builtins import object

import cherrypy
import splunk.appserver.mrsparkle # bulk edit
from splunk.appserver.mrsparkle import MIME_HTML
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.decorators import set_cache_level
from splunk.appserver.mrsparkle.lib.routes import route

import splunk.searchhelp.searchhelper as sh
import splunk.searchhelp.utils as shutils
import splunk.search
import logging
import time

logger = logging.getLogger('splunk.appserver.controllers.searchhelper')

class SearchHelperController(BaseController):
    """/searchhelper
    Note the index call accpets POST so the search can be arbitrarily large,
    not because it has any side effects.
    """

    @route('/')
    @expose_page(methods=['GET', 'POST'], handle_api=True)
    @set_cache_level('etag')
    def index(self, search="", insertpos=None, minimize=False, namespace='search', snippet=False, earliest_time=None, latest_time=None,
              count=50, max_time=1, servers=None, useTypeahead=False, showCommandHelp=True, showCommandHistory=True, showFieldInfo=True, snippetEmbedJS=True, **kwargs):

        username   = cherrypy.session['user']['name']
        sessionKey = cherrypy.session['sessionKey']
        prod_type  = cherrypy.config['product_type']
        # skip non Light products from the lookup penalty
        if prod_type != 'lite' and prod_type != 'lite_free':
            prod_type = None

        cherrypy.response.headers['content-type'] = MIME_HTML

        templateArgs = sh.help(sessionKey, namespace, username, search, insertpos, earliest_time, latest_time, count, max_time, servers, useTypeahead=useTypeahead,
                               showCommandHelp=showCommandHelp, showCommandHistory=showCommandHistory, showFieldInfo=showFieldInfo, prod_type=prod_type)
        templateArgs['error'] = getSearchError(search, self.splunkd_urlhost, sessionKey, namespace, username)
        templateArgs['snippetEmbedJS'] = snippetEmbedJS
        
        easter = getEasterEgg(search)
        
        template = 'searchhelper/index.html'
        if easter != None:
            template = easter[0]
            templateArgs['easter'] = easter[1]
        elif snippet:
            template = 'searchhelper/snippet.html'
        return self.render_template(template, templateArgs)

MIN_TIME_BETWEEN_SEARCHES = 1
g_LAST_SEARCH = {}
def getSearchError(search, urlhost, sessionKey, namespace, username):
    global g_LAST_SEARCH
    error = ""
    now = time.time()
    try:
        search = search.strip()
        # if user has moved on to next operator (i.e., lasst character is |[]), warn user about syntax errors
        if len(search) > 0 and search[-1] in "|[]":
            last, lasterror = g_LAST_SEARCH.get(username, (0, ''))
            # only do search every N seconds to prevent calling on each keystroke, esp when editing the middle of a search
            if (now - last) > MIN_TIME_BETWEEN_SEARCHES:
                splunk.search.Parser.parseSearch(search, hostPath=urlhost, sessionKey=sessionKey, namespace=namespace)
                g_LAST_SEARCH[username] = (now, '')                
            else:
                error = lasterror
    except Exception as e:
        # import traceback # traceback.print_exc()
        msg = str(e)
        logger.debug(e)
        ignoredParseErrors = ['Unknown search operation', 'list index out of range']
        for ignoredError in ignoredParseErrors:
            if ignoredError in msg:
                break
        else:
            import re
            # For example \"inputs\"         --> For example "inputs"
            error = msg.replace('\\"', '"')
            # Error in 'SearchOperator:rex': --> In rex:
            # Error in 'rex':                --> In rex:
            # Error in 'rex' command:        --> In rex:
            error = re.sub("Error in '(\\w+:)?(\\w+)'(?: command)?:", "In \\2:", error)
            g_LAST_SEARCH[username] = (now, error)
    return error

professorpoopypants = ''',,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,.NMMMNDI:$NMMNN$.,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,~NMMMNNNNMMMMDNNNN8~,,,,,,,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,,.ONMMMMMNNNNNMNMMMMMMN8:,,,,,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,,MMMMMNMD8O8DNMNMMMMNMMNND:.,,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,MMMMMND8ODNDMMMMMMMMMMNNND8D.,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,.DMMMNMNZNDD88Z$$$ODNMMMMN7DD88.,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,OMMMNNMO888Z$$7II??I7ONMNNDZDD8Z:,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,+MMMMNNNOOO$7II???+====7DNNZZZDZ8Z,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,.NMNMNND8OO$I????+=~~:::~+8NO7ZZ$ZOO,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,:MMMMMDOZZ77I?I?+===~~::::~8D$$$ZOOO,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,:MMMN8OOOZ$77I??+?+==~~:::,~$Z7Z7ZOZ~,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,IMMMDOOOZ$77???+?++=~~:::,,,~7Z$Z$$Z=,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,7MMM88OO$I+====~~~~~::::::,,,:$ZOD8O=,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,=MMN8D8OO$I+=~~::~~~=+=~:~~:,,,ZODO8O,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,:MMDN8OZ$7II?+~:,,,,,::,,.,::,,=Z88OO,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,.MM88Z$77$888O?:..,~+7?~,...,,,,$O88O.,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,MM8O8DNDNNN8O7~,,~I7IZD$:,...,:78Z8D.,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,OMMOZ8OOO8D88O7~,:~?I?+~,,,,..,,7DO7:.,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,.ZNOZZZOOOOOOO$~,,,::~~::,,,,,,,II..~,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,ODOOZZOOOOOO8I::,,:~~~~=~:,,.,,I,..~,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,.Z8OZ$77$ZO8OZ=:,,:,:::::,,,,..,+,:.,.,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,OOZ$I?I$8OZO?:.....,=~:,......,=.=,~,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,.+OO$??ZO88D8Z=..,::.,~=:......,=:..,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,=8O$+78DDD8OZI?+~=::::~+,.....,=..:,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,I8OZ+788OO$7I?=~:::::~I?,.....,+..,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,.88OI=7ZMO$$I+=::,,,7Z7?,....,,+,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,$8OZ?77O88O$$7II+==,:?:,.,..,~~,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,.N8OOOZZZZZI++~,...,:=:,,,.,:=,,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,NN8D8Z$$7I+=~,..,::=:,:.,~=~,,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,~NDNDOZZZI?+~::~=+:=:::,:+,:,,,,,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,.:NNNDOO7?++~:~~=:~+::~==,.,??..,,,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,:NNND$I?7I===~:~I:~+=:...,~:NN$.,,,,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,M8NNMD$I7$7?7?7I===:,....,~~8DDO~..,,,,,,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,,,,,OMMD888NND8O$77III?+,,,.....,+DDDNDDDDD7,,.,,,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,,,:NMMMMM88ZO8OZ7I?+=~::,,,,....,=DDDNNDNDDNDDDD87~,,,,,,,,<br/>,,,,,,,,,,,,,,,,,,,,,7MMMMMMMMD8OZ$OO$?=::,,,,......=DDDDNNNDDNNDDDDDD88O?,,,,,,<br/>,,,,,,,,,,,,,,,,,,8MMMMMMMMMMMM88Z$$$II+:,,.,.,,.:ODDDDNNNN8DNNNDDDNDDDDD8OO:,,,<br/>,,,,,,,,,,,,,,:MMMMMMMMMMMMMMMMNN8Z$$7I+~::~?ZNNNNDDDNNNNDDNDNNDDNNNDDDDDDD8O8=,<br/>,,,,,,,,,,,,DMMMMMMMMMMMMMMMMMMMMMMMMNMMNNNNNNNNNNNNNNNDDDNNNNNDDNNNDDNNDDDDD8OZ<br/>,,,,,,,,,?NNMMNNMMMNMMMMMMMMMMMMMMMMMNNNNNNNNNNNDNNMMDDDNNNNMNDDNNNNDNNNNNNDD888<br/>,,,,,,,:MMMMMNNNNMNNMMMMMMMMNNMMMMMNNNNNNNNNNNNNNMMNDDDNNNNNNDDNNNNNNNNNNNNDDDDD<br/>,,,,,,ONMNMMNNNNMMNNMMMNNMMMMNNNMMMNNNNNNNNNNNNNMNNDNNNNNNNNNDNNNNNDNNNNNNNNDDDD<br/>'''

def getEasterEgg(search):
    imagetexttemplate = '<center><table width="100%%" height="100%%"><tr><td align=center background="%s"><font size="30px" color="black">%s</font></td></tr></table></center>'
    asciitexttemplate = '<div  style="background: white"><code style="color: black">%s</code></div>'

    credits = ( 'searchhelper/creditframe.html', '')
    eastermapping = {
        #'zork': ( 'searchhelper/rawhtml.html', '<iframe src ="http://thcnet.net/zork/index.php" width="100%%" height="100%%"><p>Go West, Young Man.</p></iframe>'),
        #'boss': ('searchhelper/rawhtml.html',  imagetexttemplate % ('http://img.skitch.com/20090612-kd2i9ru8e164tre4y2a9h2u3y.jpg', '<blink>Boss is the <u>best</u>! Top 25 CTO! </blink>')),
        #'ssb' : ('searchhelper/rawhtml.html', imagetexttemplate % ('http://img.skitch.com/20090612-8cc11y7kpts6ms6serry316pk2.jpg', "<br/><br/><font color='red'><b>Bomberman, FTW</b></font><br/><br/>")),
        'poopypants' : ('searchhelper/rawhtml.html', asciitexttemplate % professorpoopypants),
        'credits' : credits,
        'about' : credits
        }
    result = None
    comm = shutils.getLastCommand(search, None)
    if comm != None:
        lastcommand, arg = comm
        result = eastermapping.get(lastcommand, None)
    return result

    
    
    
if __name__ == '__main__':

    def unit_test():
        import sys

        sessionKey = splunk.auth.getSessionKey('admin', 'changeme')
        try:
            cherrypy.session['sessionKey'] = sessionKey
        except AttributeError:
            setattr(cherrypy, 'session', {})
            cherrypy.session['sessionKey'] = sessionKey
        cherrypy.session['user'] = { 'name': 'admin' }
        cherrypy.config['module_dir'] = '/'
        cherrypy.config['build_number'] = '123'
        cherrypy.request.lang = 'en-US'

        # roflcon
        class elvis(object):
            def ugettext(self, msg):
                return msg
        cherrypy.request.t = elvis()
        # END roflcon

        shc = SearchHelperController()

        argc = len(sys.argv)
        if argc == 2:
            query = sys.argv[1]
            print(shc.index(search=query, snippet=True, minimize=False))
        else:
            print("Usage: %s 'search'" % sys.argv[0])


    unit_test()
