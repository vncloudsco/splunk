from __future__ import absolute_import
from __future__ import print_function
#   Version 4.0
#
# Intersplunk provides simple access to the comm protocol between Splunk search
# operators.
#
# The intersplunk format is plain CSV, with a first-line field header.
#
# Usage: see test cases below.
#

from builtins import zip
from builtins import range
import csv 
import sys 
import copy
import re
if sys.version_info >= (3, 0):
    from io import (BytesIO, TextIOWrapper)
else:
    from StringIO import StringIO
    BytesIO = StringIO
from future.moves.urllib import parse as urllib_parse
import os

# set the maximum allowable CSV field size
#
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for
# the background on issues surrounding field sizes.
# (this method is new in python 2.5)
csv.field_size_limit(10485760)

MV_ENABLED = True

def set_binary_mode(fileobj):
    # Pylint can't handle platform-dependent code.
    # pylint: disable-all

    # This works around a design error in Intersplunk where it assumes that the
    # bytes it writes to stdout will be identical to the bytes which are
    # emitted.
    # This is false on windows where \n is mapped to \r\n
    # The typical solution is to simply open the file in binary mode, but stdout
    # is already open, thus this hack
    if sys.platform == 'win32':
        import msvcrt
        msvcrt.setmode(fileobj.fileno(), os.O_BINARY)

def default_stdout_stream():
    if sys.version_info >= (3, 0):
        return sys.stdout.buffer
    set_binary_mode(sys.stdout)
    return sys.stdout

def splunkHome():
    import os
    return os.path.normpath(os.environ["SPLUNK_HOME"])

def isGetInfo(args):
    if (len(args) >= 2) and (args[1] == "__GETINFO__"):
        newargs = [args[0]]
        newargs.extend(args[2:])
        return (True, newargs)
    elif (len(args) >= 2) and (args[1] == "__EXECUTE__"):
        newargs = [args[0]]
        newargs.extend(args[2:])
        return (False, newargs)
    else: # invalid invocation, exit and return error message immediately
        generateErrorResults("Unexpected first argument to script, expected '__GETINFO__' or '__EXECUTE__'.")
        sys.exit()

def parseError(msg):
    generateErrorResults(msg)
    sys.exit()

def outputInfo(streaming, generating, retevs, reqsop, preop, timeorder=False, clear_req_fields=False, req_fields = None):
    infodict = {
        'streaming_preop' : preop,
        'streaming' : '0',
        'generating' : '0',
        'retainsevents' : '0',
        'requires_preop' : '0',
        'generates_timeorder' : '0',
        'overrides_timeorder' : '1',
        'clear_required_fields' : '0' }
    
    if streaming:
        infodict['streaming'] = '1'
    
    if generating:
        infodict['generating'] = '1'
        if timeorder:
            infodict['generates_timeorder'] = '1'
    else:
        if timeorder:
            infodict['overrides_timeorder'] = '0'

    if retevs:
        infodict['retainsevents'] = '1'

    if reqsop:
        infodict['requires_preop'] = '1'

    if clear_req_fields:
        infodict['clear_required_fields'] = '1'

    if req_fields is not None and len(req_fields) > 0:
        infodict['required_fields'] = req_fields

    outputResults([ infodict ], mvdelim=',')
    sys.exit()

'''
For multivalues, values are wrapped in '$' and separated using ';'
Literal '$' values are represented with'$$'
'''
def getEncodedMV(vals):
    s = ""
    for val in vals:
        val = val.replace('$', '$$')
        if len(s):
            s += ';'
        s += '$' + val + '$'
    return s


def decodeMV(s, vals):
    if len(s) == 0:
        return False

    tok = ""
    inval = False

    i = 0
    while i < len(s):
        if not inval:
            if s[i] == '$':
                inval = True
            elif s[i] != ';':
                return False
        else:
            if s[i] == '$' and i+1 < len(s) and s[i+1] == '$':
                tok += '$'
                i += 1
            elif s[i] == '$':
                inval = False
                vals.append(tok)
                tok = ""
            else:
                tok += s[i]
        i += 1
    return True


