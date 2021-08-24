from __future__ import absolute_import
from __future__ import print_function
from builtins import range
from builtins import object

import re
import sys

from splunk.searchhelp import utils

_DEBUG = False

def getMatchingParen(exp, pos):
    depth = 1
    inquote = False
    elen = len(exp)
    while depth != 0 and pos < elen:
        ch = exp[pos]
        if ch == '"':
            inquote = not inquote
            pos += 1
            continue
        if inquote:
            pos += 1            
            continue
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        pos += 1
            
    if depth != 0:
        Exception("mismatched paren")
    return pos

def isTypeChar(ch):
    return ch.isalnum() or ch in '<>_-=:'

def emitToken(tokens, token):
    if len(token) > 0:
        tokens.append(token)
        token = ""
    return token

def printd(str):
    if _DEBUG:
        print(str)

def parseBNF(exp):
    printd("syntax: '%s'" % exp)
    subexp = []
    pos = 0
    inquote = False
    quotestart = 0
    token = ""
    elen = len(exp)
    while pos < elen:
        ch = exp[pos]
        if ch == '"':
            if inquote:
                quote = exp[quotestart+1:pos]
                printd("QUOTE: '%s'" % quote)
                subexp.append(quote)
                inquote = False
            else:
                quotestart = pos
                inquote = True
                token = emitToken(subexp, token)
            pos += 1            
            continue
        if inquote:
            pos += 1            
            continue
        if ch == '(':
            token = emitToken(subexp, token)
            
            end = getMatchingParen(exp, pos+1)
            subtext = exp[pos+1:end-1]
            printd("SUBTEXT: '%s'" % subtext)
            headexp = parseBNF(subtext)
            if len(headexp) == 0:
                headexp = [ " " ]
            printd("HEADEXP: '%s'" % headexp)
            subexp.append(headexp)
            subexp.extend(parseBNF(exp[end:]))
            printd("FINALSUBEXP: '%s'" % str(subexp))
            return subexp
            continue

        if ch.isspace():
            token = emitToken(subexp, token)
        else:
            printd("CH:"+ ch)
            if not isTypeChar(ch) or (token!="" and not isTypeChar(token[-1])):
                token = emitToken(subexp, token)
            token += ch
            printd("TOKEN:"+ token)

        pos += 1

    emitToken(subexp, token)
    return subexp

def cleanParse(exp):
    #print("EXP %s" % exp)
    if not isinstance(exp, list):
        #print("NOTLIST %s" % exp)
        return exp
    
    newexp = []
    for x in exp:
        #print("%s %u %s" % (x, len(x), newexp))
        if isinstance(x, list) and len(x) == 1:
            #print("INPUT: %s, CLEANPARSE: %s" %( x[0], cleanParse(x[0])))
            newexp.append(cleanParse(x[0]))
        else:
            newexp.append(cleanParse(x))
    return newexp
        


def regexRecurseSyntax(commands, stanza, datatypes, maxdepth):

    maxdepth -= 1

    syntax = stanza["syntax"][0]
        
    #print("%s SYNTAX: %s" % (maxdepth, syntax))
    if maxdepth == 0:
        # logger.error("regexRecurseSyntax() called with maxdepth==0")
        return "FAIL%sFAIL" % syntax
    
    terms = re.findall("<([a-zA-Z]+[a-zA-Z0-9_-]*)>", syntax)
    
    for term in terms:

        breakdown = re.findall("([a-zA-Z0-9_/-]+)(?::([^=]+))?(?:=(.*))?", term)
        datatype   = breakdown[0][0]
        variable   = breakdown[0][1]
        # defaultval = breakdown[0][2]
        # print("datatype %s variable %s defaultval %s " % (datatype, variable, defaultval))
        if term in commands:
            substanza = commands[datatype]
        elif term in datatypes:
            substanza = datatypes[datatype]
        else:
            sys.stderr.write("Ignoring undefined stanza: %s\n" % term)                        
            continue
        # print("SUB: %s STANZA: %s" % (substanza, stanza))
        if substanza == stanza:
            sys.stderr.write("Ignoring recursive definition: %s\n" % term)                        
            continue
        syntax = syntax.replace("<" + term + ">", "(?:" + regexRecurseSyntax(commands, substanza, datatypes, maxdepth) + ")")
    return syntax



class Exp(object):
    pass

