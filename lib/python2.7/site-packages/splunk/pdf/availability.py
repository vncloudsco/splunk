try:
    import cherrypy
except ImportError:
    cherrypy = None
import splunk.entity as entity

WEB_CONF_ENTITY = '/configs/conf-web'


def is_available(session_key=None):
    """
    read the available flag from web.conf
    :param session_key:
    :return:
    """
    if cherrypy is not None and cherrypy.config is not None and 'pdfgen_is_available' in cherrypy.config:
        pdf_available = cherrypy.config.get('pdfgen_is_available')
    else:
        try:
            settings = entity.getEntity(WEB_CONF_ENTITY, 'settings', sessionKey=session_key)
            pdf_available = settings.get('pdfgen_is_available', 0)
        except Exception:
            # failed to retrieve web.conf, we assume pdf service is ready.
            pdf_available = 1
    return pdf_available
