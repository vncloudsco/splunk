import json
import os
import sys
import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

path = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                     '..', '..', 'bin'))
sys.path.append(path)

try:
    from splunk_instrumentation.splunkd import Splunkd
except Exception:
    raise


def get_search_heads(splunkd):
    """
    Get the list of search head mgmt uri's
    """
    shcluster_config = splunkd.get_json_content('/services/shcluster/config')
    if not shcluster_config['disabled']:
        shcluster_member_entries = splunkd.get_json('/services/shcluster/member/members')['entry']
        return [entry['content']['mgmt_uri'] for entry in shcluster_member_entries]
    else:
        return []


class ListDiagsHandler(PersistentServerConnectionApplication):
    """
    Lists the status for all known diags on a single server or SHC
    """

    def __init__(self, command_line=None, command_arg=None):
        PersistentServerConnectionApplication.__init__(self)
        self.token = ''
        self.server_uri = ''

    def parse_arg(self, arg):
        try:
            arg = json.loads(arg)
        except Exception:
            raise Exception(["Payload must be a json parseable string, JSON Object, or JSON List"])
        return arg

    def get_service(self, token, service=None):
        self.token = token
        self.server_uri = rest.makeSplunkdUri()
        if not service:
            service = Splunkd(token=self.token, server_uri=self.server_uri)
        return service

    def handle(self, arg):
        try:
            arg = self.parse_arg(arg)
            splunkd = self.get_service(token=arg['session']['authtoken'])
            splunkd_system = self.get_service(token=arg['system_authtoken'])

            search_heads = []
            try:
                # Use the system-authenticated splunkd service as some users
                # will not have the capability to list search head cluster members.
                # (We do not expose this list, it is only used internally).
                search_heads = get_search_heads(splunkd_system)
            except Exception:
                # The shcluster status endpoints may throw if clustering is disabled.
                # We'll still want to return the diags from this host though, so
                # continue.
                pass

            if search_heads:
                body = splunkd.get('/services/diag/status', storageHost=search_heads).get('body').read()
            else:
                body = splunkd.get('/services/diag/status').get('body').read()

            if sys.version_info >= (3, 0):
                body = body.decode()
            return {'payload': body,
                    'status': 200}
        except Exception:
            return {'payload': 'Internal server error', 'status': 500}