def addMessage(messages, msg, key):
    if key not in messages:
        messages[key] = []
    messages[key].append(msg)
    
def addInfoMessage(messages, msg):
    addMessage(messages, msg, "info_message")
def addWarnMessage(messages, msg):
    addMessage(messages, msg, "warn_message")
def addErrorMessage(messages, msg):
    addMessage(messages, msg, "error_message")

def outputResults(results, messages = None, fields = None, mvdelim = '\n', outputfile = None):
    '''
    Outputs the contents of a result set to STDOUT in Interplunk
    format, for consumption by the next search processor.
    '''

    if outputfile is None:
        outputfile = default_stdout_stream()
    
    if messages != None:
        # message header is everything before the first empty line, similar to the input
        # header format.  also key = value, with stripping of whitespace
        for level, messages in messages.items():
            for msg in messages:
                msg = "%s=%s\n" % (level, msg)
                if sys.version_info >= (3, 0):
                    msg = msg.encode()
                outputfile.write(msg)
        outputfile.write(b"\n")
    
    if results == None:
        return

    s = set()
    l = []

    '''
    Check each entry to see if it is a list (multivalued). If so, set
    the multivalued key to the proper encoding Replace the list with a
    newline separated string of the values
    '''
    for i in range(len(results)):
        for key in list(results[i].keys()): # We wrapped the call to keys() in a list() for py3's dictionary changed size during iteration.
            if(isinstance(results[i][key], list)):
                results[i]['__mv_' + key] = getEncodedMV(results[i][key])
                results[i][key] = mvdelim.join(results[i][key])
        for k in list(results[i].keys()): # We wrapped the call to keys() in a list() for py3's dictionary changed size during iteration.
            if not k in s:
               s.add(k)
               l.append(k)
        #s.update(results[i].keys())

    if fields is None:
        h = l
    else:
        h = fields

    if sys.version_info >= (3, 0):
        outputfile = TextIOWrapper(outputfile, encoding = 'utf-8', write_through = True)
    dw = csv.DictWriter(outputfile, h, extrasaction='ignore')

    dw.writerow(dict(zip(h, h)))
    dw.writerows(results)
    if sys.version_info >= (3, 0):
        outputfile.detach() # Don't close the underlying file


def outputStreamResults(results, version = "4.3", header = None, mvdelim = '\n', outputfile = None):

    if outputfile is None:
        outputfile = default_stdout_stream()

    header_io = BytesIO()
    header_str = b""
    if header is not None:
        outputResults(header, None, None, mvdelim, header_io)
        header_str = header_io.getvalue()
        header_io.close()

    body_io = BytesIO()
    body_str = b""
    outputResults(results, None, None, mvdelim, body_io)
    body_str = body_io.getvalue()
    body_io.close()

    if sys.version_info >= (3, 0):
        version = version.encode()
    outputfile.write(b"splunk %s,%d,%d\n" % (version, len(header_str), len(body_str)))
    if len(header_str) > 0:
        outputfile.write(header_str)
    if len(body_str) > 0:
        outputfile.write(body_str)

def generateErrorResults(errorStr):
    '''
    Generates a properly formatted error message for use by the
    outputResults() method.
    '''
    h = ["ERROR"]
    results = [ {"ERROR": errorStr} ]
    outputfile = default_stdout_stream()
    if sys.version_info >= (3, 0):
        outputfile = TextIOWrapper(outputfile, encoding = 'utf-8', write_through = True)
    dw = csv.DictWriter(outputfile, h)
    dw.writerow(dict(zip(h, h)))
    dw.writerows(results)
    if sys.version_info >= (3, 0):
        outputfile.detach() # Don't close the underlying file
    # return [{"ERROR": errorStr}]
    return None # legacy calls tried to use this value.


