# coding=UTF-8
from __future__ import absolute_import

import cherrypy
import logging
import splunk
import splunk.entity
import splunk.util
import splunk.appserver.mrsparkle # bulk edit
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.decorators import ONLY_API
from splunk.appserver.mrsparkle.lib.decorators import set_cache_level
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib import message

from splunk.appserver.mrsparkle.lib.jsonresponse import JsonResponse
from splunk.appserver.mrsparkle.lib.i18n import deferred_ugettext
from splunk.models.message import Message

from splunk.appserver.mrsparkle.lib.msg_pool import MsgPoolMgr, UI_MSG_POOL
import json

logger = logging.getLogger('splunk.appserver.controllers.messages')

class MessagesController(BaseController):
    # Map select splunkd messages to UI messages
    msg_map = {
        # use deferred_ugettext() to ensure the string is translated on demand during a user request as we don't know what language they'll want at this point
        'Splunk must be restarted for changes to take effect.':  deferred_ugettext('Splunk must be restarted for changes to take effect.  [[/manager/search/control|Click here to restart from Server controls]].')
    }

    @route('/:action=uipool')
    @expose_page(must_login=True, handle_api=ONLY_API, methods='GET')
    @set_cache_level('etag')
    def uipool(self, action, **args):

        # unauthed calls get nothing
        if not cherrypy.session.get('sessionKey'):
            return '/* unauthorized */'

        return self.render_json(MsgPoolMgr.get_poolmgr_instance()[UI_MSG_POOL].list())

    @expose_page(must_login=True, handle_api=ONLY_API, methods='GET')
    def uiindex(self, **kwargs):
        '''
        JSONResponse envelope of message data.
        '''
        resp = JsonResponse()

        try:
            msg = MsgPoolMgr.get_poolmgr_instance()[UI_MSG_POOL].pop(kwargs['id'])

            if msg:
                resp.addMessage(msg.severity.upper(), msg.text)

        except splunk.SplunkdConnectionException as e:
            logger.exception(e)
            resp.success = False
            resp.addFatal(_('The appserver was unable to connect to splunkd. Check if splunkd is still running. (%s)') % e.args[0])

        except Exception as e:
            logger.exception(e)
            resp.success = False
            resp.addError(e)
                
        return self.render_json(resp)

    @route('/:action=delete')
    @expose_page(must_login=True, handle_api=ONLY_API, methods='POST')
    def delete_message(self, action, **params):
        message = Message.get(params.get('message_id'))
        message.delete()
 
    @route('/:action=index')
    @expose_page(must_login=True, handle_api=ONLY_API, methods='GET')
    @set_cache_level('never')
    def index(self, action, **args):
        '''
        JSONResponse envelope of message data.

        URL: /api/messages/index/
        '''
        resp = JsonResponse()
        uri = '/messages'
        try:
            entries = splunk.entity.getEntities(uri)
            msgs = message.get_session_queue().get_all()

            # Collect all reasons that a restart is required.
            restart_reason = ''
            for idx, entry in list(entries.items()):
                if idx.startswith('restart_required_reason'):
                    restart_reason += ' '
                    restart_reason += str(entry[idx])
                    # Remove individual reason message.
                    del entries[idx]

            for idx, entry in entries.items():
                mapped_msg = self.msg_map.get(entry[idx], entry[idx])
                if (idx == 'restart_required') and (len(restart_reason) > 0):
                    # Combine restart_required and restart_required_reason(s)
                    mapped_msg += restart_reason
              
                # If this message is removable, then append an id 
                removeLink = entry.getLink('remove')
                if removeLink is not None: 
                    id = "/" + "/".join(entry.id.split('/')[3:])
                    resp.addWarn(mapped_msg, id=id)
                else: 
                    resp.addWarn(mapped_msg)
            
            for msg in msgs:
                resp.addMessage(msg['level'].upper(), msg['message'])

        except splunk.AuthenticationFailed as e:
            logger.debug('client not authenticated; no persistent messages retrieved')

        except splunk.SplunkdConnectionException as e:
            logger.exception(e)
            resp.success = False
            resp.addFatal(_('The appserver was unable to connect to splunkd. Check if splunkd is still running. (%s)') % e.args[0])

        except splunk.RESTException as e:
            logger.exception(e)
            resp.success = False
            resp.parseRESTException(e)
            
        except Exception as e:
            logger.exception(e)
            resp.success = False
            resp.addError(e)
                
        return self.render_json(resp)
