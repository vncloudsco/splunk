from __future__ import print_function

from splunk.clilib import literals
from lxml import etree
import getopt
import sys

__doc__ = """
          A pythonic representation of the mapping b/w cli commands and eai rest endpoints. The data structure is made up of a dictionary of dictionaries.
 
          To obtain an xml representation see the help:

             python rcCmds.py --help

          The primary data structure here is the dict remote_cmds. The keys of this dict map to the available EAI endpoints. Under each of the endpoints are listed the available actions that can be taken. Most of the items in this data struct are self explanatory. There are some nuances which are listed below:

          <name>:<objname>

                   When a key of a dict has this format it means that this object has some cutom parameters that need to be handled differently. eg.

                   show:license
                       uri: <foo...>
                   show
                       uri: <bar...>

                   The above example shows that when a user invokes a show command the <foo...> uri is invoked eg. ./splunk show minfreemb
                   But if the user invokes ./splunk show license, the <bar...> uri is invoked which is sufficiently diff that it could not be 
                   constructed easily via relative urls.

         <cliname>:<eainame>

                   Args in each section could have the above format. This means that the documentation in the cli calls the parameter by the name
                   'cliname', while the eai endpoint expects the same parameter to have the name 'eainame'. Only args which need a mapping need a mention in this list.

         default_eai_parms

                   Some endpoints require default parameters to be always sent in. Unfortunaletly the cli does not tell us these parameters too. eg. ./splunk enable local-index
                   The appropriate endpoint requires a name=default parameter to be sent in the POST request. The existing cli does not tell us that there is a parameter like
                   'name' that needs to be sent in too. In such cases, populate this with k,v pairs that your endpoint needs.

          required:
   
                    If present, it should be a list of cli field names that need to be present before any GET/POST can be made. Typically we should not
                    have to do required arguments checking at the cli client. But some endpoints do not check for these, so for now we have to do these checks.
                    I know, life sucks.

          prehooks

                    If present, it should name a function in rcHooks.py. Sometimes we have to do preprocessing on the cli args before we send them over
                    to splunkd. This is only on a case by case basis. For those endpoints that we do need this functionality, this method is called and provided with the cmd
                    obj and the cli args. This function should return a dict with all args processed in whatever fashion required. By default, the last function of this list is always 
                    map_args_cli_2_eai in rcHooks.py. i.e. the last pre processing function is always conversion to the eai equivalent names. 

          app_context

                    In some cases, an app context is required. But having the user to specify it via the -app argument always is a pain. The UI gets around this by doing a GET, getting the app
                    context and using this info for a second POST. This is now supported in the cli. Use the app_context dict to specify the uri to hit and provide a helper function (which should be 
                    in rcHooks.py) to parse the response and return the namespace.

          NOTES:
             1. splunkd will take care of determining 'pro'/'free' version requirements 
             2. splunk rc knows what actions the foll 'eai_type' maps to:(ie. they are implicit)
            
                   list => GET
                   create => POST
                   edit => POST
                   remove => DELETE

             3. the args 'auth','namespace' apply globally and can be used with any command
             4. the bridge framework will build the first part of the url i.e. servicesNS/... or services/...
             5. for help, if a help text is shared by multiple objects eg. add, list, remove, edit etc, they are listed under the //_common//help 
             6. This dict does not contain version/build info as the version cmd is currently handled by the splunk launcher
             7. All keys need a '_common' entry. This can be an empty dict, but it is required.


          """
__version__ = "1..0.0"
__copyright__ = """  Version 4.0"""
__author__ = 'Jimmy John'

NSMAP = { None : 'http://www.w3.org/2005/Atom',
         's': 'http://dev.splunk.com/ns/rest',
         'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'
        }

GLOBAL_ARGS = ['auth', 'namespace', 'uri', 'port']
GLOBAL_ACTIONS = {
                   'list': 'GET',
                   'create': 'POST',
                   'edit': 'POST',
                   'remove': 'DELETE',
                  }
GLOBAL_DEFAULTS = {
                   'list': 'list',
                   'add': 'create',
                   'edit': 'edit',
                   'remove': 'remove',
                  }

