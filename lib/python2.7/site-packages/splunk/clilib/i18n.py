#
# Extracts text to be translated from python, javascript and mako templates
# and compiles it into a .pot file


import sys, os.path
from babel.messages import frontend
import splunk.clilib.cli_common as comm
from splunk.clilib.bundle_paths import make_splunkhome_path

def i18n_extract(args, fromCLI):
    splunk_home = comm.splunk_home
    params_req = ('app',)
    params_opt = ()
    comm.validateArgs(params_req, params_opt, args)

    app_path = make_splunkhome_path(['etc', 'apps', args['app']])
    app_locale_path = os.path.join(app_path, 'locale')
    if not os.path.exists(app_locale_path):
        os.makedirs(app_locale_path)

    messages_pot = os.path.join(app_locale_path, 'messages.pot')

    babel_cfg = os.path.join(app_locale_path, 'babel.cfg')
    if not os.path.exists(babel_cfg):
        from splunk.appserver import mrsparkle
        mrsparkle = os.path.dirname(mrsparkle.__file__)
        babel_cfg = os.path.join(mrsparkle, 'locale', 'babel.cfg')
    
    args = [ 
        'extract', 
        '-F', babel_cfg,
        '-c', 'TRANS:',
        '-o', messages_pot,
        '--sort-output',
        app_path
        ]

    sys.argv[1:] = args

    frontend.main()
