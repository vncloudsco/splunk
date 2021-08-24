from __future__ import absolute_import
from builtins import map

import cherrypy
import splunk
import splunk.util
from splunk.appserver.mrsparkle.list_helpers.generators import ListGeneratorController

SEARCH_JOIN_OPERATOR = ' | '
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.decorators import set_cache_level
from splunk.appserver.mrsparkle.lib.decorators import format_list_template
from splunk.appserver.mrsparkle.lib.decorators import normalize_list_params
from splunk.appserver.mrsparkle.lib.routes import route

class JobsListGenerator(ListGeneratorController):

    endpoint = 'jobs'
    
    @route('/:sid/:action=events')
    @expose_page(handle_api=True)
    @set_cache_level('never')
    @format_list_template()
    @normalize_list_params()
    def events(self, sid, action, **kw):
        '''Returns the events from a job in list format.'''
        job = self.__fetchAndPrepJob(sid, kw)
        return list(map(self.__cleanResponse, job.events[kw['offset']:kw['count']+kw['offset']]))

    @route('/:sid/:action=results')
    @expose_page(handle_api=True)
    @set_cache_level('never')
    @format_list_template()
    @normalize_list_params()
    def results(self, sid, action, **kw):
        '''Returns the results from a job in list format.'''
        job = self.__fetchAndPrepJob(sid, kw)
        return list(map(self.__cleanResponse, job.results[kw['offset']:kw['count']+kw['offset']]))
    
    def __fetchAndPrepJob(self, sid, kw):
        '''
        Handles getting the job safely and adding a sort.
        
        One caveat is the sorting implementation.  Sorting happens via the
        search parameter on the events/ results/ endpoint, thus if the user has
        specified a sort via the search syntax explicitly we respect that over
        the lists/ endpoint sort_key and sort_dir params.
        
        TODO: handle eventIsTruncated
        '''
        try:
            job = splunk.search.getJob(sid)
        except splunk.ResourceNotFound as e:
            raise cherrypy.HTTPError(status=404, message="Cannot find job '%s'." % sid)

        fetch_options = {}

        if len(fetch_options) > 0:
            job.setFetchOption(**fetch_options)

        has_search_sort = False
        search = fetch_options.get('search', False)
        if search:
            parts = search.split('|')
            for part in parts[1:]:
                if part.strip().startswith('sort'):
                    has_search_sort = True
            
        sort_key= kw.get('sort_key')
        
        if not has_search_sort and not sort_key == None:
            sort_dir = kw.get('sort_dir')
            sort = 'sort %s%s' % (self.normalizeSortDir(sort_dir), sort_key)
            if fetch_options.get('search', False):
                sort = SEARCH_JOIN_OPERATOR.join([fetch_options['search'], sort])
            job.setFetchOption(search=sort)
        
        return job

    def normalizeSortDir(self, sortDir):
        '''
        The jobs endpoint uses the search command on the splunkd events and results endpoints
        to preform sorts.  The search command requires the use of '-' signs to apply sorts
        so we have to normalize on asc and desc.
        '''
        sortDir = sortDir.lower()
        if not sortDir == 'desc' and not sortDir == 'asc':
            sortDir = self.SORT_DIR
        if sortDir == 'desc':
            return '-'
        return ''

    def __cleanResponse(self, result):
        '''Job events and results return a _raw object that json and other encoders cannot handle.'''
        dict_result = dict(result)
        if dict_result.get('_raw', False):
            dict_result['_raw'] = splunk.util.unicode(dict_result['_raw'])
        return dict_result
