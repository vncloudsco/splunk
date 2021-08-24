from __future__ import absolute_import
from builtins import object

import hashlib
import logging
import os
import os.path
import re
import sys

import splunk.appserver as appserver
import splunk.appserver.mrsparkle.lib.cached as cached
import splunk.appserver.mrsparkle.lib.util as util
import splunk.util


logger = logging.getLogger('splunk.appserver.lib.apps')


class LocalApps(object):
    """
    Interface to enumerate locally installed applications
    Don't instantiate this yourself - access the apps.local_apps singleton instead

    NOTE: This class is an unsecure data provider because its primary purpose
    is to load application-level assets, and does not make calls to the auth
    system.  For user-facing situations, the splunk.entity.getEntities('apps/local')
    call is preferred.
    """

    def __init__(self):
        self.apps = {} # application data keyed on app name
        self.modules = {} # module name to app name mapping
        self.system_modules_path = util.make_splunkhome_path(['share', 'splunk', 'search_mrsparkle', 'modules'])
        self.loaded = False # data is lazy loaded

    def refresh(self, force=True):
        """
        Refresh the list of applications installed on the local machine
        """
        apps_path = util.get_apps_dir()
        slaveapps_path = util.get_slaveapps_dir()
        if self.loaded and not force:
            return True
        else:
            newapps = os.listdir(apps_path)
            newapps_slave = os.listdir(slaveapps_path) if os.path.isdir(slaveapps_path) else []

        ### will return a list to be appended by refresh()
        self.loaded = True

        # scan patch directory
        patch_dir = util.make_splunkhome_path(['share', 'splunk', 'search_mrsparkle', 'exposed', 'css', 'skins', 'default', 'patches'])
        patches = {}
        if os.path.exists(patch_dir):
            for patch_file in os.listdir(patch_dir):
                m = re.search("(\w+)\.css$", patch_file)
                if m:
                    patches[m.group(1)] = '/static/css/skins/default/patches/%s' % patch_file

        # SPL-79309 - Warning regarding duplicate module dir name
        # refreshing self.modules since apps are being force refreshed
        if force:
            self.modules = {}

        for fn in set(newapps_slave + newapps):
            # apps in slave-apps take precedence over regular apps. we merge and remove dups, then find the path with higher priority.
            path = os.path.join(slaveapps_path, fn) if fn in newapps_slave else os.path.join(apps_path, fn)
            if not os.path.isdir(path):
                continue

            self.apps[fn] = {
                'full_path': path,
                'modules': [],
                'static': {},
                'patch': {'css': []},
            }

            # See if the app defines any modules
            if os.path.exists(os.path.join(path, 'appserver', 'modules')):
                modules = self.apps[fn]['modules'] = self._scanAppModules(fn)
                for module in modules:
                    # check if prior set app module duplicates a module in the app namespace
                    prior_set_app = self.modules.get(module)
                    if prior_set_app:
                        selected_app = min(prior_set_app, fn)
                        # if prior set app is in the app namespace
                        if prior_set_app is not appserver.mrsparkle.SYSTEM_NAMESPACE:
                            # override module namespace with selected app namespace
                            self.modules[module] = selected_app
                            msg = "Duplicate module dir name '%s' between apps '%s' and '%s', will refer to module dir in '%s'"
                            # should be info, but stupid default log levels lead to nonsense
                            logger.warn(msg % (module, fn, prior_set_app, selected_app))
                    else:
                        selected_app = fn
                        self.modules[module] = selected_app

                    # check if app module duplicates a system module
                    # warn user that we will use the module in the system namespace since system modules are populated below overriding dups if any
                    # placing check here instead of populating system modules above newapps for loop to avoid modifying order in which self.modules is populated
                    if os.path.isdir(os.path.join(self.system_modules_path, module) ):
                        msg = "Duplicate module dir name '%s' between apps '%s' and '%s', will refer to module dir in '%s'"
                        logger.warn(msg % (module, fn, 'system', 'system'))

            # See if the app defines any static content
            if os.path.isdir(os.path.join(path, 'appserver', 'static')):
                self.apps[fn]['static'] = self._scanAppStaticContent( os.path.join(path, 'appserver', 'static') )

            application_css_path = os.path.join(path, 'appserver', 'static', 'application.css')
            if os.path.exists(application_css_path):
                f = open(application_css_path, 'rb')
                hash = hashlib.sha1()
                hash.update(f.read())
                digest = hash.hexdigest()
                f.close()
                patch_file_name = '%s-%s.css' % (fn, digest)
                if digest in patches:
                    self.apps[fn]['patch']['css'].append(patches[digest])

        # scan in the system built-in/default modules and put them in the system namespace
        self.apps[appserver.mrsparkle.SYSTEM_NAMESPACE] = {
            'full_path': util.make_splunkhome_path(['share', 'splunk', 'search_mrsparkle']),
            'modules' : self._scanSystemModules()
        }

        return True


    def _scanAppStaticContent(self, app_static_path):
        # filetypes that we are scanning for
        fileTypes = ['css', 'js']#, '.jpg', '.gif', '.png']
        static_content_paths = {}
        for fileType in fileTypes:
            static_content_paths[ fileType ] = []

        # scan file and add into dictionary of the form:
        # { "css": [<list of css files>], "js": [<list of js files>]}
        for fn in os.listdir(app_static_path):
            name, ext = os.path.splitext(fn)
            if ext[1:] in fileTypes:
                static_content_paths[ ext[1:] ].append(fn)
            else:
                continue

        if len(static_content_paths) > 0:
            logger.debug('_scanAppStaticContent - found static assets in: %s' % static_content_paths)

        return static_content_paths

    def _scanSystemModules(self):
        system_modules = []
        for module_dir in os.listdir(self.system_modules_path):
            if os.path.isdir(os.path.join(self.system_modules_path, module_dir) ):
                system_modules.append(module_dir)
                self.modules[module_dir] = appserver.mrsparkle.SYSTEM_NAMESPACE
        return system_modules


    def _scanAppModules(self, app):
        if app not in self.apps:
            raise ValueError("Invalid app name supplied")
        app = self.apps[app]
        modules_dir = os.path.join(app['full_path'], 'appserver', 'modules')
        result = []
        if not os.path.exists(modules_dir):
            return result
        for fname in os.listdir(modules_dir):
            modpath = os.path.join(modules_dir, fname)
            if os.path.isdir(modpath):
                result.append(fname)
        return result


    def getAppModules(self, app):
        """Return a list of module directory names that an app defines"""
        self.refresh(False)
        if app not in self.apps:
            raise ValueError("Invalid app name supplied")
        return self.apps[app]['modules']


    def getModulePath(self, module_name):
        """Fetch the on disk path name to a given module"""
        self.refresh(False)
        if module_name not in self.modules:
            return False
        if self.apps[self.modules[module_name]]['full_path'].find('search_mrsparkle') > -1:
            return os.path.join(self.apps[self.modules[module_name]]['full_path'], 'modules', module_name)
        else:
            return os.path.join(self.apps[self.modules[module_name]]['full_path'], 'appserver', 'modules', module_name)

    def getAllModules(self):
        """
        Return a list of all modules that applications has defined.
        Each list element is a tuple (app_name, module_name, module_path)
        """
        self.refresh(False)
        return [ (app_name, module_name, self.getModulePath(module_name)) for module_name, app_name in list(self.modules.items()) ]

    def __iter__(self):
        self.refresh(False)
        return self.apps.__iter__()

    def items(self):
        self.refresh(False)
        return list(self.apps.items())

    def __getitem__(self, index):
        self.refresh(False)
        if sys.version_info < (3, 0) and isinstance(index, str):
            return self.apps.__getitem__(splunk.util.unicode(index, 'utf-8'))
        else:
            return self.apps.__getitem__(index)

    def __contains__(self, index):
        self.refresh(False)
        if sys.version_info < (3, 0) and isinstance(index, str):
            return self.apps.__contains__(splunk.util.unicode(index, 'utf-8'))
        else:
            return self.apps.__contains__(index)

# define stub method to init a new apps instance
def getLocalApps():
    '''
    static method accessor to class-based object instance
    '''
    return LocalApps()

# TODO: remove this singleton
local_apps = getLocalApps()
