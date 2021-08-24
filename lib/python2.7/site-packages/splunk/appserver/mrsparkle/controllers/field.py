# coding=UTF-8
from __future__ import absolute_import
from __future__ import division
from past.utils import old_div
from builtins import object
import fnmatch
import cherrypy
import logging
import re
import splunk.search

from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.decorators import ONLY_API
from splunk.appserver.mrsparkle.lib.decorators import set_cache_level
from splunk.appserver.mrsparkle.lib.routes import route

from splunk.appserver.mrsparkle.lib.jsonresponse import JsonResponse
import splunk.appserver.mrsparkle.lib.util as util
import splunk.util
SUMMARY_HTML_TEMPLATE = 'field/summary.html'
SUMMARY_COUNT_CONSTRAINT = 10

logger = logging.getLogger('splunk.appserver.controllers.field')

class FieldAction(object):
    '''Base class for the field action types.'''

    def __init__(self, field_action, fields, special_params):
        self.field_action = field_action
        self.fields = fields
        self.special_params = special_params

    def replaceVars(self, string, decs=None):
        '''
        Given a string, find the variables in it and replace
        them with values from the event.
        '''

        # Start by allowing any field to insert its value without the decorator escaping.
        # Use at your own risk!
        string = util.replace_vars(string, self.fields, open_delimiter="$!", retain_escape=True)

        # Replace any special variables
        string = util.replace_vars(string, self.special_params, decorators=decs, open_delimiter="$@", retain_escape=True)

        # Replace the regular fields
        string = util.replace_vars(string, self.fields, decorators=decs, default="")

        return string

    def generate(self):
        '''
        This method should be overridden for each subclass.
        It should return a simple Python dict that represents
        the output for that field action type.

        It is called internally by the generate() method.
        '''
        return {}


class LinkFieldAction(FieldAction):

    def generate(self):
        response = {
            'type': 'link',
            'name': self.field_action.name,
            'label': _(self.replaceVars(self.field_action['label'])),
            'link.method': 'GET',
            'link.target': self.field_action.get('link.target') or '_blank'
        }

        link_uri = self.field_action.get('link.uri')
        if link_uri == None:
            logger.warn('The link field action requires the link.uri property be set.')
            return None

        schema_rex = re.compile(r'^[A-Za-z]+://.')
        try:
            raw_link = self.replaceVars(link_uri, splunk.util.safeURLQuote)
            if schema_rex.search(raw_link):
                response['link.uri'] = raw_link
            else:
                response['link.uri'] = util.make_url(raw_link)
        except:
            logger.warn('Could not generate work flow action url, check for illegal characters in URI: %s' % link_uri)
            return None

        # normalize the link.target input, just in case we're getting poorly migrated 3.x field actions.
        if response['link.target'] not in ['blank', '_blank', 'self', '_self']:
            response['link.target'] = '_blank'

        if not response['link.target'].startswith('_'):
            response['link.target'] = '_' + response['link.target']

        # Handle all the optional fields
        if 'link.method' in self.field_action and self.field_action['link.method'].upper() != 'GET':
            response['link.method'] = self.field_action['link.method'].upper()

        # Add post args
        if response['link.method'] == 'POST':

            # Provide a default payload, there is no obligation to create a POST body
            # so empty string should be sufficient.
            response['link.payload'] = ''

            # Generate the payload for post args
            payload = {}
            for key in self.field_action:
                if key.startswith('link.postargs'):
                    parts = key.split('.')

                    # ensure the postargs have at least 4 parts
                    # 0: link
                    # 1: postargs
                    # 2: number
                    # 3: key
                    if len(parts) < 4:
                        continue

                    payload[self.replaceVars(parts[3])] = self.replaceVars(self.field_action[key])

            response['link.payload'] = payload

        return response

