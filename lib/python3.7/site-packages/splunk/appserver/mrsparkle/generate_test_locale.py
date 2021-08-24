from __future__ import print_function
# 1. run this in $SPLUNK_HOME/lib/python2.7/site-packages/splunk/appserver/mrsparkle/locale
# 2. pass in args of: <path to messages.pot> <locale directory> <msgfmt path>
#    default values will be used if no arg present
# 3. I test using th-TH 
# 4. splunk restart

from builtins import range
import sys, os, subprocess, os.path, re, shutil

pot_filename = None
output_dir = None
msgfmt_path = None

if len(sys.argv) > 1:
    pot_filename = sys.argv[1]
else:
    pot_filename = os.path.join(os.environ.get('SPLUNK_HOME'),
                                'lib', 'python2.7', 'site-packages',
                                'splunk', 'appserver', 'mrsparkle', 'locale',
                                'messages.pot')    
if len(sys.argv) > 2:
    output_dir = sys.argv[2] 
else:
    output_dir = os.path.join(os.environ.get('SPLUNK_HOME'),
                              'lib', 'python2.7', 'site-packages',
                              'splunk', 'appserver', 'mrsparkle', 'locale',
                              'th_TH')

if len(sys.argv) > 3:
    msgfmt_path = sys.argv[3]
else:
    msgfmt_path = os.path.join(os.environ['SPLUNK_SOURCE'], 'contrib/Python-2.7.11/Tools/i18n/msgfmt.py')

print('pot_filename=%s' % pot_filename)
print('output_dir=%s' % output_dir)
print('msgfmt_path=%s' % msgfmt_path)

if pot_filename is None or output_dir is None:
    print('Unspecified pot_filename or output_dir')
    exit(-1)

# clear out output director
shutil.rmtree(output_dir, ignore_errors=True)

#
# build locale directory
#
os.mkdir(output_dir)
lc_messages_dir = os.path.join(output_dir, 'LC_MESSAGES')
os.mkdir(lc_messages_dir)

#
# build po file
#
po_filename = 'messages.po'

pot_file = open(pot_filename, 'r')
po_file = open(os.path.join(lc_messages_dir, po_filename), 'a')

test = 0
msglines = []
matcher = re.compile('\"(\\\"|[^"])*\"')
for line in pot_file:
    if "msgid" in line:
        msglines = []

    if "msgstr" in line:
        output_msglines = []
        for msgline in msglines:
            # translate everything but backslahed characters and string formatting i.e. %s %(name)s
            splits = re.split('(\\\\.|%s|%\([^\)]*\)s)', msgline)
            outputsplits = []
            for split in splits:
                outputsplit = split
                if split.startswith('%') == False:
                    if split.startswith('\\') == False:
                        outputsplit = re.sub('\w', 'X', split)
                outputsplits.append(outputsplit)
             
            output_msglines.append("".join(outputsplits))

        if len(output_msglines) > 0:
            po_file.write(line.replace('""', '%s' % output_msglines[0]))       
        if len(output_msglines) > 1:
            for i in range(1, len(output_msglines)):
                po_file.write('%s\n' % output_msglines[i])
    else: 
        match = matcher.search(line)
        if match:
            msglines.append('%s' % match.group(0))

        po_file.write(line)

pot_file.close()
po_file.close()   

#
# build mo file
#
os.chdir(lc_messages_dir)
subprocess.call([msgfmt_path, po_filename])