# X Y
class SequenceExp(Exp):
    def __init__(self, seq):
        self._seq = seq

    def minMatchLen(self):
        return sum([s.minMatchLen() for s in self._seq])
        
    def __str__(self):
        out = ""
        for v in self._seq:
            if out != "":
                out += " "
            out += str(v)
        return "seq(%s)" % out

    def getSeq(self):
        return self._seq

    def toRegex(self, datatypes):
        out = ""
        for v in self._seq:
            if out != "":
                out += " *" # needs some work.  between some a " "+ is obviously needed. e.g. "sort <num>"
            out += v.toRegex(datatypes)
        return "(?:%s)" % out
    def toSimpleRegex(self, noparens = False):
        out = ""
        for v in self._seq:
            if out != "":
                out += " " # needs some work.  between some a " "+ is obviously needed. e.g. "sort <num>"
            out += v.toSimpleRegex()
        if not noparens and len(self._seq) > 1:
            return "(%s)" % out
        else:
            return "%s" % out
    
MAX_SIMPLE_CHOICES = 1000 #5    
# X | Y
class ChoiceExp(Exp):
    def __init__(self, choices):
        self._choices = choices

    def minMatchLen(self):
        return min([s.minMatchLen() for s in self._choices])   
        
    def __str__(self):
        out = ""
        for v in self._choices:
            if out != "":
                out += " "
            out += str(v)
        return "choice(%s)" % out

    def getChoices(self):
        return self._choices

    def toRegex(self, datatypes):
        out = ""
        singleChar = True
        for v in self._choices:
            if not isinstance(v, LiteralTerm) or len(v.getValue()) != 1:
                singleChar = False
                break
        if singleChar:
            chars = ""
            for v in self._choices:
                chars += v.getValue()
            return "[%s]" % chars

        for v in self._choices:
            if out != "":
                out += "|"
            out += v.toRegex(datatypes)
        return "(?:%s)" % out

    def toSimpleRegex(self, noparens = False):
        out = ""
        i = 0
        for v in self._choices:
            i += 1
            if out != "":
                out += "|"  # " OR "
            if i > MAX_SIMPLE_CHOICES:
                out += "..."
                break
            out += v.toSimpleRegex()
        if not noparens and len(self._choices) > 1:
            return "(%s)" % out
        else:
            return "%s" % out
    
# "?"
class OptionalExp(Exp):
    def __init__(self, exp, canRepeat=False):
        self._exp = exp

    def minMatchLen(self):
        return 0    
        
    def __str__(self):
        return "optional(%s)" % self._exp

    def toRegex(self, datatypes):
        return "(?:%s)?" % self._exp.toRegex(datatypes)

    def getValue(self):
        return self._exp

    def toSimpleRegex(self, noparens = False):
        if self._exp.toSimpleRegex() == " ":
            return " "
        return "[%s]" % self._exp.toSimpleRegex(True)
    
# "*"
class OptionalRepeatingExp(Exp):
    def __init__(self, exp):
        self._exp = exp

    def minMatchLen(self):
        return 0        
        
    def __str__(self):
        return "optionalRepeating(%s)" % self._exp
    def getValue(self):
        return self._exp
    
    def toRegex(self, datatypes):
        return "(?:%s)*" % self._exp.toRegex(datatypes)

    def toSimpleRegex(self, noparens = False):
        if self._exp.toSimpleRegex() == " ":
            return " "
        return "[%s]*" % self._exp.toSimpleRegex(True)
    
# "+"
class RequiredRepeatingExp(Exp):
    def __init__(self, exp):
        self._exp = exp
    def minMatchLen(self):
        return self._exp.minMatchLen()
    def __str__(self):
        return "requiredRepeating(%s)" % self._exp
    def getValue(self):
        return self._exp

    def toRegex(self, datatypes):
        return "(?:%s)+" % self._exp.toRegex(datatypes)
    def toSimpleRegex(self, noparens = False):
        if len(self._exp.toSimpleRegex()) > 1:
            return "(%s)+" % self._exp.toSimpleRegex(True)
        else:
            return "%s+" % self._exp.toSimpleRegex()
        

def needsEsc(ch):
    return ".()[]{}*+^$!-\?".find(ch) >= 0

def safeRegexLiteral(literal):
    safe = ""
    for ch in literal:
        if needsEsc(ch):
            ch = "\\" + ch
        safe += ch
    return safe
    
class LiteralTerm(Exp):
    def __init__(self, term):
        self._term = term
    def minMatchLen(self):
        return len(self._term)              
    def __str__(self):
        return "'%s'" % self._term
    def getValue(self):
        return self._term
    def toRegex(self, datatypes):
        return "%s" % safeRegexLiteral(self._term)
    def toSimpleRegex(self, noparens = False):
        if self._term != safeRegexLiteral(self._term):
            return '"%s"' % self._term
        return self._term
    



