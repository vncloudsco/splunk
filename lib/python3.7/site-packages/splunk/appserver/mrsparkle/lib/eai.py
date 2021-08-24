import logging
import splunk.entity as en
import splunk.util
import splunk.rest as rest
import json
from splunk import auth
from splunk.appserver.mrsparkle.lib import util

logger = logging.getLogger('splunk.appserver.lib.eai')

class EAIFetchError(Exception): 
    pass

def dynfilter(val, context=None):
    if isinstance(val, dict):
        return DynamicUIHelper(val, __context=context)
    if isinstance(val, list):
        return DynamicUIHelperList(val, __context=context)
    return val

class DynamicUIHelper(dict):
    """
    This class is used by controllers/admin.py to wrap the uiHelper dictionary to add
    dynamic behaviour to the static dictionary.

    Methods added to this class can either override a value, or act as a fallback if a key
    doesn't exist in the underlying dictionary.

    Upon getting a request for a key, this code will:
    1) see if a method called pre_<key>() is defined - if so, the value it returns is returned
    instead of the value from the dictionary
    2) see if the dictionary contains the requested key - if so it's returned
    3) see if a method called post_<key>() is defined - if so, the  value it returns is returned
    instead of raising a KeyError exception

    Any dictionaries that would be returned are themselves wrapped in this class.
    Any lists that would be returned are wrapped in by DynamicUIHelperList so that the dynamic
    behaviour is preserved throughout the entire tree.
    """
    def __init__(self, *a, **kw):
        # some splunkSource entries are constructed dynamically from values contained in context
        if '__context' in kw:
            self._context = kw['__context']
            del kw['__context']
        else:
            self._context = {}
        super(DynamicUIHelper, self).__init__(*a, **kw)
            
    def __getitem__(self, key):
        if hasattr(self, 'pre_%s' % key):
            return getattr(self, 'pre_%s' % key)(key)
        try:
            return dynfilter(dict.__getitem__(self, key), context=self._context)
        except KeyError as e:
            try:
                return getattr(self, 'post_%s' % key)(key)
            except AttributeError:
                raise e # raise the original KeyError exception

    def __contains__(self, key):
        return hasattr(self, 'pre_%s' % key) or dict.__contains__(self, key) or hasattr(self, 'post_%s' % key)

    def _eval_str(self, cfgstr, additional_locals=None):
        # eval a splunkSource or splunkSourceEntity entry from uiHelper
        # we can guess that if it starts with a / for a url, then it's not meant
        # to be eval'd so we return it as a string literal
        if not len(cfgstr):
            return None
        if cfgstr[0]=='/':
            return cfgstr
        locals().update(self._context)
        if additional_locals:
            locals().update(additional_locals)
        return eval(cfgstr)

    def post_options(self, key):
        # called if the dictionary has no key called "options"
        if 'dynamicOptions' in self:
            dyn = dict.__getitem__(self, 'dynamicOptions')
            prefixOptions = dyn.get('prefixOptions', [])
            splunkSource = self._eval_str(dyn['splunkSource'])
            # fetch from splunk
            sargs = dyn.get('splunkSourceParams', {}).copy()
            if sargs:
                for key, val in list(sargs.items()):
                    nv = self._eval_str(val)
                    if nv == '': 
                        del sargs[key]
                        continue
                    sargs[key] = nv
            
            outputMode = sargs.get('output_mode', 'not-set')
            if dyn.get('splunkSourceEntity'):
                splunkSourceEntity = self._eval_str(dyn['splunkSourceEntity'])

                # check for possible conflict of args
                if 'namespace' in sargs:
                    logger.error('getEntity arguments contain a "namespace" key; namespace must be specified via __context in DynamicUIHelper instance')

                # fetch a single entity
                if splunkSourceEntity:
                    try:
                        enlist = en.getEntity(
                            splunkSource, 
                            splunkSourceEntity, 
                            namespace=self._context.get('namespace'), 
                            **sargs
                        )
                    except splunk.ResourceNotFound as e:
                        raise EAIFetchError(e.get_extended_message_text())

                    except splunk.InternalServerError as e:
                        # Some endpoints raise an exception if they have problems which we can translate into a nicer
                        # on-screen message by converting the exception to an EAIFetchError
                        logger.error("Failed to fetch dynamic element content from the server for splunkSource=%s splunkSourceEntity=%s" % (splunkSource, splunkSourceEntity))
                        if e.extendedMessages and 'text' in e.extendedMessages[0]:
                            raise EAIFetchError(e.extendedMessages[0]['text'])
                        raise EAIFetchError(e.msg)

                    if 'entityField' in dyn:
                        # fetch a dict/list from a specific entity field
                        entityField = self._eval_str(dyn['entityField'])
                        enlist = enlist[entityField]

                else:
                    #
                    # TODO: this branch does not seem to ever be executed.
                    # splunkSourceEntity will always be set in this if/else
                    # block
                    #
                    
                    # if splunkSourceEntity is there, but set to None, just return entity titles
                    try:
                        enlist = list(en.getEntities(
                            splunkSource, 
                            namespace=self._context.get('namespace'), 
                            count=-1, 
                            **sargs
                        ).keys())
                    except splunk.InternalServerError as e:
                        logger.error("Failed to fetch dynamic element content from the server for splunkSource=%s " % (splunkSource,))
                        if e.extendedMessages and 'text' in e.extendedMessages[0]:
                            raise EAIFetchError(e.extendedMessages[0]['text'])
                        raise EAIFetchError(e.msg)


            else:
                try:
                    if outputMode == 'json':
                        uri = en.buildEndpoint(splunkSource, namespace=self._context.get('namespace')) 
                        response, content = rest.simpleRequest(uri, getargs=sargs)
                        if response.status == 204:
                            content = '[]'
                        enlist = json.loads(content)['results']
                            
                    else:
                        enlist = en.getEntities(
                            splunkSource, 
                            namespace=self._context.get('namespace'), 
                            **sargs
                        )

                    if util.isLite() and enlist and splunkSource == '/apps/local':
                        newEnList = {}
                        appWhitelist = []
                        appList = auth.getUserPrefsGeneral('app_list')
                        addonList = auth.getUserPrefsGeneral('TA_list')

                        if appList:
                            appList = appList.split(",")
                        else:
                            appList = ['search']

                        appWhitelist.extend(appList)

                        if addonList:
                            addonList = addonList.split(",")
                            appWhitelist.extend(addonList)

                        for app in enlist:
                            if app in appWhitelist:
                                newEnList[app] = enlist[app]

                        enlist = newEnList

                except splunk.SplunkdConnectionException as e:
                    logger.error("Splunkd Connection Exception: %s" % e)
                    raise EAIFetchError(_('The splunkd daemon cannot be reached by splunkweb.  Check that there are no blocked network ports or that splunkd is still running.'))

                except splunk.RESTException as e:
                    logger.error("Failed to fetch dynamic element content from the server for splunkSource:%s\n%s" %
                    (splunkSource, e))
                    if 'get_extended_message_text' in dir(e):
                        raise EAIFetchError(e.get_extended_message_text())
                    raise EAIFetchError(e.msg)
                    
                except Exception as e:
                    raise EAIFetchError(e.msg)

            if 'extraOptions' in self:
                for opt in dict.__getitem__(self, 'extraOptions'):
                    yield opt

            if isinstance(enlist, (dict, splunk.util.OrderedDict)):
                keyname = dyn.get('keyName', 'title')
                keyvalue = dyn.get('keyValue', 'entry')
                for entry, title in prefixOptions:
                    yield {'label': _(title), 'value': "" if entry is None else entry }
                for title, entry in list(enlist.items()):
                    ev_locals = locals()
                    label = self._eval_str(keyname, ev_locals)
                    value = self._eval_str(keyvalue, ev_locals)
                    if value is None:
                        continue
                    yield {'label': label, 'value': value}
            elif isinstance(enlist, (list, tuple)):
                keyname = dyn.get('keyName', 'entry')
                keyvalue = dyn.get('keyValue', 'entry')
                for entry, title in prefixOptions:
                    yield {'label': title, 'value': "" if entry is None else entry }
                for entry in enlist:
                    ev_locals = locals()
                    label = self._eval_str(keyname, ev_locals)
                    value = self._eval_str(keyvalue, ev_locals)
                    if value is None:
                        continue
                    yield {'label': label, 'value': value}
        else:
            raise KeyError(key)


