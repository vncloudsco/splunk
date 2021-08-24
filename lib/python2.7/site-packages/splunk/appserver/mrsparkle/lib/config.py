import cherrypy
import json
import time
import logging
import splunk
import splunk.appserver.mrsparkle
import splunk.appserver.mrsparkle.lib.cached as cached
import splunk.appserver.mrsparkle.lib.decorators as decorators
import splunk.appserver.mrsparkle.lib.i18n as i18n
import splunk.appserver.mrsparkle.lib.times as times
import splunk.appserver.mrsparkle.lib.util as util

logger = logging.getLogger('splunk.appserver.lib.config')

def _get_root_path():
    if hasattr(cherrypy.request, 'embed') and cherrypy.request.embed and cherrypy.request.config.get('embed_uri'):
        return cherrypy.request.config.get('embed_uri')
    else:
        return cherrypy.request.script_name

def _get_active_config():
    js_logging_level = logging.getLogger('splunk.appserver.controllers.util').getEffectiveLevel()
    sso_created_session = False
    if cherrypy.request.headers.get('X-Splunkd') is not None:
        sso_created_session = util.parse_xsplunkd_header().get('sso_created_session')
    else:
        # Retrieve the name of the remote user header passed from the proxy
        remote_user_header = cherrypy.request.config.get(decorators.SPLUNKWEB_REMOTE_USER_CFG) or decorators.DEFAULT_REMOTE_USER_HEADER
        sso_created_session = cherrypy.request.headers.get(remote_user_header) is not None and cherrypy.config.get('trustedIP') is not None

    return {
        'SEARCH_RESULTS_TIME_FORMAT': i18n.ISO8609_MICROTIME,
        'DISPATCH_TIME_FORMAT': cherrypy.config.get('DISPATCH_TIME_FORMAT'),
        'MRSPARKLE_ROOT_PATH': _get_root_path(),
        'MRSPARKLE_PORT_NUMBER': cherrypy.config.get('tools.csrfcookie.port'),
        'VERSION_LABEL': cherrypy.config.get('version_label', 'UNKNOWN_VERSION'),
        'BUILD_NUMBER': cherrypy.config.get('build_number', '0'),
        'BUILD_PUSH_NUMBER': cherrypy.config.get('_push_version', 0),
        'LOCALE': i18n.current_lang_url_component(),
        'FLASH_MAJOR_VERSION': cherrypy.config.get('flash_major_version', 0),
        'FLASH_MINOR_VERSION': cherrypy.config.get('flash_minor_version', 0),
        'FLASH_REVISION_VERSION': cherrypy.config.get('flash_revision_version', 0),
        "JS_LOGGER_MODE": cherrypy.config.get('js_logger_mode', 0),
        "JS_LOGGER_MODE_SERVER_END_POINT": cherrypy.config.get('js_logger_mode_server_end_point', '/'),
        "JS_LOGGER_MODE_SERVER_POLL_BUFFER": cherrypy.config.get('js_logger_mode_server_poll_buffer', 100000),
        "JS_LOGGER_MODE_SERVER_MAX_BUFFER": cherrypy.config.get('js_logger_mode_server_max_buffer', 1000),
        "JS_LOGGER_LEVEL": logging.getLevelName(js_logging_level),
        'UI_UNIX_START_TIME': int(cherrypy.config.get('start_time', 0)),
        'DEFAULT_NAMESPACE': splunk.getDefault('namespace'),
        'SYSTEM_NAMESPACE': splunk.appserver.mrsparkle.SYSTEM_NAMESPACE,
        'UI_INACTIVITY_TIMEOUT': getCherrypyConfigIntSafe('ui_inactivity_timeout', 60),
        'SERVER_TIMEZONE_OFFSET': getServerTimezoneOffset(),
        'SERVER_ZONEINFO': getServerZoneInfo(),
        'SPLUNKD_FREE_LICENSE': cherrypy.config.get('is_free_license'),
        'USERNAME': cherrypy.session.get('user', {}).get('name'),
        'ENABLE_PIVOT_ADHOC_ACCELERATION': cherrypy.config.get('enable_pivot_adhoc_acceleration', True),
        'APP_NAV_REPORTS_LIMIT': int(cherrypy.config.get('appNavReportsLimit', 500)),
        'PIVOT_ADHOC_ACCELERATION_MODE': cherrypy.config.get('pivot_adhoc_acceleration_mode', 'Elastic'),
        'JSCHART_TEST_MODE': cherrypy.config.get('jschart_test_mode', False),
        'PDFGEN_IS_AVAILABLE': cherrypy.config.get('pdfgen_is_available', 0),
        'JOB_MIN_POLLING_INTERVAL': int(float(cherrypy.config.get('job_min_polling_interval', 100))),
        'JOB_MAX_POLLING_INTERVAL': int(float(cherrypy.config.get('job_max_polling_interval', 1000))),
        'SPLUNKD_PATH': util.make_url('/splunkd/__raw'),
        'JSCHART_TRUNCATION_LIMIT': cherrypy.config.get('jschart_truncation_limit', None),
        'JSCHART_TRUNCATION_LIMIT_CHROME': cherrypy.config.get('jschart_truncation_limit.chrome', None),
        'JSCHART_TRUNCATION_LIMIT_FIREFOX': cherrypy.config.get('jschart_truncation_limit.firefox', None),
        'JSCHART_TRUNCATION_LIMIT_SAFARI': cherrypy.config.get('jschart_truncation_limit.safari', None),
        'JSCHART_TRUNCATION_LIMIT_IE11': cherrypy.config.get('jschart_truncation_limit.ie11', None),
        'JSCHART_TRUNCATION_LIMIT_IE10': cherrypy.config.get('jschart_truncation_limit.ie10', None),
        'JSCHART_TRUNCATION_LIMIT_IE9': cherrypy.config.get('jschart_truncation_limit.ie9', None),
        'JSCHART_TRUNCATION_LIMIT_IE8': cherrypy.config.get('jschart_truncation_limit.ie8', None),
        'JSCHART_TRUNCATION_LIMIT_IE7': cherrypy.config.get('jschart_truncation_limit.ie7', None),
        'JSCHART_SERIES_LIMIT': cherrypy.config.get('jschart_series_limit', None),
        'JSCHART_RESULTS_LIMIT': cherrypy.config.get('jschart_results_limit', None),
        'CHOROPLETH_SHAPE_LIMIT': cherrypy.config.get('choropleth_shape_limit', None),
        'DASHBOARD_HTML_ALLOW_INLINE_STYLES': cherrypy.config.get('dashboard_html_allow_inline_styles', True),
        'DASHBOARD_HTML_ALLOW_IFRAMES': cherrypy.config.get('dashboard_html_allow_iframes', True),
        'DASHBOARD_HTML_WRAP_EMBED': cherrypy.config.get('dashboard_html_wrap_embed', True),
        'DASHBOARD_HTML_ALLOW_EMBEDDABLE_CONTENT': cherrypy.config.get('dashboard_html_allow_embeddable_content', False),
        'EMBED_URI': cherrypy.config.get('embed_uri', ''),
        'EMBED_FOOTER': cherrypy.config.get('embed_footer', ''),
        'MAX_UPLOAD_SIZE': cherrypy.config.get('server.max_request_body_size', 0),
        'SSO_CREATED_SESSION': sso_created_session,
        'ENABLE_RISKY_COMMAND_CHECK': cherrypy.config.get('enable_risky_command_check', True)
    }