def getDef(syntax, depth, datatypes):
    if depth == 0:
        return "FAIL%sFAIL" % datatypes
    terms = re.findall("<([a-zA-Z]+[a-zA-Z0-9_-]*)>", syntax)
    for term in terms:
        breakdown = re.findall("([a-zA-Z0-9_/-]+)(?::([^=]+))?(?:=(.*))?", term)
        datatype   = breakdown[0][0]
        variable   = breakdown[0][1]
        # defaultval = breakdown[0][2]
        # print("term  %s datatype %s variable %s defaultval %s " % (term, datatype, variable, defaultval))

        if datatype in datatypes.stanzas:
            definition = datatypes[datatype]['syntax'][0]
        else:
            raise Exception("UNDEFINED(%s)" % term)
            return "UNDEFINED(%s)" % term
        syntax = syntax.replace("<" + term + ">", "(?:" + getDef(definition, depth-1, datatypes) + ")")
    return syntax
    
class DataTypeTerm(Exp):
    def __init__(self, term):
        self._term = term
    def __str__(self):
        return "%s" % self._term
        #return "datatype(%s)" % self._term
    def getValue(self):
        return self._term
    def toRegex(self, datatypes):
        return getDef(self._term, 10, datatypes)
        return "THISISNOTAREGEX(%s)" % safeRegexLiteral(self._term)
    def toSimpleRegex(self, noparens = False):
        return self._term


# ['<num>', '?', ['auto', '|', 'str', '|', 'ip', '|', 'num'], '*']

def convert(exp):
    if exp == '':
        return LiteralTerm('')
    if not isinstance(exp, list):
        if exp[0] == '<':
            return DataTypeTerm(exp)
        else:
            return LiteralTerm(exp)
    
    newexp = []
    elen = len(exp)

    # if odd number of values
    if elen > 2 and elen % 2 == 1:
        
        choice = True
        for i in range(elen):
            if i % 2 == 1 and exp[i] != '|':
                choice = False
                break
        if choice:
            choices = [convert(v) for i, v in enumerate(exp) if i%2==0]
            printd("CHOICES:" + str(choices))
            return ChoiceExp(choices)
    i = 0
    while i < elen:
        subexp = convert(exp[i])
        if i == elen-1:
            next = "AHhhhhhhh"
        else:
            next = exp[i+1]
        if next == '?':
            newexp.append(OptionalExp(subexp))
        elif next == '*':
            newexp.append(OptionalRepeatingExp(subexp))            
        elif next == '+':
            newexp.append(RequiredRepeatingExp(subexp))
        else:
            newexp.append(subexp)
            i -= 1
        i += 2
    return SequenceExp(newexp)


def getBNF(command, sessionKey, username, namespace):
    from splunk.searchhelp import describer
    stanzas = utils.getStanzas("searchbnf", sessionKey, username, namespace)
    datatypes = utils.getStanzas("datatypesbnf", sessionKey, username, namespace)
    try:
        #print("stanzas: %s" % stanzas.keys())
        stanza = stanzas[command+"-command"]
    except:
        # print("datatypes: %s" % datatypes)
        stanza = datatypes[command]

    datatypes = []
    syntax = describer.recurseSyntax(command, stanzas, stanza, datatypes)
    printd("Original Syntax:" + str(stanza["syntax"]))
    printd("Recursed:" + syntax)
    return syntax

def getExp(bnf):
    p = parseBNF(bnf)
    p1 = cleanParse(p)
    exp = convert(p1)
    printd("Cleaned:" + str(p1))
    printd("Converted:" + str(exp))
    return exp

def getTokens(exp, tokens):
    'xxx'
    if isinstance(exp, SequenceExp):
        seq = exp.getSeq()
        if len(seq) == 2 and isinstance(seq[0], LiteralTerm) and isinstance(seq[1], ChoiceExp):
            attr = seq[0].getValue()
            if attr.endswith('='):
                attr = attr[:-1]
            tokens[attr] = [x.getValue() for x in seq[1].getChoices()]
        else:
            for v in seq:
                getTokens(v, tokens)
    elif isinstance(exp, list):
        for v in exp:
            getTokens(v, tokens)




    elif isinstance(exp, ChoiceExp):
        getTokens(exp.getChoices(), tokens)        
    elif isinstance(exp, LiteralTerm):
        if '=' in exp.getValue():
            field, value = exp.getValue().split('=', 1)
            tokens[field] = value
        else:
            attr = exp.getValue()
            # if a single punct char (+-!|()[],) or busted literal like '-<int' -- ignore
            if  (len(attr) == 1 and not attr.isalpha()) or ('<' in attr and '>' in attr and (not attr.startswith('<') or not attr.endswith('>'))):
                pass
            else:
                tokens[attr] = 'literal'
                
    elif isinstance(exp, OptionalRepeatingExp) or isinstance(exp, OptionalExp) or isinstance(exp, RequiredRepeatingExp):
        getTokens(exp.getValue(), tokens)
        #tokens[exp.getValue()] = 'optional'        
    elif isinstance(exp, DataTypeTerm):
        tokens[exp.getValue()] = 'datatype'        
    else:
        print("HUH? %s" % exp.__class__.__name__)