class DynamicUIHelperList(list):
    def __init__(self, *a, **kw):
        self._context = kw['__context']
        del kw['__context']
        super(DynamicUIHelperList, self).__init__(*a, **kw)

    def __getitem__(self, key):
        return dynfilter(list.__getitem__(self, key), context=self._context)

    def __contains__(self, key):
        return list.__contains__(self, key)

    def __iter__(self):
        for val in list.__iter__(self):
            yield dynfilter(val, context=self._context)



def cpQuoteEntity(entity_name, urlquote=True):
    """
    Cherrypy unquotes path segments during an incoming request
    and then the default dispatcher converts and remaining %2f strings to "/" 
    characters before invoking a handler.
    We want to keep the %2f intact, we we double encode it before then
    urllib.quote'ing the entire string

    Set urlquote=False if the resulting string is to be passed via an
    array into make_url() to avoid double escaping
    """
    if urlquote:
        return splunk.util.safeURLQuote(entity_name.replace('/', '%252f').replace('\\', '%255C'))
    return entity_name.replace('/', '%252f').replace('\\', '%255C')

def cpUnquoteEntity(entity_name):
    """
    By the time this function is called, cherrypy has already
    run urllib.unquote on the path segment so we just need to
    undo the previous double encoding of "/"
    """
    return entity_name.replace('%252f', '/').replace('%255C', '\\')
