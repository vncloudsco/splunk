#!/opt/splunk/bin/python
#
# Extracts text to be translated from python, javascript and mako templates
# and compiles it into a .pot file
#
# also stores all strings found in .js files in a python pickle cache file
# to accelerate lookup times from splunkweb


from __future__ import absolute_import
from __future__ import print_function
from builtins import range
import sys
import os
import os.path
import time
from babel.messages import frontend
from babel.messages.pofile import unescape
import babel.util
import babel.messages.extract
import pickle
from tempfile import NamedTemporaryFile
import splunk.util

HEADER = u"""\
# Translations for Splunk
# Copyright (C) 2005-%(year)s Splunk Inc. All Rights Reserved.
""" % {'year': time.strftime('%Y') }

def processFilename(line):
    fn = line[2:].rsplit(':',1)[0].strip() # split off the line number
    try:
        # strip the relative portion of the filename
        fn = fn[fn.rindex('../')+3:]
    except ValueError:
        pass
    # hack for search_mrsparkle directories
    if fn.startswith('web/'):
        fn = fn[4:]
    return fn


# Really ugly hack to exclude contrib paths from being extracted
def custom_pathmatch(pattern, filename):
    if 'contrib/' in filename or 'contrib\\' in filename:
        return False
    return babel.util.pathmatch(pattern, filename)
babel.messages.extract.pathmatch = custom_pathmatch


def main():
    if not os.path.isdir('locale'):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        os.chdir(script_dir)

    if len(sys.argv) == 1:
        locale_dir = 'locale'
    elif len(sys.argv) == 2:
        locale_dir = sys.argv[1]
    else:
        print("Usage: i18n-extract.py [<locale path>]")
        sys.exit(1)

    splunk_home = os.environ.get('SPLUNK_HOME')
    if not splunk_home:
        print("SPLUNK_HOME environment variable was not set!")
        sys.exit(2)
    locale_dir = os.path.realpath(locale_dir)
    pot_output = os.path.join(locale_dir, 'messages.pot')

    print('$SPLUNK_HOME: %s' % splunk_home)
    print('Locale directory: %s' % locale_dir)
    print('POT output: %s' % pot_output)
    print('')

    if locale_dir.startswith(splunk_home):
        strip = splunk_home.replace(os.path.sep, '/')
        strip = (strip+'/share/splunk', strip, 'etc/apps/')
        from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
        template_dir = make_splunkhome_path(['share', 'splunk', 'search_mrsparkle'])
        default_dir = make_splunkhome_path(['etc', 'system', 'default'])
        search_app = make_splunkhome_path(['etc', 'apps', 'search'])
        launcher_app = make_splunkhome_path(['etc', 'apps', 'launcher'])
        datapreview_app = make_splunkhome_path(['etc', 'apps', 'splunk_datapreview'])
        monitoring_console_app = make_splunkhome_path(['etc', 'apps', 'splunk_monitoring_console'])
        instance_monitoring_app = make_splunkhome_path(['etc', 'apps', 'splunk_instance_monitoring'])
        dmcv2_app = make_splunkhome_path(['etc', 'apps', 'dmc'])
        webhook_app = make_splunkhome_path(['etc', 'apps', 'alert_webhook'])
    else:
        # assume this is an extraction from the source tree
        strip = ('../../../../../web', '../../../../../', 'cfg/bundles/')
        template_dir = '../../../../../web/search_mrsparkle'
        default_dir = '../../../../../cfg/bundles/default'
        search_app = '../../../../../cfg/bundles/search'
        launcher_app = '../../../../../cfg/bundles/launcher'
        datapreview_app = '../../../../../cfg/bundles/splunk_datapreview'
        monitoring_console_app = '../../../../../cfg/bundles/splunk_monitoring_console'
        instance_monitoring_app = '../../../../../cfg/bundles/splunk_instance_monitoring'
        dmcv2_app  = '../../../../../cfg/bundles/dmc'
        webhook_app = '../../../../../cfg/bundles/alert_webhook'

    # this is always relative to the script directory
    search_helper_dir = '../../searchhelp'

    with open(pot_output, 'w') as pot_outfile, NamedTemporaryFile() as babel_outfile_temp:
        args = [
            'extract',
            '-F',  os.path.join(locale_dir, 'babel.cfg'),
            '-c', 'TRANS:',
            '-k', 'deferred_ugettext',
            '-k', 'deferred_ungettext',
            '-o', babel_outfile_temp.name,
            '--sort-output',
            '.',
            template_dir,
            default_dir,
            search_app,
            launcher_app,
            datapreview_app,
            monitoring_console_app,
            instance_monitoring_app,
            dmcv2_app,
            webhook_app
            ]

        sys.argv[1:] = args

        # Do the extraction
        frontend.main()

        pot_outfile.write(HEADER + "\n")
        currentfn = []
        filemapping = {}
        msgid = msgid_plural = None
        for line in babel_outfile_temp:
            line = splunk.util.toDefaultStrings(line)
            line = line.strip()
            if line.startswith('# '):
                # strip the original comment header
                continue
            if line[:3] != '#: ': # filename:linenum references begin with #:
                pot_outfile.write(line + "\n")
                if currentfn:
                    # capture the translation associated with the current filename(s)
                    if line.startswith('msgid '):
                        msgid = unescape(line[6:])
                    elif line.startswith('msgid_plural '):
                        msgid_plural = unescape(line[13:])
                    elif line.startswith('"'):
                        # multi-line translation
                        if msgid is not None:
                            msgid = msgid + unescape(line)
                        elif msgid_plural is not None:
                            msgid_plural = msgid_plural + unescape(line)
                continue
            if msgid and currentfn:
                for fn in currentfn:
                    fn = fn.lower()
                    if fn.find('data' + os.sep + 'ui') > -1:
                        fn = os.path.splitext(os.path.basename(fn))[0]
                    filemapping.setdefault(fn, []).append( (msgid, msgid_plural) )
                msgid = msgid_plural = None
                currentfn = []
            newline = '#: '
            fnpairs = line[3:].split(' ')
            for fnpair in fnpairs:
                fn, ln = fnpair.rsplit(':', 1) if ':' in fnpair else (fnpair, 0)
                for prefix in strip:
                    if fn.startswith(prefix):
                        fn = fn[len(prefix):].strip('/')
                # keep track of js files
                if fn.endswith('.js') or fn.find('data' + os.sep + 'ui') > -1:
                    currentfn.append(fn)
                newline += "%s:%s " % (fn, ln)
            pot_outfile.write(newline + "\n")

    # collect the final message
    if msgid and currentfn:
        for fn in currentfn:
            if fn.find('data' + os.sep + 'ui') > -1:
                fn = os.path.splitext(os.path.basename(fn))[0]
            filemapping.setdefault(fn.lower(), []).append( (msgid, msgid_plural) )

    # pickle the lookup data
    with open(os.path.join(locale_dir, "messages-filecache.bin"), 'wb') as cachefile:
        pickle.dump(filemapping, cachefile, 2)

if __name__=='__main__':
    main()