def _get_active_unauthorized_config():
    return {
        'MRSPARKLE_ROOT_PATH': _get_root_path(),
        'MRSPARKLE_PORT_NUMBER': cherrypy.config.get('tools.csrfcookie.port'),
        'UI_INACTIVITY_TIMEOUT': getCherrypyConfigIntSafe('ui_inactivity_timeout', 60),
        'FORM_KEY': util.getFormKey(),
        'SERVER_ZONEINFO': '',
        'SPLUNKD_PATH': util.make_url('/splunkd/__raw'),
        'JSCHART_TEST_MODE': cherrypy.config.get('jschart_test_mode', False),
        'JSCHART_TRUNCATION_LIMIT': cherrypy.config.get('jschart_truncation_limit', None),
        'JSCHART_TRUNCATION_LIMIT_CHROME': cherrypy.config.get('jschart_truncation_limit.chrome', None),
        'JSCHART_TRUNCATION_LIMIT_FIREFOX': cherrypy.config.get('jschart_truncation_limit.firefox', None),
        'JSCHART_TRUNCATION_LIMIT_SAFARI': cherrypy.config.get('jschart_truncation_limit.safari', None),
        'JSCHART_TRUNCATION_LIMIT_IE11': cherrypy.config.get('jschart_truncation_limit.ie11', None),
        'JSCHART_TRUNCATION_LIMIT_IE10': cherrypy.config.get('jschart_truncation_limit.ie10', None),
        'JSCHART_TRUNCATION_LIMIT_IE9': cherrypy.config.get('jschart_truncation_limit.ie9', None),
        'JSCHART_TRUNCATION_LIMIT_IE8': cherrypy.config.get('jschart_truncation_limit.ie8', None),
        'JSCHART_TRUNCATION_LIMIT_IE7': cherrypy.config.get('jschart_truncation_limit.ie7', None),
        'JSCHART_SERIES_LIMIT': cherrypy.config.get('jschart_series_limit', None),
        'JSCHART_RESULTS_LIMIT': cherrypy.config.get('jschart_results_limit', None),
        'EMBED_URI': cherrypy.config.get('embed_uri', ''),
        'EMBED_FOOTER': cherrypy.config.get('embed_footer', ''),
        'LOCALE': i18n.current_lang_url_component(),
    }

