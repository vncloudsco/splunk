from __future__ import absolute_import
import time
import json

import cherrypy

import splunk
import splunk.auth
import splunk.search
import splunk.search.Parser
import splunk.search.Transformer as xformer
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page

from splunk.search.TransformerUtil import INAME, IARG, IFLAGS

import logging
logger = logging.getLogger("splunk.appserver.controller.parser")


class ParserController(BaseController):
    """
    /parser
    """
    
    counter = 0
    
    def _failJSON(self, message):
        """ Create a dictionary that will be JSON''d and returned """
        failDict = {
            "success"  : False,
            "messages" : []
        }
        failDict['messages'].append(message)
        return self.render_json(failDict)

    @expose_page(methods='POST')
    def parse(self, q=None, intentions=None, namespace=None, owner=None):
        """
        EXAMPLE request:
 
        q=search foo bar&intentions=[
             {
                 "name" : "addterm",
                 "arg"       : "baz"
             },
             {
                 "name" : "toggleterm",
                 "arg"       : "quux"
             }
        ]
        """

        self.counter += 1
        sequence = str(time.time()) + '.' + str(self.counter)
        
        logger.debug("Parse/Apply Intentions: q: %s intentions: %s" % (q, intentions))

        try:
            
            if intentions is None:
                # just parse the search
                replacedIntentions = []
                parsedObj = splunk.search.Parser.parseSearch(
                    q, 
                    hostPath=self.splunkd_urlhost, 
                    sessionKey=cherrypy.session['sessionKey'],
                    namespace=namespace,
                    owner=owner
                )
            else:
                decodedIntentions = json.loads(intentions)
                # do the string replacement here.
                replacedQ, replacedIntentions = self._applyStringReplacement(q, decodedIntentions)
                parsedObj = self._parseAndApplyIntentions(replacedQ, replacedIntentions, namespace=namespace, owner=owner)

        except Exception as e:
            logger.exception(e)
            return self._failJSON( _("PARSER: Applying intentions failed %s" % str(e) ) )

        # return a JSON object
        logger.debug("SIZE OF INTENTION QUEUE: %s" % len(replacedIntentions) )
        if len(replacedIntentions) < 1:
            logger.debug("RAW JSONABLE %s" % parsedObj.rawJsonable() )
            return self.render_json(parsedObj.rawJsonable())

        return self.render_json(parsedObj.jsonable())


    @expose_page(methods=['POST', 'GET'])
    def decompose(self, q=None, namespace=None, owner=None):
        logger.debug("Decomposing intentions: %s" % q)

        try:
            parsedObj = splunk.search.Parser.parseSearch(
                q, 
                hostPath=self.splunkd_urlhost, 
                sessionKey=cherrypy.session['sessionKey'],
                namespace=namespace,
                owner=owner
            )
            decomposedSearch, intentions = xformer.decomposeSearch(namespace, owner, parsedObj, q)
            logger.debug("Decomposing intentions result search: %s intentions: %s" % (decomposedSearch, intentions))

        except Exception as e:
            return self._failJSON( _("PARSER: Unsupported search (%s): %s" % (q, e)))

        # return a JSON object
        return self.render_json({ "search" : str(decomposedSearch), "intentions": intentions})

    def _applyStringReplacement(self, q, intentions):
        REPLACE_INTENT_NAME = 'stringreplace'

        # find all string replacement intents
        replaceIntents = [intention for intention in intentions if intention[INAME] == REPLACE_INTENT_NAME]
        intentions     = [intention for intention in intentions if intention[INAME] != REPLACE_INTENT_NAME]

        for replacement in replaceIntents:
            for token, props in replacement.get('arg').items():
                default = props.get('default', None)
                value = props.get('value', None)
                prefix = props.get('prefix', '')
                suffix = props.get('suffix', '')
        
                if (not value or value == '') and default:
                    value = default

                if props.get('fillOnEmpty', False) and (value == None):
                    q = q.replace('$%s$' % token, '').strip()
                    continue

                if value != None:
                    replacement_str = prefix + value + suffix
                    q = q.replace('$%s$' % token, replacement_str).strip()

        return q, intentions

    def _parseAndApplyIntentions(self, q=None, intentions=None, namespace=None, owner=None):

        # first, try to parse the given search string
        parsedObj = splunk.search.Parser.parseSearch(
            q, 
            hostPath=self.splunkd_urlhost, 
            sessionKey=cherrypy.session['sessionKey'],
            namespace=namespace,
            owner=owner
        )

        # walk through the transform stack
        for intention in intentions:
            if intention[INAME] not in ["", None]:
                intentName = intention[INAME]
                intentArg = intention.get(IARG, {} )
                intentFlags = intention.get(IFLAGS, None )
                parsedObj = xformer.applyIntention(namespace, owner, parsedObj, intentName, intentArg, intentFlags)
        return parsedObj

    # tests have moved to ../test/test_string_replacement.py