def readResults(input_buf = None, settings = None, has_header = True):
    '''
    Converts an Intersplunk-formatted file object into a dict
    representation of the contained events.
    '''

    if input_buf == None:
        if sys.version_info >= (3, 0):
            input_buf = TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
        else:
            input_buf = sys.stdin

    results = []

    if settings == None:
        settings = {} # dummy

    if has_header:
        # until we get a blank line, read "attr:val" lines, setting the values in 'settings'
        attr = last_attr = None
        while True:
            line = input_buf.readline()
            line = line[:-1] # remove lastcharacter(newline)
            if len(line) == 0:
                break

            colon = line.find(':')
            if colon < 0:
                if last_attr:
                   settings[attr] = settings[attr] + '\n' + urllib_parse.unquote(line)
                else:
                   continue

            # extract it and set value in settings
            last_attr = attr = line[:colon]
            val  = urllib_parse.unquote(line[colon+1:])
            settings[attr] = val

    csvr = csv.reader(input_buf)
    header = []
    first = True
    mv_fields = []
    for line in csvr:
        if first:
            header = line
            first = False
            # Check which fields are multivalued (for a field 'foo', '__mv_foo' also exists)
            if MV_ENABLED:
                for field in header:
                    if "__mv_" + field in header:
                        mv_fields.append(field)
            continue

        # need to maintain field order
        import splunk.util as util
        result = util.OrderedDict()
        i = 0
        for val in line:
            result[header[i]] = val
            i = i+1

        for key in mv_fields:
            mv_key = "__mv_" + key
            if key in result and mv_key in result:
                # Expand the value of __mv_[key] to a list, store it in key, and delete __mv_[key]
                vals = []
                if decodeMV(result[mv_key], vals):
                    result[key] = copy.deepcopy(vals)
                    if len(result[key]) == 1:
                        result[key] = result[key][0]
                    del result[mv_key]

        results.append(result)

    return results


def getOrganizedResults(input_str = None):
    '''
    Converts an Intersplunk-formatted file object into a dict
    representation of the contained events, and returns a tuple of:
    
        (results, dummyresults, settings)
        
    "dummyresults" is always an empty list, and "settings" is always
    an empty dict, since the change to csv stopped sending the
    searchinfo.  It has not been updated to store the auth token.
    '''

    settings = {}
    dummyresults = []

    results = readResults(input_str, settings)

    return results, dummyresults, settings


def rawresultsToString(results):
    '''
    Extracts the raw event data from a result set and returns all of
    them as a single CR-delimited string.
    '''

    # TODO: is this method still being used?
    # TODO: this can be optimized by list comprehensions
    rawresults = []
    for result in results:
        for k, v in result.items():
            if k == "_raw":
                rawresults.append(v)
    resultstext = "\n".join(rawresults)
    return resultstext


def win32_utf8_argv():                                                                                               
    """Uses shell32.GetCommandLineArgvW to get sys.argv as a list of UTF-8                                           
    strings.                                                                                                         
                                                                                                                     
    Versions 2.5 and older of Python don't support Unicode in sys.argv on                                            
    Windows, with the underlying Windows API instead replacing multi-byte                                            
    characters with '?'.                                                                                             
                                                                                                                     
    Returns None on failure.                                                                                         
                                                                                                                     
    Example usage:                                                                                                   
                                                                                                                     
    >>> def main(argv=None):                                                                                         
    ...    if argv is None:                                                                                          
    ...        argv = win32_utf8_argv() or sys.argv                                                                  
    ...                                                                                                              
    """                                                                                                              

    if sys.version_info >= (3, 0):
        return sys.argv

    try:                                                                                                             
        from ctypes import POINTER, byref, cdll, c_int, windll                                                       
        from ctypes.wintypes import LPCWSTR, LPWSTR                                                                  
                                                                                                                     
        GetCommandLineW = cdll.kernel32.GetCommandLineW                                                              
        GetCommandLineW.argtypes = []                                                                                
        GetCommandLineW.restype = LPCWSTR                                                                            
                                                                                                                     
        CommandLineToArgvW = windll.shell32.CommandLineToArgvW                                                       
        CommandLineToArgvW.argtypes = [LPCWSTR, POINTER(c_int)]                                                      
        CommandLineToArgvW.restype = POINTER(LPWSTR)                                                                 
                                                                                                                     
        cmd = GetCommandLineW()       

        argc = c_int(0)                                                                                              
        argv = CommandLineToArgvW(cmd, byref(argc))                                                                  
        if argc.value > 0:                                                                                           
            # Remove Python executable if present                                                                    
            if argc.value - len(sys.argv) == 1:                                                                      
                start = 1                                                                                            
            else:                                                                                                    
                start = 0                                                                                            
            return [argv[i].encode('utf-8') for i in
                    range(start, argc.value)]
    except Exception:                                                                                                
        pass


