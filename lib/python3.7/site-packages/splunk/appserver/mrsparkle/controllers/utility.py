import datetime
import json
import logging
import cherrypy
from splunk.appserver.mrsparkle import MIME_TEXT
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.decorators import set_cache_level
from splunk.appserver.mrsparkle.lib.routes import route

import splunk.util
from splunk.appserver.mrsparkle.lib import i18n
from splunk.appserver.mrsparkle.lib import times

logger = logging.getLogger('splunk.appserver.controllers.util')


class UtilityController(BaseController):
    '''
    General utilities
    /util
    '''


    @route('/:log/:js')
    @expose_page(must_login=False, methods='POST')
    def log_js(self, log, js, data='[]', **args):
        '''
        Provides javascript logging service.
        
        Args:
            
            data: A JSON encoded collection of JavaScript log messages to process.  Default is an empty collection.

        '''
        out = {'events_logged': "0"}
        # non-logged in users cannot write to disk
        if cherrypy.session.get('sessionKey', None) is None:
            return self.render_json(out)
        cherrypy.session.release_lock()

        try:
            logs = json.loads(data)
        except Exception as e:
            logger.error("Could not parse json from javascript logger. Data set was:\n %s" % data)
            return self.render_json(out)
        successCount = 0;
        for item in logs:
            event = []
            event.append('name=javascript')
            event.append('class=%s' % item.get('class', 'undefined'))
            event.append('%s' % item.get('message', ''))
            eventFormat = ", ".join(event);
            try:
                logLevel = item.get('level', 'info')
                if logLevel == 'log':
                    logLevel = 'info'
                getattr(logger, logLevel)(eventFormat)
                successCount = successCount + 1
            except Exception as e:
                logger.error("Could not log javascript event. Event was:\n%s" % eventFormat)
        out['events_logged'] = str(successCount)
        return self.render_json(out)


    #
    # time-related utilities
    # all hosted under /util/time
    #


    @route('/:m=time/:n=zoneinfo/:tz')
    @set_cache_level('always')
    @expose_page(must_login=False)
    def get_tztable(self, tz, **unused):
        '''
        Returns the Olsen database entries for the current server timezone.
        
        The 'tz' parameter is required for caching purposes.  It is not
        actually used.
        
        /util/time/zoneinfo/<SOME_TZ_LABEL>
        '''
        
        cherrypy.response.headers['content-type'] = MIME_TEXT
        
        try:
            return times.getServerZoneinfo()
        except Exception as e:
            logger.exception(e)
            return ''



    @route('/:m=time/:n=parser')
    @set_cache_level('never')
    @expose_page(must_login=False)
    def parse_time(self, ts, date_format='medium', time_format='medium', **unused):
        '''
        Returns a JSON structure of unix timestamps translated into both
        ISO-8601 format and a localized string.
        
        ts:
            one or more unix timestamps or relative time identifiers
            
        date_format:
            short - 10/17/09
            medium - Oct 17, 2009
            long - October 17, 2009
            
        time_format:
            short - 3:49 PM
            medium - 3:49:33.000 PM
            long - 3:49:40.000 PM -0700
        '''

        try:
             parsed = times.splunktime2Iso(ts)
        except Exception as e:
            logger.exception(e)
            return '{}'
            
        output = {}
        
        for key in parsed:
            
            localizedargs = {
                'dt': splunk.util.parseISO(parsed[key]),
                'date_base_format': date_format,
                'time_base_format': time_format
            }
                
            output[key] = {
                'iso': parsed[key],
                'localized': i18n.format_datetime_microseconds(**localizedargs)
            }
            
        return self.render_json(output)


