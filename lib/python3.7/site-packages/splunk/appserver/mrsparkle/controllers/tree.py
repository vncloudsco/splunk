import re
import cherrypy
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

import logging

from future.moves.urllib import parse as urllib_parse

import splunk
import splunk.util as util
import splunk.entity as en

logger = logging.getLogger('splunk.appserver.controllers.tree')

class TreeController(BaseController):
    '''   /tree    '''

    @route('/')
    @expose_page(must_login=True)
    def index(self, **kwargs):
        '''
        Displays a tree view
        
        Arguments:
        eai_path      - (Optional) Path of the source endpoint (ex: admin/win-ad-explorer); (Required if using eai_proxy)
        proxy_path    - (Optional) Path of the proxy endpoint, by default tree/eai_proxy translating xml response into json.
        count         - (Optional) Maximum number of nodes requested per click.
        selected_text - (Optional) Text in the bottom preceeding the selected path.
        '''
        
        
        errors = []
        proxy_path = ''
        selected_text = ''
        
        if not 'proxy_path' in kwargs and not 'eai_path' in kwargs:
            errors.append(_('No source specified for the treeview.'))
        else:
            # Per SPL-135538: only allow same-origin links
            proxy_path = kwargs.pop('proxy_path', 'tree/eai_proxy')
            proxy_path = re.sub(r'^.*[/\\][\s/\\]+', '', proxy_path)
            selected_text = kwargs.pop('selected_text', _('Selected path: '))

        # cleanse input
        for key in kwargs:
            kwargs[key] = urllib_parse.quote(kwargs[key].strip())

        templateArgs = {'proxy_path'        : proxy_path,
                        'selected_text'     : selected_text,
                        'start_node'        : kwargs.pop('start_node', '').strip(),
                        'separate_children' : util.normalizeBoolean(kwargs.pop('separate_children', False)),
                        'data_args'         : kwargs,
                        'errors'            : errors
                        }
        return self.render_template('/view/tree.html', templateArgs)
        
        
    @route('/:proxy=eai_proxy')
    @expose_page(must_login=True)
    def eai_proxy(self, proxy, root, eai_path, **kwargs):
        '''
        Provides an eai adapter for treeview.js
        '''
        if not eai_path:
            raise cherrypy.HTTPError(404, _('eai_path argument is missing when calling tree/eai_proxy endpoint'))
        
        if not 'count' in kwargs:
            kwargs['count'] = 100
            
        kwargs.pop('_', '') # ignore anti-caching jQuery arg
        
        selectionMode = 0
        try:
            selectionMode = int(kwargs.pop('selection_mode', 0))
        except ValueError:
            pass
        
        root = (root or '').strip().replace('/', '%2F')
        
        output = None
        data, err = self.get_data(eai_path, root, **kwargs)
        if data:
            output = self.build_response(data, selectionMode)
        if err:
            output = self.add_error(output, err)
        
        return self.render_json(output)
    
    def get_data(self, eai_path, root, msg=None, **kwargs):
        entity_path = eai_path
        if len(root) > 0:
            entity_path = '/'.join([eai_path, root])
            
        try:
            entities = en.getEntities(entity_path, **kwargs)
            
        except splunk.RESTException as e:
            if e.statusCode == 401:
                err = _('Client is not authenticated.')
                return (None, (err, 400))
                
            elif e.statusCode == 403:
                err = _('You are not authorized to perform this action.')
                return (None, (err, 400))
                
            else: 
                err = _('Unable to open the selected path. Path doesn\'t exist or access is denied.')
                if not msg and len(root)>0:
                    # return error and the root nodes
                    logger.warn('%s %s' % (err, e.get_extended_message_text()))
                    return self.get_data(eai_path, '', msg=err, **kwargs)
                else:                     
                    # if root node can't be accessed, just display the message
                    return (None, err)
                
        except Exception as e:
            err = _('Unable to open the selected path.')
            logger.warn(err)
            return (None, (err, 500))
            
        return (entities, msg)
    
    def build_response(self, entities, selectionMode=None):
        output = jsonresponse.JsonResponse()
        output.count = entities.itemsPerPage
        output.offset = entities.offset
        output.total = entities.totalResults
        output.data = []
        
        if entities:
            if len(entities) == 1 and not list(entities.values())[0].get('name'):
                # empty node
                return output
            
            blocks = []
            for ent in list(entities.values()):
                hasChildren = util.normalizeBoolean(ent.get('hasSubNodes', True))
                block = {'text': ent.get('name', ent.name), 
                         'fileSize': ent.get('fileSize'), 
                         'id': ent.name, 
                         'hasChildren': hasChildren, 
                         'classes': 'nonleaf' if hasChildren else 'leaf',
                         'selectable': self.is_selectable(ent, selectionMode)
                        }
                blocks.append(block)
            output.data = sorted(blocks, key=lambda block: block['text'].lower())
            
        return output
    
    def add_error(self, output, error):
        status = None
        if not error: return output
        
        if not output:
            output = jsonresponse.JsonResponse()
            output.data = []
        if isinstance(error, tuple):
            status = error[1]
            error = error[0]
            
        if status:
            cherrypy.response.status = status
        output.success = False
        output.addError(error)
        
        return output
        
        
    def is_selectable(self, ent, selectionMode):
        hasChildren = util.normalizeBoolean(ent.get('hasSubNodes', True))

        if selectionMode == 1:
            return hasChildren
        elif selectionMode == 2:
            return not hasChildren
        else: 
            return True