class SearchFieldAction(FieldAction):

    DEFAULT_APP  = 'search'
    DEFAULT_VIEW = 'flashtimeline'

    def escape_search_term(self, term):
        return splunk.util.toUnicode(term).replace('\\', '\\\\')

    def generate(self):
        response = {
            'type': 'search',
            'name': self.field_action.name,
            'label': _(self.replaceVars(self.field_action['label'])),
            'search.target': self.field_action.get('search.target') or '_blank'
        }

        search_string = self.field_action.get('search.search_string')
        if search_string == None:
            logger.warn('The search field action requires the search.search_string property be set.')
            return None

        # normalize the search.target input, just in case we're getting poorly migrated 3.x field actions.
        if response['search.target'] not in ['blank', '_blank', 'self', '_self']:
            response['search.target'] = '_blank'

        if not response['search.target'].startswith('_'):
            response['search.target'] = '_' + response['search.target']

        response['search.search_string'] = self.replaceVars(self.field_action.get('search.search_string'), self.escape_search_term)
        response['search.app'] = self.field_action.get('search.app') or self.special_params.get('namespace') or SearchFieldAction.DEFAULT_APP
        response['search.view'] = self.field_action.get('search.view') or self.special_params.get('view') or SearchFieldAction.DEFAULT_VIEW

        # Handle various time configurations
        preserve_timerange = self.field_action.get('search.preserve_timerange', False)
        earliest = self.field_action.get('search.earliest', None)
        latest = self.field_action.get('search.latest', None)

        if earliest != None:
            response['search.earliest'] = earliest

        if latest != None:
            response['search.latest'] = latest

        if preserve_timerange:
            response['search.preserve_timerange'] = preserve_timerange

        return response

fieldActions = {
    'link': LinkFieldAction,
    'search': SearchFieldAction
}

