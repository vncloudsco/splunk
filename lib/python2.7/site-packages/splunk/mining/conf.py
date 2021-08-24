from __future__ import print_function
#   Version 4.0

#
# THIS FILE IS DEPRECATED IN FAVOR OF splunk.bundle.*
#

from builtins import object
import re, sys

def readText(filename):
    try:
        f = open(filename, 'r')
        text = f.read()
        f.close()
        return text
    except Exception as e:
        print('Cannot read file: ' + filename + ' cause: ' + str(e))
        return ""

class ConfParser(object):
    '''DEPRECATED. Use splunk.bundle.getConf() instead.'''

    def _parseLine(line):
        if len(line.strip()) == 0 or line.startswith("#"):
            return None
        # [name]
        m1 = re.match("^\[(.+)\]", line)
        if m1 != None:
            return "Xname", m1.groups()
        # attr = val
        m1 = re.match("^\s*([a-zA-Z0-9_-]+)\s*=\s*(.*)", line)
        #m1 = re.match("(\w+)\s*=\s*(.*)", line)
        if m1 != None:
            attr, val = m1.groups()
            return attr, val
        return "Xerror", line

    @staticmethod
    def parse(filename, singleVal=False, errors = []):
        text = readText(filename)
        stanzas = {}
        stanzas['default'] = stanza = {}
        name = None
        stanza = None
        continued = False
        lastAttr = None
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("\xEF\xBB\xBF"):
                line = line[3:]    # Ignore UTF-8 BOM 
            vals = ConfParser._parseLine(line)
            if vals == None:
                continued = False
                lastAttr = None
                continue
##             print("VALS=%s" % vals)
            #print("")
            attr, val = vals
            #print("Attr: %s val: %s Continued: %s lastAttr: %s\n\tLINE=%s" % (attr, val, continued, lastAttr, line))
            #print("LINE= " + line)
            if attr == "Xerror":
                if continued:
                    #print("\tVAL: " + val)
                    if singleVal:
                        stanza[lastAttr] += "\\n" + val
                    else:
                        stanza[lastAttr][-1] += "\\n" + val
                    #print("\tNEWVAL: ", stanza[lastAttr])
                else:
                    errors.append("ignoring line with parsing error: %s" % line)
            elif attr == "Xname":
                stanza = {}
                stanzas[val[0]] = stanza
                name = val[0]
            else:
                if attr in stanza:
                    if singleVal:
                        print("Warning: Seeing a second %s value in %s" % (attr, name))
                    else:
                        stanza[attr].append(val)
                else:
                    if singleVal:                    
                        stanza[attr] = val
                    else:
                        stanza[attr] = [val]
                        
            continued = False
            if len(val) > 0 and val[-1] == '\\':
                continued = True
            if attr != "Xerror":
                lastAttr = attr

        return stanzas
    

    def toString(trans):
        out = ""
        orderedattrs = trans.keys()
        orderedattrs = sorted(orderedattrs)
        for name in orderedattrs:
            attrs = trans[name]
            out += "[" + str(name) + "]\n"
            for attr, val in attrs.items():
                if attr != "name":
                    #print("VAL: %s" % val)
                    for v in val:
                        s = str(v)
                        s = s.replace("\\n", "\n\t")
                        out += attr + " = " + s + "\n"
            out += "\n"
        return out

    #parse = staticmethod(parseStanzas)
    toString = staticmethod(toString)
    _parseLine = staticmethod(_parseLine)
    
if __name__ == '__main__':
    argc = len(sys.argv)
    argv = sys.argv
    if argc == 2:
        filename = argv[1]
        errors = []
        trans = ConfParser.parse(filename, False, errors)
        print(ConfParser.toString(trans))
        print("-"*80)
        for error in errors:
            print("ERROR: " + error)
    else:
        print('Usage:')
        print(argv[0] + " filename")
