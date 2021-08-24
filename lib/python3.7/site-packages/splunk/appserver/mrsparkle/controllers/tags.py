# coding=UTF-8
import logging

import cherrypy

import splunk
import splunk.auth
import splunk.entity
import splunk.util
import splunk.appserver.mrsparkle # bulk edit
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
import splunk.appserver.mrsparkle.lib.util as util
from splunk.appserver.mrsparkle.lib.routes import route

from splunk.appserver.mrsparkle.lib.util import DeferCall

logger = logging.getLogger('splunk.appserver.controllers.tags')

ERROR_FAIL_UPDATE = DeferCall(_, 'Could not update/create tags for the specified field/value set.')
ERROR_FAIL_GET = DeferCall(_, 'Could not retrieve tags for the specified field/value set.')
TAG_DELIMITER = '::'
ADD_DELETE_DELIMITER = ' '

class TagsController(BaseController):

    @route('/:app/:fields=fields/:field_name/:field_value', methods='POST')
    @expose_page(must_login=True, methods=['POST'])
    def set_field_tags(self, app, fields, field_name, field_value, add='', delete='', **args):
        '''
        Edits the tags associated with a :field_name/:field_value. The :field_value parameter specifies
        the specific value on which to bind tag actions. Multiple tags can be attached by passing a space
        separated add or delete parameters. The server will process all of the adds first, and then deletes.
        '''
        error = None
        uri = self.get_uri(app, field_name)
        add = add.replace('"', '\\"') # splunkd supports /a-z0-9/gi only, escape double quotes for splunk.util.stringToFieldList
        add = splunk.util.stringToFieldList(add)
        old = set(splunk.util.stringToFieldList(delete))
        new = set(add)
        delete = list(old.difference(new))
        postargs = {}

        postargs['value'] = field_value #should be field_value
        postargs['add'] = add
        postargs['delete'] = delete
        try:
            serverResponse, serverContent = splunk.rest.simpleRequest(uri, postargs=postargs)
        except Exception as e:
            cherrypy.response.status = 400
            error = ERROR_FAIL_UPDATE
        if error is None and serverResponse.status not in [200, 201]:
            cherrypy.response.status = 400
            error = ERROR_FAIL_UPDATE

        template_args = self.get_template_args(app, field_name, field_value, error)
        return self.render_template('tags/get_field_tags.html', template_args)

    # parse <field-value>::<tag-name>, last :: is used as delimiter
    def parse_tag(self, title):
        last  = title.rfind(TAG_DELIMITER)
        if last == -1:
            return ['', '']
        return [ title[0:last], title[last+len(TAG_DELIMITER):] ]


    @route('/:app/:fields=fields/:field_name/:field_value', methods='GET')
    @expose_page(must_login=True, methods=['GET'])
    def get_field_tags(self, app, fields, field_name, field_value, **args):
        template_args = self.get_template_args(app, field_name, field_value)
        return self.render_template('tags/get_field_tags.html', template_args)

    def get_template_args(self, app, field_name, field_value, error=None):
        uri = self.get_uri(app, field_name)
        tags = []

        if error is None:
            try:
                serverResponse, serverContent = splunk.rest.simpleRequest(uri)
            except Exception as e:
                error = ERROR_FAIL_GET

        if error is None and serverResponse.status not in [200, 201]:
            error = ERROR_FAIL_GET
        else:
            atomFeed = splunk.rest.format.parseFeedDocument(serverContent)
            for x in atomFeed.entries:
               kv = self.parse_tag(x.title)
               if kv[0] == field_value:
                  tags.append(kv[1])

        template_args = {
            'action': self.get_action(app, field_name, field_value),
            'field_name': field_name,
            'field_value': field_value,
            'tags': tags,
            'error': error,
            'is_xhr': util.is_xhr()
        }
        return template_args

    def get_uri(self, app, field_name):
        '''
        Retrieve the owner/app related endpoint URI
        '''
        uri = None
        entity_class = '/search/fields/%s/tags' % splunk.util.safeURLQuote(field_name)
        uri = splunk.entity.buildEndpoint(entity_class, namespace=app, owner=splunk.auth.getCurrentUser()['name'])
        return uri

    def get_action(self, app, field_name, field_value):
        '''
        Retrieve a safe action uri that is correctly escaped, UTF8 safe and processed via make_url.
        '''
        return self.make_url(['/tags', app, 'fields', splunk.util.safeURLQuote(field_name, ""), splunk.util.safeURLQuote(field_value, "")])