remote_cmds = {  
                 '_common':
                      {
                         'help':
                               {
                                'help': 'HELP_DEFAULT_LONG',
                                'splunk': 'HELP_DEFAULT_LONG',
                                'parameters': 'HELP_DEFAULT_LONG',
                                'parameter': 'HELP_DEFAULT_LONG',
                                '': 'HELP_DEFAULT_LONG',
                                'add': 'ADDEDIT_LONG',
                                'edit': 'ADDEDIT_LONG',
                                'extract': 'EXTRACT_I18N_LONG',
                                'clone-prep-clear-config': 'CLONE_PREP_CLEAR_CONFIG__LONG',
                                'list': 'LIST_LONG',
                                'remove': 'REMOVE_LONG',
                                'commands': 'COMMANDS_LONG',
                                'command': 'COMMANDS_LONG',
                                'uri': 'URI_LONG',
                                'port': 'PORT_LONG',
                                'ports': 'PORT_LONG',
                                'cheatsheet': 'CHEATSHEETSIMPLE_LONG',
                                'simple': 'CHEATSHEETSIMPLE_LONG',
                                'auth': 'AUTH_LONG',
                                'version': 'VERSION_LONG',
                                'splunk-version': 'VERSION_LONG',
                                'license': 'LICENSE_LONG', 
                                'input': 'INPUT_LONG',
                                'inputs': 'INPUT_LONG',
                                'file': 'FILE_LONG',
                                'dir': 'FILE_LONG',
                                'directory': 'FILE_LONG',
                                'path': 'FILE_LONG',
                                'pathname': 'FILE_LONG',
                                'local-index': 'LOCALINDEX_LONG',
                                'local': 'LOCALINDEX_LONG',
                                'datastore': 'DATASTORE_LONG',
                                'data': 'DATASTORE_LONG',
                                'store': 'DATASTORE_LONG',
                                'deploy-client': 'DEPLOYCLIENT_LONG',
                                'deploy-clients': 'DEPLOYCLIENT_LONG',
                                'client': 'DEPLOYCLIENT_LONG',
                                'exec': 'EXEC_LONG',
                                'forwarding': 'FORWARDING_LONG',
                                'distributed-search': 'DISTRIBUTED_SEARCH_LONG',
                                'cloning': 'DISTRIBUTED_SEARCH_LONG',
                                'routing': 'DISTRIBUTED_SEARCH_LONG',
                                'deployments': 'DISTRIBUTED_SEARCH_LONG',
                                'deployment': 'DISTRIBUTED_SEARCH_LONG',
                                'forward-server': 'FORWARDSERVER_LONG',
                                'forwardserver': 'FORWARDSERVER_LONG',
                                'search-server': 'SEARCHSERVER_LONG',
                                'searchserver': 'SEARCHSERVER_LONG',
                                'dist-search': 'DISTSEARCH_LONG',
                                'disable': 'DISABLEENABLE_LONG',
                                'enable': 'DISABLEENABLE_LONG',
                                'display': 'DISPLAY_LONG',
                                'deploy-server': 'DEPLOYSERVER_LONG',
                                'deployserver': 'DEPLOYSERVER_LONG',
                                'server': 'DEPLOYSERVER_LONG',
                                'boot-start': 'BOOTSTART_LONG',
                                'watchdog': 'MONITOR_LONG',
                                'rtsearch': 'RTSEARCH_LONG',
                                'realtime': 'RTSEARCH_LONG', 
                                'real-time': 'RTSEARCH_LONG',
                                'livetail': 'RTSEARCH_LONG',
                                'live-tail': 'RTSEARCH_LONG',
                                'anonymize': 'ANONYMIZE_LONG',
                                'blacklist': 'BLACKLIST_LONG',
                                'clean': 'CLEAN_LONG',
                                'create': 'CREATE_LONG',
                                'deploy-poll': 'DEPLOYPOLL_LONG',
                                'deploypoll': 'DEPLOYPOLL_LONG',
                                'poll': 'DEPLOYPOLL_LONG',
                                'eventdata': 'EVENTDATA_LONG',
                                'event': 'EVENTDATA_LONG',
                                'export': 'EXPORTIMPORT_LONG',
                                'find': 'FIND_LONG',
                                'globaldata': 'GLOBALDATA_LONG',
                                'global': 'GLOBALDATA_LONG',
                                'import': 'EXPORTIMPORT_LONG',
                                'package': 'PACKAGE_LONG',                                
                                'stop': 'CONTROL_LONG',
                                'start': 'CONTROL_LONG',
                                'restart': 'CONTROL_LONG',
                                'control': 'CONTROL_LONG',
                                'controls': 'CONTROL_LONG',
                                'splunkd': 'CONTROL_LONG',
                                'splunkweb': 'CONTROL_LONG',
                                'status': 'STATUS_LONG',
                                'server-status': 'STATUS_LONG',
                                'validate': 'VALIDATE_LONG',
                                'recover': 'RECOVER',
                                'spool': 'SPOOL_LONG',
                                'test': 'TESTTRAIN_LONG',
                                'tools': 'TOOLS_LONG',
                                'train': 'TESTTRAIN_LONG',
                                'training': 'TESTTRAIN_LONG',
                                'userdata': 'USERDATA_LONG',
                                'fifo': 'FIFO_LONG',
                                'logs': 'FIND_LONG',
                                'logout': 'LOGINLOGOUT_LONG',
                                'createssl': 'CREATESSL_LONG',
                                'validate-bundle': 'VALIDATE_BUNDLE',
                                'apply': 'APPLY',
                                'cluster': 'CLUSTER_LONG',
                                'clustering': 'CLUSTER_LONG',
                                'shcluster': 'SHPOOL_LONG',
                                'shclustering': 'SHPOOL_LONG',
                                'offline': 'OFFLINE_PEER',
                               },
                      },

                 'settings':
                      {
                       '_common':
                                {
                                 'uri': '/server/settings',
                                 #the cli docs calls the arg 'servername'. Internally the existing cli converts this to 'instancename'. Hence that is also included in the mapping
                                 'args': {'default-hostname':'host', 'datastore-dir':'SPLUNK_DB'},
                                 'help':
                                     {
                                        'show': 'SETSHOW_LONG',
                                        'set': 'SETSHOW_LONG',
                                        'settings': 'SETSHOW_LONG',
                                        'setting': 'SETSHOW_LONG',
                                     },
                                },
                       'show':
                              {
                                  'type': 'list',                                  
                              },
                       'show:license':
                              {
                                  'type': 'list',
                                  'uri': '/license/', 
                                  'eai_id': 'license',
                              },
                       'show:config':
                             {
                                  'type': 'list',
                                  'uri': '/properties/',
                                  'eai_id': '%(name)s',#name appears as the key in the argsDict with value <config> eg. {'name':'inputs'}
                              },
                       'set':
                              {       
                                  'type': 'edit',
                                  'eai_id': 'server-settings',
                              },
                       'set:default-index':
                              {
                                  'args': {'value':'srchIndexesDefault'},
                                  'uri': 'authorization/roles/',
                                  'type': 'edit',
                                  'eai_id': '%(role)s',
                                  'required': ['value'],
                                  'prehooks': ['conv_to_list'],
                              },
                       'enable:web-ssl':
                              {   
                                  'type': 'edit',
                                  'eai_id': 'server-settings',
                                  'default_eai_parms': {'enableSplunkWebSSL':'true'},
                              },
                       'disable:web-ssl':
                              {
                                  'type': 'edit',
                                  'eai_id': 'server-settings',
                                  'default_eai_parms': {'enableSplunkWebSSL':'false'},
                              },
                        'enable:webserver':
                              {
                                  'type': 'edit',
                                  'eai_id': 'server-settings',
                                  'default_eai_parms': {'startwebserver':'1'},
                              },
                       'disable:webserver':
                              {
                                  'type': 'edit',
                                  'eai_id': 'server-settings',
                                  'default_eai_parms': {'startwebserver':'0'},
                              },

                      },

                 'scripted':
                      {
                       '_common':
                                {
                                 'uri': '/data/inputs/script/',
                                 'args': {'source':'name', 'hostname':'host','hostregex':'host_regex', 'keep-open':'persistent'},
                                 'help':
                                     {
                                        'scripted': 'EXEC_LONG',
                                     },
                                },
                       #eg. ./splunk add scripted xyz.py -hostregex hostregex_val -hostname hostname_val -index main -interval interval_val -keep-open keep-open_val -sourcetype sourcetype_val -auth admin:changeme  OR
                       #./splunk add scripted -source xyz.py -hostregex hostregex_val -hostname hostname_val -index main -interval interval_val -keep-open keep-open_val -sourcetype sourcetype_val -auth admin:changeme
                       'add': {},
                       #eg. ./splunk list scripted
                       'list': {
                              'default_eai_parms': {'count':'-1'},
                              },
                       'edit':
                              {
                                  'eai_id': '%(source)s',
                              },
                       'remove':
                              {
                                  'eai_id': '%(source)s',
                              },
                        }, 

                 #the name of the user to add,edit,remove will appear as value of the arg key 'username' as default
                 'user':
                      {
                       '_common':
                                {
                                 'uri': '/authentication/users/',
                                 'args': {'username':'name', 'full-name':'realname', 'role':'roles' },
                                 'help':
                                    {
                                       'user': 'USER_LONG',
                                       'username': 'USER_LONG',
                                       'users': 'USER_LONG',
                                    },
                                }, 
                       #eg. ./splunk add user -username myuser -full-name myname -role Admin -password mypass  -auth admin:changeme
                       #eg. ./splunk add user myuser2 -full-name myname -role Admin -password mypass  -auth admin:changeme
                       'add': {},
                       'list': {
                              'default_eai_parms': {'count':'-1'},
                              },   
                       'edit':
                              {
                                  'eai_id': '%(username)s',
                              },
                       'remove':
                              {   
                                  'eai_id': '%(username)s',
                              },

                      },


                #the name of the file to be one shotted
                'oneshot':
                      {
                       '_common':
                                 {
                                   'uri': '/data/inputs/oneshot/',
                                   'args': {'source':'name'},
                                   'help': {},
                                 },
                       'add': {
                              'prehooks': ['make_path_absolute',],
                             },
                      },

                #the name of the file to be monitored for add,edit,remove will appear as value of the arg key 'source' as default
                'monitor':
                      {
                       '_common':
                                 {
                                   'uri': '/data/inputs/monitor/',
                                   'args': {'source':'name','hostname':'host', 'hostregex':'host_regex', 'hostsegmentnum':'host_segment', 'active-only':'eatonlylivefiles', 'follow-only':'followTail'},
                                   'help':
                                      {
                                        'monitor': 'TAIL_LONG',
                                        'tail': 'TAIL_LONG',
                                        'watch': 'WATCH_LONG',
                                      },
                                    'prehooks': ['make_path_absolute',],
                                 },
                       #eg. ./splunk add monitor -source /tmp/xxx.txt -sourcetype sourcetype -index main -hostname hostname -hostregex hostregex -hostsegmentnum hostsegmentnum -active-only active-only -follow-only true -auth admin:changeme
                       #eg. ./splunk add monitor /tmp/yyy.txt -sourcetype sourcetype -index main -hostname hostname -hostregex hostregex -hostsegmentnum hostsegmentnum -active-only active-only -follow-only true -auth admin:changeme
                       'add': {
                              'required': ['source'],
                             },
                       'list': {
                              'default_eai_parms': {'count':'-1'},
                              },
                       'edit':
                                 {
                                  'eai_id': '%(source)s',
                                 },
                       'remove':
                                 {
                                  'eai_id': '%(source)s',
                                 },

                         },

                 #the port to be listened on for add,edit,remove will appear as value of the arg key 'source' as default
                 'udp':
                     {
                      '_common':
                                {
                                   'uri': '/data/inputs/udp/',
                                   'args': {'source':'name', 'remotehost':'restrictToHost', 'hostname':'host', 'resolvehost':'connection_host'},
                                   'help':
                                      {
                                         'udp': 'TCPUDP_LONG',
                                      },
                                }, 
                      'list': {
                             'default_eai_parms': {'count':'-1'},
                             },   
                       #eg. ./splunk add udp -source 777 -hostname hostname -index main -sourcetype sourcetype -resolvehost abc -auth admin:changeme
                       #eg. ./splunk add udp  999 -hostname hostname -index main -sourcetype sourcetype -resolvehost abc -auth admin:changeme
                       'add': {},
                       'remove':
                           {
                               'eai_id': '%(source)s',
                            },
                       'edit':
                            {
                               'eai_id': '%(source)s',
                            },
                     }, 

                 #the port to be listened on for add,edit,remove will appear as value of the arg key 'source' as default
                 'tcp':
                     {
                      '_common':
                                {  
                                   'uri': '/data/inputs/tcp/raw/',
                                   'args': {'source':'name', 'remotehost':'restrictToHost', 'hostname':'host', 'resolvehost':'connection_host'},
                                   'help':
                                      {
                                        'tcp': 'TCPUDP_LONG',
                                      },
                                },
                      'list': {
                             'default_eai_parms': {'count':'-1'},
                             },
                       #eg. ./splunk add tcp -source 777 -hostname hostname -index main -sourcetype sourcetype -resolvehost abc -auth admin:changeme
                       #eg. ./splunk add tcp 999 -hostname hostname -index main -sourcetype sourcetype -resolvehost abc -auth admin:changeme
                       'add': {},
                       'edit':
                            {
                               'eai_id': '%(source)s',
                            },
                       'remove':
                             {     
                               'eai_id': '%(source)s',
                             }, 
                           },

                 #the add and remove operations require splunk to be restarted for the changes to take effect. Hence not supported.
                 #edit operation on forward-server is currently not supported.
                 'forward-server':
                    {
                      '_common':
                                {  
                                   'uri': '/data/outputs/tcp/server/',
                                   'args': {'hostport':'name'},
                                },
                      'list': {
                             'default_eai_parms': {'count':'-1'},
                             }, 
                      'add': {},
                      'remove':
                            {
                               'eai_id': '%(hostport)s',
                            },
                      'display:local-index':
                                {
                                   'uri': 'data/outputs/tcp/default/tcpout/',
                                   'type': 'list',
                                },
                      'enable:local-index':
                                {
                                   'uri': 'data/outputs/tcp/default/tcpout/',
                                   'type': 'create',
                                   'default_eai_parms': {'name':'default', 'indexAndForward':'true'},
                                },
                      'disable:local-index':
                                {
                                   'uri': 'data/outputs/tcp/default/tcpout/',
                                   'type': 'create',
                                   'default_eai_parms': {'name':'default', 'indexAndForward':'false'},
                                },
                   },

                   'distributed-search':
                    {
                      '_common':
                            {
                              'args': {'host':'name','url':'servers','servers':'name'},
                              'help': {'distributed':'DISTRIBUTED_SEARCH_LONG'},
                            },
                      'add:search-server':
                            {
                              'uri': '/search/distributed/peers/',
                              'type': 'create',
                            },
                      'remove:search-server':
                            {
                              'uri': '/search/distributed/peers/',
                              'eai_id': '%(url)s',
                              'type': 'remove', 
                            },
                      'edit:search-server': 
                            {
                              'uri':'/search/distributed/peers/%(url)s/%(action)s',# /%(url)s/%(action)s',
                              'type':'edit'
                            },
                      'list:search-server':
                            {
                                 'uri': '/search/distributed/peers/',
                                 'type': 'list',
                                 'default_eai_parms': {'count':'-1'},
                            },
                      'display:dist-search':
                            {
                               'uri': '/search/distributed/config/distributedSearch/',
                               'type': 'list',
                            },
                      'disable:dist-search':
                            {
                               'uri': '/search/distributed/config/distributedSearch/',
                               'type': 'edit',
                               'default_eai_parms': {'disabled':'True'},
                            },
                      'enable:dist-search':
                             {
                               'uri': '/search/distributed/config/distributedSearch/',
                                'type': 'edit',
                                'default_eai_parms': {'disabled':'False'},
                             },
                   },

                 'login':
                     {
                      '_common':
                                {
                                   'uri': '/auth/login/',
                                   'help':
                                      {
                                         'login': 'LOGINLOGOUT_LONG',
                                      },
                                },
                      'login':
                             {
                               'type': 'create',
                             },

                     },

                 'jobs':
                    {
                      '_common':
                                {
                                   'uri': '/search/jobs/',
                                   'args': {'dummy':'jobid'},
                                },
                      'list': {
                             'default_eai_parms': {'count':'0'},
                             },
                      'remove':
                             {
                              'eai_id': '%(jobid)s',
                             },
                      'show':
                            {
                             'type': 'list',
                             'eai_id': '%(jobid)s',
                            },
                      'display':
                           {
                             'type': 'list',
                             'eai_id': '%(jobid)s',
                           },
                     },

                 #the search name will appear as value of the arg key 'search' as default
                 'search':
                     {
                      '_common':
                                {
                                   'uri': '/search/jobs/',
                                   # the cli docs only specify these two options, while spacecake mentions many more...?
                                   'args': {'maxout':'max_count', 'maxtime':'timeout'},
                                   'required': ['terms'],
                                   'help':
                                      {
                                         'search': 'SEARCH_LONG',
                                         'searches': 'SEARCH_LONG',
                                         'searching': 'SEARCH_LONG',
                                         'search-help': 'SEARCH_LONG',
                                         'dispatch': 'DISPATCH_LONG',
                                         'search-fields': 'SEARCHFIELDS_LONG',
                                         'fields': 'SEARCHFIELDS_LONG',
                                         'search-field': 'SEARCHFIELDS_LONG',
                                         'search-modifiers': 'SEARCHMODIFIERS_LONG',
                                         'search-modifier': 'SEARCHMODIFIERS_LONG',
                                         'modifiers': 'SEARCHMODIFIERS_LONG',
                                         'modifier': 'SEARCHMODIFIERS_LONG',
                                         'search-commands': 'SEARCHCOMMANDS_LONG',
                                         'operators': 'SEARCHCOMMANDS_LONG',
                                         'search-operators': 'SEARCHCOMMANDS_LONG',
                                      },
                                },
                       'dispatch':
                             {
                               'type': 'create',
                             },
                       'search':
                             {
                               'type': 'create',
                             },

                     },

                  #the saved search name for add,edit,remove will appear as value of the arg key 'name' as default
                  'saved-search':         
                     {             
                      '_common':   
                                {
                                   'uri': '/saved/searches/',
                                   'args': {'terms':'search', 'schedule':'cron_schedule'},
                                   'help':
                                      {
                                        'saved-search': 'SAVEDSEARCH_LONG',
                                        'alert': 'SAVEDSEARCH_LONG',
                                        'alerts': 'SAVEDSEARCH_LONG',
                                        'savedsearch': 'SAVEDSEARCH_LONG',
                                      },
                                },
                      'list': {
                             'default_eai_parms': {'count':'-1'},
                             },
                      'add': {
                             'prehooks': ['parse_saved_search'],
                            },
                      'edit':
                            {
                               'eai_id': '%(name)s',
                               'prehooks': ['parse_saved_search'],
                            },
                      'remove':
                             {  
                               'eai_id': '%(name)s',
                             },
                    },

                  'app':
                      {
                      '_common':
                                {
                                   'uri': '/apps/local/',
                                   'args': {'dummy':'name'},
                                },
                      'display:app':
                               {
                                  'eai_id': '%(name)s',
                                  'type': 'list',
                                  'default_eai_parms': {'count':'-1', 'name':''},
                               },
                      'edit:app':
                               {
                                  'eai_id': '%(name)s',
                                  'type': 'edit',
                               },
                      'disable:app':
                               {
                                  'uri': '/apps/local/%(name)s/disable',
                                  'type': 'edit',
                               },
                      'enable:app':
                               {
                                  'uri': '/apps/local/%(name)s/enable',
                                  'type': 'edit',
                               },
                      'remove:app':
                               {
                                  'eai_id': '%(name)s',
                               },
                      'create:app':
                               {
                                  'type': 'create',
                               },    
                      'package:app':
                               {
                                  'uri': '/apps/local/%(name)s/package/',
                                  'type': 'list',
                               },     
                      'install:app':
                               {
                                  'uri': '/apps/appinstall/',
                                  'type': 'create',
                               },
                    },

                  'deployments':
                     {
                      '_common':
                                {
                                   'help':
                                      {
                                         'refresh': 'REFRESH',
                                         'reload': 'RELOAD_LONG',
                                      },
                                },
                      'enable:deploy-client':
                                {
                                     'uri': '/deployment/client/config',
                                     'type': 'edit',
                                },
                      'disable:deploy-client':
                                {
                                     'uri': '/deployment/client/config/',
                                     'type': 'edit',
                                     'default_eai_parms': {'disabled':'true'},
                                },
                      'display:deploy-client':
                                {
                                     'uri': '/deployment/client/config/',
                                     'type': 'list',
                                },
                      'display:deploy-server':
                               {
                                  'uri': '/deployment/server/config/listIsDisabled',
                                  'type': 'list',
                               },
                      'enable:deploy-server':
                               {
                                   'uri': '/deployment/server/config/config/enable',
                                   'type': 'list',
                               },
                      'refresh:deploy-clients':
                              {
                                    'uri': '/deployment/client',
                                    'type': 'list', 
                              },
                      'list:deploy-clients':
                              {
                                    'uri': '/deployment/server/clients',
                                    'default_eai_parms': {'count':'-1'},
                                    'type': 'list',
                              },
                      'reload:deploy-server':
                               {
                                    'uri': '/deployment/server/config/_reload',
                                    'type': 'edit', 
                               },
                      'disable:deploy-server':
                               {
                                   'uri': '/deployment/server/config/config/disable',
                                   'type': 'list',
                               },
                      'show:deploy-poll':
                               {
                                  'uri': '/admin/deploymentclient/',
                                  'type': 'list',
                               },
                      'set:deploy-poll': 
                               {
                                   'args': {'uri':'targetUri'},
                                   'uri': '/admin/deploymentclient/deployment-client/',
                                   'type': 'edit',
                                   'default_eai_parms': {'disabled':'false'},
                               },
                    },

                    'role-mappings':
                     {
                        '_common':
                                 {},
                        'list':
                                  {
                                     'uri': 'admin/LDAP-groups/',
                                     'default_eai_parms': {'count':'-1'},
                                     'type': 'list',
                                  },
                      },
                    'auth-method':
                      {
                         '_common':
                                {
                                   'uri': '/authentication/providers/',
                                   'args': {'auth-type':'authType'},
                                },
                         'add': 
                                {
                                  'eai_id': '%(authType)s',
                                  'default_eai_parms': {'name':'dummy'},
                                },
                         'list': 
                                {
                                  'eai_id': {
                                              'uri': 'authentication/providers/services/active_authmodule',
                                              'type': 'list',
                                              'filter': 'active_authmodule',
                                            },
                                },
                         'edit': 
                                {
                                  'eai_id': '%(authType)s',
                                  'default_eai_parms': {'name':'dummy'},
                                },
                         'show:auth-method':
                                  {
                                     'uri': 'authentication/providers/services/active_authmodule',
                                     'type': 'list',
                                  },
                         'reload:auth':
                                  {
                                     'uri': 'authentication/providers/services/_reload',
                                     'type': 'edit',
                                  },

                    },



              }