class FieldController(BaseController):

    @route('/:action=summary/:sid/:field_name')
    @expose_page(must_login=True, methods='GET')
    def summary(self, action, sid, field_name, count=None, **args):
        '''
        Field Summary

        Arg:

        action: The current action
        field: The field to retrieve summary data from
        sid: The job search id
        count: The summary count constraint, 0 defaults to SUMMARY_COUNT_CONSTRAINT
        '''
        error = None
        if field_name is None:
            error = _('The field name is missing. Splunk could not retrieve field summary data.')
        elif sid is None:
            error = _('The job id is missing. Splunk could not retrieve field summary data.')
        else:
            try:
                job = splunk.search.getJob(sid)
            except splunk.ResourceNotFound as e:
                logger.error(e)
                error = _('The job appears to have expired or is invalid. Splunk could not retrieve field summary data.')
            except Exception as e:
                logger.error(e)
                error = _('An error occurred. Splunk could not retrieve field summary data.')
            if error:
                return self.render_template(SUMMARY_HTML_TEMPLATE, {'error': error})
            if isinstance(field_name, str):
                field_name = field_name.decode('utf-8')
            field_summary = job.summary.fields.get(field_name, None)
            if field_summary is None:
                return self.render_template(SUMMARY_HTML_TEMPLATE, {'error': _('No summary information exists for field_name %s') % field_name})
            if count is None:
                count = SUMMARY_COUNT_CONSTRAINT
            else:
                count = min(int(count), SUMMARY_COUNT_CONSTRAINT)
                #0 value delimits everything up to constraint
                if count is 0:
                    count = SUMMARY_COUNT_CONSTRAINT
            field_frequency = field_summary.get('count')/float(job.summary.count)
            field_primarily_numeric = field_summary.get('numericCount')>old_div(field_summary.get('count'),2)
            numerical_reports = [
                { 'label': _('average over time'), 'intention': {'name': 'plot', 'arg': {'mode': 'timechart', 'fields': [['avg', field_name]]}}, "reportSearch": 'timechart avg("%s")' % field_name, "chartType": "line" },
                { 'label': _('maximum over time'), 'intention': {'name': 'plot', 'arg': {'mode': 'timechart', 'fields': [['max', field_name]]}}, "reportSearch": 'timechart max("%s")' % field_name, "chartType": "line" },
                { 'label': _('minimum over time'), 'intention': {'name': 'plot', 'arg': {'mode': 'timechart', 'fields': [['min', field_name]]}}, "reportSearch": 'timechart min("%s")' % field_name, "chartType": "line" },
            ]
            categorical_reports = [
                { 'label': _('top values by time'), 'intention': {"name": "plot", "arg": {"mode": "timechart", "fields": [["count", "__events"]], "splitby": field_name}}, "reportSearch": "timechart count by %s" % field_name, "chartType": "line" },
                { 'label': _('top values overall'), 'intention': {"name": "plot", "arg": {"mode": "top", "limit": 10000, "fields": [field_name]}}, "reportSearch": "top limit=10000 %s" % field_name, "chartType": "bar" }
            ]
            template_args = {
                'error': error,
                'field_name': field_name,
                'field_summary':field_summary,
                'field_frequency': field_frequency,
                'field_primarily_numeric': field_primarily_numeric,
                'numerical_reports': numerical_reports,
                'categorical_reports': categorical_reports,
                'count': count
            }
            return self.render_template(SUMMARY_HTML_TEMPLATE, template_args)


    @route('/:actions=actions/:namespace/:sid/:offset')
    @expose_page(must_login=True, handle_api=ONLY_API, methods='GET')
    @set_cache_level('etag')
    def field_actions(self, actions, namespace, sid, offset, field_name=None, field_value=None, latest_time=None, view=None, **args):
        '''
        Returns a set of field action response for a given field or event.

        Assumptions:
            1) If field_name and field_value are provided, the data structure
               returned is representative of the single field.

            2) If either both field_name and field_value are absent, the data structure
               returned is assumed to be for the entire event.
        '''

        # These map to the workflow_actions.conf spec, just to simplify changes in the spec
        FA_CONF = '/data/ui/workflow-actions'
        FA_TYPE = 'type'
        FA_LABEL = 'label'
        FA_FIELDS = 'fields'
        FA_EVENTTYPES = 'eventtypes'
        FA_DISPLAY_LOCATION = 'display_location'
        FA_DISPLAY_LOCATION_FIELD_MENU = 'field_menu'
        FA_DISPLAY_LOCATION_EVENT_MENU = 'event_menu'
        FA_DISPLAY_LOCATION_BOTH = 'both'
        FA_DISPLAY_LOCATION_DEFAULT = FA_DISPLAY_LOCATION_BOTH

        # This ensures that only enabled field actions are retrieved
        FA_FIELD_ACTION_SEARCH = "disabled=0"

        EVENTTYPE_FIELD_NAME = 'eventtype'

        resp = JsonResponse()

        try:
            offset = int(offset)
        except ValueError as e:
            msg = _("The job's event offset must be a valid integer in order to generate field actions.")
            logger.error(msg)
            resp.addError(msg)
            return self.render_json(resp)

        try:
            job = splunk.search.getJob(sid)
        except splunk.ResourceNotFound as e:
            msg = _("While generating field actions, could not find a job with an sid = %s." % sid)
            logger.error(msg)
            resp.addError(msg)
            return self.render_json(resp)

        try:
            if "maxLines" in args:
                job.setFetchOption(maxLines=args["maxLines"])
            event = job.events[offset]
        except IndexError as e:
            msg = _("While generating field actions, could not find an event at the offset %(event_offset)s for the job with an sid = %(sid)s." % {'sid': sid, 'event_offset': offset})
            logger.error(msg)
            resp.addError(msg)
            return self.render_json(resp)

        try:
            field_actions = splunk.entity.getEntities(FA_CONF, namespace=namespace, owner=cherrypy.session['user'].get('name'), search=FA_FIELD_ACTION_SEARCH, count=-1)
        except splunk.ResourceNotFound as e:
            msg = _("The field actions configuration could not be found.")
            logger.error(msg)
            resp.addError(msg)
            return self.render_json(resp)

        # We retain a reference to the list so we can sort it later
        # if we have globbers
        event_field_names_list = event.fields
        event_field_names = set(event_field_names_list)

        # If you're smoking crack, you're whack
        if field_name != None and field_name not in event_field_names:
            msg = _("The field %s could not be found in the chosen event." % field_name)
            logger.error(msg)
            resp.addError(msg)
            return self.render_json(resp)

        # Generate the list of event fields and their values based on what field was requested.
        # This is calculated once and is what is passed to the field actions if any match this event.
        event_field_values = {}
        for event_field_name in event_field_names_list:
            event_field = event.fields[event_field_name]

            if field_name and field_value and event_field_name == field_name:
                event_field_values[event_field_name] = field_value

            elif isinstance(event_field, splunk.search.ResultField) and len(event_field) > 1:
                event_field_values[event_field_name] = splunk.util.unicode(event_field[0])

            else:
                event_field_values[event_field_name] =splunk.util.unicode(event_field)

        resp.data = []
        for fa_name, field_action in field_actions.items():

            # The general strategy here is to eliminate field actions
            # as fast as possible and leave the heaviest lifting for the
            # very end and only if necessary.

            fa_type = field_action.get(FA_TYPE)
            if fa_type == None:
                logger.warn("The field action %s was not given a type and will not be processed." % fa_name)
                continue

            if field_action.get(FA_LABEL) == None:
                logger.warn("The field action %s was not given a label and will not be processed." % fa_name)
                continue

            fa_display_location = field_action.get(FA_DISPLAY_LOCATION, FA_DISPLAY_LOCATION_DEFAULT)

            # Skip the field action if it's only for event menus and a
            # specific field's menu has been requested.

            if field_name != None and fa_display_location.lower() == FA_DISPLAY_LOCATION_EVENT_MENU:
                continue

            # Skip the field action if no field has been specified but
            # the field action should only apply to field menus.
            if field_name == None and fa_display_location.lower() == FA_DISPLAY_LOCATION_FIELD_MENU:
                continue

            # Look for eventtypes if defined
            fa_eventtypes = field_action.get(FA_EVENTTYPES)
            if fa_eventtypes != None:
                fa_eventtypes = set(splunk.util.stringToFieldList(fa_eventtypes))
                if len(fa_eventtypes) > 0:
                    if EVENTTYPE_FIELD_NAME not in event_field_names:
                        continue
                    else:
                        event_eventtypes = set(splunk.util.stringToFieldList(splunk.util.unicode(event.fields[EVENTTYPE_FIELD_NAME])))
                        if not (fa_eventtypes <= event_eventtypes):
                            globbers = [eventype for eventype in fa_eventtypes if '*' in eventype]

                            if not ((fa_eventtypes - set(globbers)) <= event_eventtypes):
                                continue

                            found_all_globbers = True
                            for globber in globbers:
                                matched_globber = False
                                for event_eventype in event_eventtypes:
                                    if fnmatch.fnmatch(event_eventype, globber):
                                        matched_globber = True
                                        break
                                if not matched_globber:
                                    found_all_globbers = False
                                    break

                            if not found_all_globbers:
                                continue

            # If fields is undefined, then assume this applies to everything (*)
            fa_fields_string = field_action.get(FA_FIELDS) or '*'
            fa_fields = set(splunk.util.stringToFieldList(fa_fields_string))

            # If we have a field name we assume the field's specific menu is being requested.
            # Here we do some optimistic checking to make sure the field name matches the
            # field action's fields list before checking against the event itself.
            if field_name != None:

                if '*' not in fa_fields:

                    # Base case, no globbers
                    if field_name not in fa_fields and '*' not in fa_fields_string:
                        continue

                    # Have globbers
                    elif '*' in fa_fields_string:
                        globbers = [field for field in fa_fields if '*' in field]
                        field_name_found = False
                        for globber in globbers:
                            if fnmatch.fnmatch(field_name, globber):
                                field_name_found = True
                                break
                        if not field_name_found:
                            continue

            # Now we start matching the fields list against the actual event.
            # If '*' is in the fields, or the event_field_names are inclusive of the
            # fields we must process the field action.
            if '*' not in fa_fields and not (fa_fields <= event_field_names):

                # Note the additional search for * seems redundant but we are
                # searchting the original fields string and thus will
                # actually find globbers like "client*", "*_ip", etc.
                if '*' not in fa_fields_string:
                    continue

                # If we've gotten here it means we have globbers in our matchfields list
                else:
                    globbers = [field for field in fa_fields if '*' in field]

                    # Test the set of non-globbers against the event_field_names set,
                    # if it is not inclusive, this FA fails before doing the globbing.
                    if not ((fa_fields - set(globbers)) <= event_field_names):
                        continue

                    # Start the heavy lifting...
                    # First we do an alpha sort to attempt to minimize the number of loops
                    globbers.sort()
                    event_field_names_list = sorted(event_field_names_list)

                    # Iterate through each globber and event field attemtping to match the globber
                    # to the an event field.  Optimistically stop iterating if even one of the globbers
                    # doesn't match. There are less loopy ways to do this, but it doesn't seem
                    # to incure much overhead, as the globber list is minimized.
                    found_all_globbers = True
                    for globber in globbers:
                        matched_globber = False
                        for event_field_name in event_field_names_list:
                            if fnmatch.fnmatch(event_field_name, globber):
                                matched_globber = True
                                break
                        if not matched_globber:
                            found_all_globbers = False
                            break

                    if not found_all_globbers:
                        continue

            # Construct the default payload for the field action renderers
            # This allows them to render @fieldname, @namespace, @sid, etc
            special_params = {
                'namespace': namespace,
                'view': view,
                'sid': sid,
                'offset': offset,
                'latest_time': latest_time or '',
                'field_name': field_name or '',
                'field_value': field_value or ''
            }

            try:
                fa = fieldActions[fa_type](field_action, event_field_values, special_params)
                parsed = fa.generate()
                if parsed != None:
                    resp.data.append(parsed)
            except KeyError as e:
                logger.error("Could not find the field action type \"%s\" in the loaded field actions." % fa_type)

        # Sort the returned list by label
        resp.data = sorted(resp.data, key=lambda x: x['label'])
        return self.render_json(resp)
