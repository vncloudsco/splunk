from __future__ import absolute_import
#
# Cherrypy boot-time helper methods
#

import logging
import os.path

import cherrypy

import splunk
import splunk.entity
import splunk.util
import splunk.appserver.mrsparkle.lib.util as util

logger = logging.getLogger('splunk.appserver.mrsparkle.lib.startup')

VERSION_INIT_KEY = 'is_version_initted'
VERSION_LABEL_FORMAT_KEY = 'version_label_format'

def initVersionInfo(force=False, sessionKey=None):
    '''
    Initializes splunk product version and license info by asking splunkd.
    Returns true if successful, false otherwise
    '''

    if not sessionKey:
        sessionKey = splunk.getSessionKey()
    
    if cherrypy.config.get(VERSION_INIT_KEY) and not (force or sessionKey):
        return True

    logger.debug('Checking for product version information')

    buildNumber = '000'
    cpuArch = 'UNKNOWN_CPU_ARCH'
    osName = 'UNKNOWN_OS_NAME'
    versionLabel = 'UNKNOWN_VERSION'
    versionNumber = '4.0'
    isTrialLicense = True
    isFreeLicense = False
    licenseState = 'OK'
    trustedIP = None
    guid = None
    master_guid = None
    license_keys_list = []
    has_remote_master = 'UNKNOWN_HAS_REMOTE_MASTER'
    license_desc = 'UNKNOWN_LICENSE_DESCRIPTION'
    activeLicenseSubgroup = 'UNKNOWN_LICENSE_SUBGROUP'
    install_type = 'UNKNOWN_INSTALL_TYPE'
    licenseGroup = None
    productType = 'splunk'
    instanceType = 'splunk'
    serverName = ''
    staticAssetId = '000'
    addOns = {}
    licenseLabels = []
    success = True

    try:
        serverInfo = splunk.entity.getEntity('/server', 'info', namespace=None, owner='anon', sessionKey=sessionKey)
        buildNumber = str(serverInfo.get('build'))
        cpuArch = serverInfo.get('cpu_arch')
        osName = serverInfo.get('os_name')
        versionNumber = serverInfo.get('version')
        versionLabel = cherrypy.config.get(VERSION_LABEL_FORMAT_KEY, '%s') % serverInfo.get('version')
        isTrialLicense = splunk.util.normalizeBoolean(serverInfo.get('isTrial'))
        isFreeLicense = splunk.util.normalizeBoolean(serverInfo.get('isFree'))
        licenseState = serverInfo.get('licenseState')
        trustedIP = serverInfo.get('trustedIP')
        cherrypy.config[VERSION_INIT_KEY] = True
        guid = serverInfo.get('guid')
        master_guid = serverInfo.get('master_guid')
        addOns = serverInfo.get('addOns')
        licenseGroup = serverInfo.get('activeLicenseGroup')
        productType = serverInfo.get('product_type')
        serverName = serverInfo.get('serverName')
        licenseLabels = serverInfo.get('license_labels')
        instanceType = serverInfo.get('instance_type')
        activeLicenseSubgroup = serverInfo.get('activeLicenseSubgroup')
        staticAssetId = serverInfo.get('staticAssetId')

        #
        # SPL-38364, in this case, we want to get up to
        # 3 license labels and ship them over as the type
        # string, we just send a comma separated value here
        #

        # default to pro
        license_desc = 'pro'
        
        #we are a free license
        if ( isFreeLicense ):
            license_desc = 'free'

        # we are on a license master
        elif ( guid == master_guid ):
            license_label_list = serverInfo.get('license_labels')

            # dedup and set only take first 3 of them
            license_label_list = list(set( license_label_list ))[:10]
            if ( len(license_label_list) > 0 ):
                license_desc = ','.join(license_label_list)

        install_type = 'trial' if isTrialLicense else 'prod'
        if ( guid != master_guid ):
            install_type = install_type + '_slave'
            
    except Exception as e:
        success = False
        if sessionKey is not None:
            logger.error('Unable to read in product version information; %s' % e)

    # always set something
    cherrypy.config['build_number'] = buildNumber
    cherrypy.config['cpu_arch'] = cpuArch
    cherrypy.config['os_name'] = osName
    cherrypy.config['version_number'] = versionNumber # "4.1"
    cherrypy.config['version_label'] = versionLabel # "4.1 Beta"
    cherrypy.config['is_free_license'] = isFreeLicense
    cherrypy.config['is_trial_license'] = isTrialLicense
    cherrypy.config['is_forwarder_license'] = True if license_desc.lower() == "splunk forwarder" else False
    cherrypy.config['license_state'] = licenseState
    cherrypy.config['splunkdTrustedIP'] = trustedIP
    cherrypy.config['guid'] = guid
    cherrypy.config['master_guid'] = master_guid
    cherrypy.config['license_desc'] = license_desc
    cherrypy.config['install_type'] = install_type
    cherrypy.config['addOns'] = addOns
    cherrypy.config['activeLicenseGroup'] = licenseGroup
    cherrypy.config['product_type'] = productType
    cherrypy.config['serverName'] = serverName
    cherrypy.config['license_labels'] = licenseLabels
    cherrypy.config['instance_type'] = instanceType
    cherrypy.config['activeLicenseSubgroup'] = activeLicenseSubgroup
    cherrypy.config['staticAssetId'] = staticAssetId

    logger.info(
        'Splunk appserver version=%(version_label)s build=%(build_number)s isFree=%(is_free_license)s isTrial=%(is_trial_license)s' % cherrypy.config
    )

    return success