# ---------------
def print_xml():
   """
   pretty prints out the dict in an xml format
   """
   root = create_xml(remote_cmds)
   
   print(etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True))

# ----------------
def serialize(d):
   """
   returns a serialized string of the dict
   """
   s = ''
   for ele in d:
      s += ' %s="%s"' % (ele, d[ele])
   return s

# ----------
def usage():
   """
   prints out the usage string
   """
   print('\nUsage:\n')
   print('''python rcCmds.py -x <or> python rcCmds.py --xml\n''')

# ----------------------------------------
def create_node_with_text(name, text):
   """
   helper function that returns an Element node with 'name' and contents 'text'
   """
   d = etree.Element(name)
   d.text = text

   return d

# -----------------------------------------------------------------------
def create_node_with_attrib_and_text(name, attribval, text):
   """
   helper function that returns an Element node with 'name', 'attrib' and contents 'text'
   """
   d = etree.Element(name, name='%s' %  attribval)
   d.text = text

   return d

# ------------------
def make_ordered(l):
   """
   returns the list l with the first element as '_common'
   """
   index = l.index('_common')
   l[0], l[index] = l[index], l[0]
   return l

# -----------------
def parse_args(d):
   """
   parses a dict 'd' containing 'args' and returns a lxml node containing all this info
   """

   args_node = etree.Element("args")
   for p in d['args']:
      args_node.append( etree.Element("arg", cli_label='%s' % p, eai_label='%s' % d['args'][p]) )

   return args_node

