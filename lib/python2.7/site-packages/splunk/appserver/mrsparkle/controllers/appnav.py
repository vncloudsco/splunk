import cherrypy, json, logging
import splunk.appserver.mrsparkle
from splunk.appserver.mrsparkle.lib import appnav
import splunk.entity as en
import time

from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

logger = logging.getLogger('splunk.appserver.controllers.appnav')

class AppNavController(BaseController):
    def _setHeaders(self):
        '''
        sets headers for appnav route
        '''
        cherrypy.response.headers['content-type'] = splunk.appserver.mrsparkle.MIME_JSON
        cherrypy.response.headers['Cache-Control'] = 'no-cache'
        cherrypy.response.headers['Pragma'] = 'no-cache'

    @route('/')
    @expose_page(must_login=True, methods='GET')
    def allApps(self):
        '''
        Outputs a JSON dictionary
            { app_name: {
            "nav": hieararchical app nav, fully populated
            "defaultView": the name of the default view
            "color": the color that should be used for the app
            }, { app_name: {...}}}
            "messages": if there were any errors, an array of messages, each item being a dict: {"type":type, "text":text}
        '''
        self._setHeaders()

        return self._getAppNav()

    @route('/:app')
    @expose_page(must_login=True, methods='GET')
    def specificApp(self, app, _=None):
        '''
        Outputs a JSON dictionary
            "nav": hieararchical app nav, fully populated
            "defaultView": the name of the default view
            "color": the color that should be used for the app
            "messages": if there were any errors, an array of messages, each item being a dict: {"type":type, "text":text}
        '''
        cherrypy.response.headers['content-type'] = splunk.appserver.mrsparkle.MIME_JSON
        return self._getAppNav(app)
        
    def _getAppNav(self, app=None):
        '''
        If app is provided, getAppNav will return the appnav data for that specific app
        If app is None, getAppNav will return all appnav data accessible by the current user

        NOTE: we're catching all exceptions in order to return JSON formatted error messages
        '''
        
        errorMessages = []
        appData = {}
        navData = {}
        viewManifest = None

        # if we are getting data for more than one app, gather nav, view and app data for all apps
        #   NOTE: we do not gather search data since we will optimistically assume that most app
        #         nav does not require saved search, so we will let appnav lib load if/when 
        #         necessary
        try:
            if not app:
                dataStart = time.time()
                appData = self._getAllAppData()
                viewManifest = self._getAllViews()
                navData = self._getAllNavData()
                dataEnd = time.time()
                logger.info("appnav getting data duration=%s" % (dataEnd - dataStart))
            else:
                appData = self._getAppData(app)
        except Exception as e:
            errorMsg = "Exception while trying to get necessary data to build nav for app '%s': %s" % (app, e)
            errorMessages.append({"type":"ERROR", "text":errorMsg})
            logger.error(errorMsg)

        # build up output for 1 or more apps
        output = {}
        for key in appData:
            try:
                output[key] = self._getIndividualAppNav(
                                    app=key, 
                                    viewManifest=viewManifest, 
                                    appData=appData.get(key, {}), 
                                    navData=navData.get(key, None)
                                    )
            except Exception as e:
                errorMsg = "Exception while trying to load nav data for app '%s': %s" % (key, e)
                errorMessages.append({"type":"ERROR", "text":errorMsg})
                logger.error(errorMsg)

        if len(errorMessages) > 0:
            output["messages"] = errorMessages
       
        # if output is just for one app, remove the unnecessary hierarchy
        if app:
            output = output[app]
 
        return json.dumps(output)
    
    def _getIndividualAppNav(self, app, viewManifest, appData, navData):
        '''
        Return the appnav data for a specific app, specified by app
        @param app: the name of the specific app
        @param viewManifest: a dict of {name:{'label':label,'isVisible':bool,'isDashboard':bool,'name':name,'app':app}}, can be None
        @param appData: the appData Entity
        @param navData: the navData Entity, can be None
        '''

        appNavObj = appnav.AppNav(app, viewManifest=viewManifest, searches=None, navData=navData)

        nav = appNavObj.getNav()
        defaultView = appNavObj.getDefaultView()
        color = appNavObj.getNavColor()

        output = {}
        if nav:
            output["nav"] = nav
        if defaultView:
            output["defaultView"] = defaultView
        if color:
            output["color"] = color

        label = appData.get('label', None) 
        if label:    
            output["label"] = label

        return output

    def _getAllAppData(self):
        output = {} 
        try:
            # don't need to worry about dict vs list here since the names of apps should be unique
            apps = en.getEntities('apps/local', search=['disabled=false', 'visible=true'], count=-1, namespace="-") 
            for key, app in apps.items():
                output[key] = {}
                output[key]['label'] = _(app.get('label', ''))
        except splunk.ResourceNotFound:
            logger.error("Unable to retrieve apps/local/-")

        return output 

    def _getAppData(self, app):
        output = {app:{}}

        try:
            appData = en.getEntity('apps/local', app, namespace=app)
            output[app]['label'] = _(appData.get('label'))
        except splunk.ResourceNotFound:
            logger.error("Unable to retrieve apps/local/%s" % app)

        return output

    def _getAllViews(self):
        output = {}
        try:
            # use getEntitiesList instead of getEntities so that we can handle views with identical names across multiple apps
            views = en.getEntitiesList('data/ui/views', count=-1, digest=1, search='isVisible=1', namespace="-")
            for view in views:
                output[view.name] = {
                    'label':view.get('label', view),
                    'isVisible':view.get('isVisible', 1),
                    'isDashboard':view.get('isDashboard', 1),
                    'name':view.name,
                    'app':view.get('eai:acl', {}).get('app', "")
                    }
        except splunk.ResourceNotFound:
            logger.warn('Unable to retrieve views')
        return output

    def _getAllNavData(self):
        navData = {}
        try:
            # use getEntitiesList instead of getEntities since each entity is named "default"
            navs = en.getEntitiesList('data/ui/nav', namespace="-")
            for data in navs:
                if data.get('eai:appName'):
                    navData[data.get('eai:appName')] = data 
        except splunk.ResourceNotFound:       
            logger.warn('Unable to retrieve nav data for all apps')
        return navData