def getDatepickerPath (): 
    """
    returns the path of the datepicker js file with the correct locale
    """
    import splunk.appserver.mrsparkle.lib.i18n as i18n
    staticdir = cherrypy.config.get('staticdir')
    lang = i18n.current_lang_url_component()
    locale = None
    locale1 = lang
    locale2 = lang[:2]
    for testlocale in (locale1, locale2):
        if os.path.exists(os.path.join(staticdir, 'js', 'contrib', 'jquery.ui.datepicker', 'jquery.ui.datepicker-%s.js' % testlocale)):
            locale = ('contrib', 'jquery.ui.datepicker', 'jquery.ui.datepicker-%s.js' % testlocale)
            break
    return locale

def generateJSManifest(internal_use = False):
    '''
    if internal_use is False, the generated list will be forward-slash-delimited, with '/static/'
    as the prefix, ["/static/js/contrib/lowpro_for_jquery.js",...]

    if internal_use is True, the generated list will be os.path.join()ed segments, e.g.
    [os.path.join("contrib", "jquery-1.6.2.js"),...]
    '''
    # only used internally, templates include these in base.html
    js_initial_filenames = [
            # initial packages
            ("contrib", "jquery", "jquery.js"),
            "i18n.js",
            "splunk.js",
            "util.js"
    ]

    # !!!!!
    # Note: when adding new libraries here, they also need to be added to admin_lite.html template
    # for Manager pages that don't use view system.
    js_filenames = [
            # external packages
            ("contrib", "lowpro_for_jquery.js"),
            ("contrib", "json2.js"),
            ("contrib", "deprecated", "jquery-ui-1.8.24.js"),
            ("contrib", "jquery.ui.tablesorter.js"),
            ("contrib", "jquery.bgiframe.min.js"),
            ("contrib", "jquery.cookie.js"),
            ("contrib", "jquery.form.js"),
            ("contrib", "ui.spinner.js"),
            ("contrib", "jquery.tipTip.minified.js"),
            ("contrib", "jquery.iphone-style-checkboxes.js"),
            ("contrib", "jquery.ui.nestedSortable.js"),
            ("contrib", "jquery.placeholder.min.js"),
            ("contrib", "spin.min.js"),
            ("contrib", "jquery.treeview.js"),
            ("contrib", "jquery.treeview.edit.js"),
            ("contrib", "jquery.treeview.async.js"),
            ("contrib", "jquery.tools.min.js"),
            ("contrib", "doT.js"),
            ("contrib", "jg_global.js"),
            ("contrib", "jg_library.js"),
            ("contrib", "script.js"),
            ("contrib", "jquery.trap.min.js"),

            # splunk sdk, required for geoviz
            ("contrib", "splunk.js"),

            # TEMPORARY - we're still looking for something better than strftime
            ("contrib", "strftime.js"),

            # splunk packages
            "logger.js",
            "error.js",
            "session.js",
            "job.js",
            "messenger.js",
            "message.js",
            "context.js",
            "search.js",
            "jobber.js",
            "menu_builder.js",
            "admin.js",
            "admin_lite.js",
            "time_range.js",
            "module_loader.js",
            "ja_bridge.js",
            "legend.js",
            "jquery.sparkline.js",
            "popup.js",
            "layout_engine.js",
            "paginator.js",
            "print.js",
            "page_status.js",
            "dev.js",
            "window.js",
            "field_summary.js",
            "viewmaster.js",
            "textarea_resize.js",
            "scroller.js",
            "timespinner.js",
            "login.js",
            "dashboard.js",
            "splunk_time.js",
            "pdf.js",   

            # patch the draggables lib for ios support
            ("patches", "splunk.jquery.ios-drag-patch.js"),

            # Check for the CSRF token
            "splunk.jquery.csrf_protection.js",

            # Check for the X-Splunk-Messages-Available flag and instruct the Messenger to update itself
            "splunk.jquery.check_messages.js",

            # rich radio controls
            "splunk.jquery.radio.js"
            ]

    if (util.isLite()):
        js_filenames.append(("..", "build", "modules_nav", "lite", "index.js"))
    else:
        js_filenames.append(("..", "build", "modules_nav", "enterprise", "index.js"))

    #datepicker
    datepicker_path = getDatepickerPath()
    if (datepicker_path):
        js_filenames.append(datepicker_path)

    if internal_use:
        return [ fn if isinstance(fn, splunk.util.string_type) else os.path.join(*fn) for fn in js_initial_filenames + js_filenames ]
    else:
        prefix = '/static/js/'
        return [ prefix + fn if isinstance(fn, splunk.util.string_type) else prefix + '/'.join(fn) for fn in js_filenames ]