# safe-extend.  extends list with value if it's another list, otherwise append.  a simple 'extend' will extend 'elvis' as 'e','l','v','i','s'
def sextend(list, val):
    if isinstance(val, list):    
        list.extend(val)
    else:
        list.append(val)
        
def getFirst(result, exp ):
    #print("ELVIS: %s" % exp)
    # SEQUENCE
    if isinstance(exp, SequenceExp):
        for v in exp.getSeq():
            if getFirst(result, v):
                return True
    # CHOICE
    elif isinstance(exp, ChoiceExp):
        for x in exp._choices:
            getFirst(result, x)
        return True
    # DATATYPE, LITERAL
    elif isinstance(exp, DataTypeTerm) or isinstance(exp, LiteralTerm):
        sextend(result, exp.getValue())
        return True
    # OPTIONAL, OPTIONALREPEAT
    elif isinstance(exp, OptionalRepeatingExp) or isinstance(exp, OptionalExp):
        getFirst(result, exp.getValue())
    # REQUIREDREPEAT
    elif isinstance(exp, RequiredRepeatingExp):
        if getFirst(result, exp.getValue()):
            return True

    return False

def getNext(exp, argtext):
    result = []
    if argtext.strip() == "":
        getFirst(result, exp)
        return result

    if isinstance(exp, SequenceExp):
        nexts = []
        for v in exp.getSeq():
            nexts.append(getNext(v, argtext))
        return nexts
    else:
        return "AHHHHHH: NOT SEQUENCE", exp.__class__.__name__
    

def getRegex(command, sessionKey, username, namespace):
    stanzas = utils.getStanzas("searchbnf", sessionKey, username, namespace)
    datatypes = utils.getStanzas("datatypesbnf", sessionKey, username, namespace)
    try:
        stanza = stanzas[command+"-command"]
    except:
        stanza = datatypes[command]

    syntax = regexRecurseSyntax(stanzas, stanza, datatypes, 10)
    printd("Original Syntax:" + str(stanza["syntax"]))
    printd("Recursed:" + syntax)
    return syntax


def usage():
    argv = sys.argv    
    print('Usage:')
    print("\t" + argv[0] + '"commandname" "input" ')
    print("\t\t example:" + argv[0] + '"sort" "sort 10" ')
    print("")
    print("\t" + argv[0] + 'parse blah "expression" "input"')
    print("\t\t example:" + argv[0] + 'parse blah "(foo|bar)? elvis*" "foo"')
    print("")
    exit(-1)

def _main():
    argc = len(sys.argv)
    argv = sys.argv
    sessionKey = utils.TEST_SESSION()
    namespace  = utils.TEST_NAMESPACE()
    username = 'admin'
    if len(argv) < 2:
        usage()
    cmd = argv[1]
    if argc == 3 and cmd != "parse":
        inputtxt = argv[2]        
        bnf = getBNF(cmd, sessionKey, username, namespace)
        exp = getExp(bnf)
        next = getNext(exp, inputtxt)
        #regex = getRegex(cmd, sessionKey)

        datatypes = utils.getStanzas("datatypesbnf", sessionKey, username, namespace)

        print("bnf:\t%s" % bnf)
        print("exp:\t%s" % exp)
        print("next:\t%s" % next)
        print("regex:\t%s" % exp.toRegex(datatypes))
        print("Simpleregex:\t%s" % exp.toSimpleRegex(True))

    elif argc >= 3:
        bnf = argv[2]
        inputtxt = ""
        if argc == 4:
            inputtxt = argv[3]
        exp = getExp(bnf)
        next = getNext(exp, inputtxt)
        #print("exp: %s" % exp)
        #print("minMatchLen: %s" % exp.minMatchLen())
        #print("next: %s" % next)
        print("%s\t%s" % (exp.minMatchLen(), bnf))
    else:
        usage()
    
if __name__ == '__main__':
    _main()