def getKeywordNewlineSafe(arg, argname):
    argnamelen = len(argname)
    if arg.startswith('"') and arg.endswith('"'):
        arg = arg[1:-1]
    if arg.startswith(argname):
        # pick off just the search string and construct the list
        # technically we could have gotten '::' or '==' and not just '='
        if arg.startswith("%s::" % argname) or arg.startswith("%s==" % argname):
            val = arg[argnamelen+2:]
        else:
            val = arg[argnamelen+1:]
        return [(argname, '=', val)]
    else:
        return []

# from sys.argv, get key=value args as well as other plain keyword args (e.g. "file")
# decode the values if charset is provided
def getKeywordsAndOptions(charset=None):
    keywords = []
    kvs = {}
    first = True
    
    # SPL-30670 - handle unicode args specially in windows
    argv = win32_utf8_argv() or sys.argv

    # for each arg
    for arg in argv:
        if first:
            first = False
            continue

        # ssquery could have newlines within the search, don't lose them - SPL-65995
        if re.match( "\"?ssquery(::|={1,2})", arg.lower()):
            matches = getKeywordNewlineSafe(arg, 'ssquery')
        # message could have newlines within it, don't lose them
        elif re.match( "\"?message(::|={1,2})", arg.lower()):
            matches = getKeywordNewlineSafe(arg, 'message')
        # footer could have newlines within it, don't lose them
        elif re.match( "\"?footer(::|={1,2})", arg.lower()):
            matches = getKeywordNewlineSafe(arg, 'footer')
        else:
            # handle case where arg is surrounded by quotes
            # remove outter quotes and accept attr=<anything>
            if arg.startswith('"') and arg.endswith('"'):
                arg = arg[1:-1]
                matches = re.findall('(?:^|\s+)([a-zA-Z0-9_-]+)\\s*(::|==|=)\\s*(.*)', arg)
            else:
                matches = re.findall('(?:^|\s+)([a-zA-Z0-9_-]+)\\s*(::|==|=)\\s*((?:[^"\\s]+)|(?:"[^"]*"))', arg)

        def needs_decoding(obj):
            if sys.version_info >= (3, 0):
                return isinstance(obj, bytes)
            return isinstance(obj, str)

        if len(matches) == 0:
            if charset!=None and needs_decoding(arg):
                arg = arg.decode(charset)

            keywords.append(arg)
        else:
            # for each k=v match
            for match in matches:
                attr, eq, val = match
                # put arg in a match
                if charset!=None and needs_decoding(val):
                    kvs[attr] = val.decode(charset)
                else:
                    kvs[attr] = val
    return keywords, kvs


# /////////////////////////////////////////////////////////////////////////////
# Tests
# /////////////////////////////////////////////////////////////////////////////