def _get_app_config(app):
    try:
        rawConfig = splunk.bundle.getConf('app', namespace=app)
    except splunk.ResourceNotFound:
        return {}
    return {
        'APP_BUILD': rawConfig['install'].get('build', 0)
    }

def getCherrypyConfigIntSafe(key, default):
    """returns int value under the key in cherrypy.config; if it's not an integer, returns default value"""
    try:
        i = int(cherrypy.config.get(key, default))
        return (i<0)*0 + (i>0)*i
    except ValueError:
        logger.warn('%s key is not integer, assuming default value %s', key, default)
        return default

def getServerTimezoneOffset():
    """  returns the offset from GMT in seconds  """
    # Somewhat shockingly, this clunky if/else is the official way to get the actual timezone offset,
    # ie a offset int that is accurate in both DST and non-DST times.
    if (time.localtime()[-1] == 1):
        return time.altzone
    else:
        return time.timezone

def getServerZoneInfoNoMem():
    '''
    Returns server's zoneinfo table.  Not Memoized.
    '''
    try:
        return times.getServerZoneinfo()
    except Exception as e:
        logger.exception(e)
        return ''

@cached.memoized(cache_age=30)
def getServerZoneInfo():
    '''
    Returns server's zoneinfo table.  Memoized.
    '''
    return getServerZoneInfoNoMem()

def getConfig(sessionKey=None, namespace=None, embed=False, oid=None):
    '''
    Returns the configuration information for the main Splunk frontend.
    The values returned from the endpoint are subject to the following:

    1) values are idempotent
    2) any time values are in ISO-8601 format
    3) values are typed appropriately

    These values should be treated as read-only.

    '''
    # unauthed calls get the bare minimum
    if not sessionKey:
        args = _get_active_unauthorized_config()
        if embed:
            try:
                args['SERVER_ZONEINFO'] = times.getServerZoneinfo(sessionKey=oid)
            except:
                pass
    else:
        args = _get_active_config()

    if namespace:
        args.update(_get_app_config(namespace))

    logger.debug('config values: %s' % args)
    return args