# ----------------
def parse_help(d):
   """
   parses a dict 'd' containing 'help' and returns a lxml node containing all this info
   """
   help_node = etree.Element("help")
   for p in d['help']:
      help_node.append( create_node_with_attrib_and_text('helptext', p, d['help'][p]) )

   return help_node

# ----------------------------
def create_xml(remote_cmds):
   """
   returns an lxml structure of the remote_cmds dict
   """

   root = etree.Element("feed", nsmap=NSMAP)

   root.append( etree.Comment(''' splunk rc knows what actions the foll 'eai_type' maps to:(ie. they are implicit)
            
                   list => GET
                   create => POST
                   edit => POST
                   remove => DELETE

                  splunik rc also has knowledge of the following parameters for all commands:(ie. they are implicit)

                  'auth','namespace', 'uri', 'port'
                  ''') )
   
   for obj in make_ordered(list(remote_cmds)):

       if obj == '_common':
          if 'args' in remote_cmds['_common']:
             root.append( parse_args(remote_cmds['_common']) )

          help = etree.Element("help")
          for ele in remote_cmds['_common']['help']:
             if ele == '_default':
                continue
             help.append( create_node_with_attrib_and_text('helptext', '%s' % ele, remote_cmds['_common']['help'][ele]) ) 
          root.append(help)
          continue

       d = etree.Element("configuration", name='%s' % obj)
       d.append( create_node_with_text('uri', remote_cmds[obj]['_common']['uri']))

       #iterate through the 'verbs'
       for cmd in make_ordered(list(remote_cmds[obj])):

          if cmd == '_common':
             if 'args' in remote_cmds[obj]['_common']:
                args_node = parse_args(remote_cmds[obj]['_common'])
                d.append( args_node ) 
             if 'help' in remote_cmds[obj]['_common']:
                help_node = parse_help(remote_cmds[obj]['_common'])
                d.append( help_node )
             continue

          try:
             type = remote_cmds[obj][cmd]['type']
          except KeyError:
             type = GLOBAL_DEFAULTS[cmd]

          try:
             cmd_node = etree.Element("action", cli_arg='%s' % cmd, eai_type='%s' % type, eai_id='%s' % remote_cmds[obj][cmd]['eai_id'])
          except:
             cmd_node = etree.Element("action", cli_arg='%s' % cmd, eai_type='%s' % type) #no eai_id

          try:
             cmd_node.attrib['uri'] = remote_cmds[obj][cmd]['uri']
          except:
             pass #uri is not different from that inherited

          try:
             cmd_node.attrib['default_eai_parms'] = '&'.join(['%s=%s' % (x[0], x[1]) for x in remote_cmds[obj][cmd]['default_eai_parms'].items()])
          except:
             pass #there are no defauly eai parameters to send with this request

          if 'args' in remote_cmds[obj][cmd]:
             new_args_node = parse_args(remote_cmds[obj][cmd])
             cmd_node.append( new_args_node )

          if 'help' in remote_cmds[obj][cmd]:
             cmd_node.append( parse_help(remote_cmds[obj][cmd]) )

          d.append(cmd_node)
          
       root.append(d)

   
   return root
 
# --------------------------
# --------------------------
if __name__ == '__main__':

    #only internal folks would need the xml printed out. 
    try:
       optlist, ignore = getopt.getopt(sys.argv[1:], 'xh', ['xml', 'help'])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err)) # eg. "option -<blah> not recognized"
        usage()
        sys.exit()

    for o, a in optlist:
       if o in ['-x', '--xml']:
          print_xml()
       elif o in ['-h', '--help']:
          usage()
          sys.exit()
       else:
            assert False, "unhandled option"




