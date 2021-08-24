import splunk.admin as admin
import splunk.appbuilder as appbuilder
import splunk.bundle as bundle
import splunk.util

ADMIN_ALL_OBJECTS = "admin_all_objects"
EDIT_OR_INSTALL_APPS = "edit_local_apps or install_apps"

class AppTemplatesHandler(admin.MConfigHandler):
    def setup(self):
        limits_conf = bundle.getConf('limits', sessionKey=self.getSessionKey())
        enableInstallApps = limits_conf['auth']['enable_install_apps']
        if ('enable_install_apps' in limits_conf['auth'] and
                splunk.util.normalizeBoolean(enableInstallApps)):
            self.setReadCapability(EDIT_OR_INSTALL_APPS)
        else:
            self.setReadCapability(ADMIN_ALL_OBJECTS)

    '''
    Lists locally installed applications
    '''
    def handleList(self, confInfo):
        for template in appbuilder.getTemplates():
            confInfo[template].append('lol', 'wut')

admin.init(AppTemplatesHandler, admin.CONTEXT_APP_ONLY)
