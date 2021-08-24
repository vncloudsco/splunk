import base64
import json
import logging
import zlib
import sys
import splunk.util as util

logger = logging.getLogger('splunk.appserver.lib.statedict')


BASE64=1

class StateDict(dict):
    """
    Simple class to provide a serializable dict for storing state
    in web forms
    """

    def serialize(self, format=BASE64):
        if not len(self):
            return ''
        if format==BASE64:
            data = json.dumps(dict(self))
            if sys.version_info >= (3, 0):
                data = data.encode('utf-8')

            b64_cmp_data = base64.urlsafe_b64encode(zlib.compress(data))

            if sys.version_info >= (3, 0):
                return b64_cmp_data.decode()
            return b64_cmp_data
        raise ValueError("Invalid format specified")

    @classmethod
    def unserialize(cls, data, format=BASE64):
        if not data:
            return cls()
        if format==BASE64:
                try:
                    state = json.loads(zlib.decompress(base64.urlsafe_b64decode(util.toUTF8(data))))

                    if state.get('breadcrumbs'):
                        state['breadcrumbs'] = util.sanitizeBreadcrumbs(state['breadcrumbs'])

                    if state.get('return_to') and not util.isRedirectSafe(str(state['return_to'])):
                        del state['return_to']

                    if state.get('return_to_success') and not util.isRedirectSafe(str(state['return_to_success'])):
                        del state['return_to_success']

                    return cls(state)
                except Exception as e:
                    logger.error("Failed to decompress StateDict: %s" % e)
                    raise ValueError("Invalid state string supplied")
        raise ValueError("Invalid format specified")