if __name__ == '__main__':
    
    import unittest
    
    # NOTE: cStringIO does not support unicode
    if sys.version_info >= (3, 0):
        from io import BytesIO
    else:
        from StringIO import StringIO
        BytesIO = StringIO

    class TestSimple(unittest.TestCase):

        def testBasicFieldChange(self):
            '''
            Does a basic run through of the read and output methods.
            '''

            # create dummy intersplunk data
            input = u'''
constant,sourcetype,"_time",field0,field1,source,host,"_raw",position,geometric,mval,__mv_mval
gardener,fictional,"1203623437",0,0,\u001A\u0BC3\u1451,"HAL_9000","2008-02-21T11:50:37 POSITION 0 geometric=1 constant=gardener field0=0 field1=0",0,1,ignored,$dollar$$bill$;$bar$
gardener,fictional,"1203622417",0,1,\u001A\u0BC3\u1451,"HAL_9000","2008-02-21T11:33:37 POSITION 1 geometric=4 constant=gardener field0=0 field1=1",1,4,ignored,$dollar$$bill$;$bar$
gardener,fictional,"1203621397",0,2,\u001A\u0BC3\u1451,"HAL_9000","2008-02-21T11:16:37 POSITION 2 geometric=7 constant=gardener field0=0 field1=2",2,7,ignored,$dollar$$bill$;$bar$
gardener,fictional,"1203620377",0,3,\u001A\u0BC3\u1451,"HAL_9000","2008-02-21T10:59:37 POSITION 3 geometric=10 constant=gardener field0=0 field1=3",3,10,ignored,$dollar$$bill$;$bar$
gardener,fictional,"1203619357",0,4,\u001A\u0BC3\u1451,"HAL_9000","2008-02-21T10:42:37 POSITION 4 geometric=13 constant=gardener field0=0 field1=4",4,13,ignored,$dollar$$bill$;$bar$
'''

            expectedOutput = u'''constant,sourcetype,_time,field0,field1,source,host,_raw,position,geometric,mval,scrabble,mv1,__mv_mval,__mv_mv1
breeder,fictional,1203623437,0,0,\x1a\u0bc3\u1451,HAL_9000,2008-02-21T11:50:37 POSITION 0 geometric=1 constant=gardener field0=0 field1=0,0,1,"dollar$bill
bar",dictionary,"a
b",$dollar$$bill$;$bar$,$a$;$b$
breeder,fictional,1203622417,0,1,\x1a\u0bc3\u1451,HAL_9000,2008-02-21T11:33:37 POSITION 1 geometric=4 constant=gardener field0=0 field1=1,1,4,"dollar$bill
bar",dictionary,"a
b",$dollar$$bill$;$bar$,$a$;$b$
breeder,fictional,1203621397,0,2,\x1a\u0bc3\u1451,HAL_9000,2008-02-21T11:16:37 POSITION 2 geometric=7 constant=gardener field0=0 field1=2,2,7,"dollar$bill
bar",dictionary,"a
b",$dollar$$bill$;$bar$,$a$;$b$
breeder,fictional,1203620377,0,3,\x1a\u0bc3\u1451,HAL_9000,2008-02-21T10:59:37 POSITION 3 geometric=10 constant=gardener field0=0 field1=3,3,10,"dollar$bill
bar",dictionary,"a
b",$dollar$$bill$;$bar$,$a$;$b$
breeder,fictional,1203619357,0,4,\x1a\u0bc3\u1451,HAL_9000,2008-02-21T10:42:37 POSITION 4 geometric=13 constant=gardener field0=0 field1=4,4,13,"dollar$bill
bar",dictionary,"a
b",$dollar$$bill$;$bar$,$a$;$b$
'''

            expectedOutputFields = u'''constant,sourcetype
breeder,fictional
breeder,fictional
breeder,fictional
breeder,fictional
breeder,fictional
'''            
            # decode intersplunk to list/dict format
            results = readResults(BytesIO(input.encode('UTF-8')))

            # loop over events
            for event in results:

                # change existing field
                event['constant'] = 'breeder'

                # add new field
                event['scrabble'] = 'dictionary'

                # add a multivalued field
                event['mv1'] = ['a', 'b']

            # begin stdout capture
            fake_stdout = BytesIO()
            
            # encode result data back to intersplunk format
            outputResults(results, outputfile=fake_stdout)
            generatedOutput = fake_stdout.getvalue()
            generatedOutput = generatedOutput.replace('\r\n', '\n')
            if MV_ENABLED:
                self.assertEqual(generatedOutput.decode('UTF-8'), expectedOutput)
  
            fake_stdout.truncate(0)
            outputResults(results, fields=['constant', 'sourcetype'], outputfile=fake_stdout)
            generatedOutput = fake_stdout.getvalue()
            generatedOutput = generatedOutput.replace('\r\n', '\n')
            if MV_ENABLED:
                self.assertEqual(generatedOutput.decode('UTF-8'), expectedOutputFields)
    
    # run all tests
    unittest.main()
