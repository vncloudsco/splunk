from __future__ import absolute_import

from builtins import object
import re
from xml.sax import saxutils
from splunk.searchhelp import parser
from splunk.searchhelp import utils

MAX_SYNTAX_LEN = 150

class logger(object):
    @staticmethod
    def warn(msg):
        #print(msg)
        pass

def removeWhitespaces(text):
    text = text.replace("\\\\n", " ")
    text = text.replace("\r\n", " ")
    text = text.replace("\n", " ")
    text = text.replace("\t", " ")
    while True:
        oldtext = text
        text = text.replace("  ", " ")
        if oldtext == text:
            break
    # replace PARAGRAPH TOKEN \p\ with newline
    text = text.replace("\\p\\", "<br/><br/>")
    # replace INDENT TOKEN \i\ with newline 4spaces
    text = text.replace("\\i\\", "<br/>" + "&nbsp;"*4)
    return text
    
def cleanSyntax(syntax):
    syntax = removeWhitespaces(syntax)
    # remove double parens
    parenhogs = re.findall("\(\s*\([^\(\)]*\)\s*\)", syntax)
    for hog in parenhogs:
        syntax = syntax.replace(hog, hog[1:-1])
    # remove unnecessary single quotes
    parenhogs2 = re.findall("(\([^ |]*?\))[^?*+]", syntax)
    for hog in parenhogs2:
        syntax = syntax.replace(hog, hog[1:-1])
    syntax = removeWhitespaces(syntax)
    syntax = syntax.replace(" <no-ws> ", "")
    syntax = syntax.replace("<no-ws> ", "")
    syntax = syntax.replace(" <no-ws>", "")
    syntax = syntax.replace("<no-ws>", "")
    return syntax


def escapeAllBut(text, tags):
    for t in tags:
        text = text.replace("<%s/>"  % t, "xxx%s/xxx"  % t)
        text = text.replace("<%s>"  % t, "xxx%sxxx"  % t)
        text = text.replace("</%s>" % t, "xxx/%sxxx" % t)
    text = saxutils.escape(text)
    for t in tags:    
        text = text.replace("xxx%s/xxx" % t, "<%s/>" % t)
        text = text.replace("xxx%sxxx"  % t, "<%s>"  % t)
        text = text.replace("xxx/%sxxx" % t, "</%s>" % t)
    return text


def stylizeVariables(text):
    # finds all terms of the form <foo> (surrounded by "<" and ">", contains a-z, A-Z, 0-9, _/:-)
    terms = re.findall("<([a-zA-Z][a-zA-Z0-9_/:=-]*)>", text)

    # each term has a structure: "<foo:bar=hurrah>" (the ":bar=hurrah" is optional)
    # in the above example, datatype=foo, variable=bar, defaultval="=hurrah"
    REGEX = re.compile("([a-zA-Z0-9_/-]+)(:[^=]+)?(=.*)?")
    for term in terms:
        breakdown = REGEX.findall(term)
        datatype   = breakdown[0][0]
        variable   = breakdown[0][1]
        defaultval = breakdown[0][2]
        text = text.replace("<%s>" % term, "xxxixxx%sxxx/ixxx%s%s" % (datatype, variable, defaultval), 1)

    #Finds "literals", which are a sequence of all capital letters (or an underscore) immediately followed by a non-letter.  Wraps each match with the "xxxbxxx" and "xxx/bxxx" tags and converts to lower case.  
    # Examples: 
    # "SQL" is not a match because it's not followed by a non-letter
    # "SQL1" finds a match for "SQL" because it is all caps and is followed by a non-letter ("1")     
    # "SQL hurrah" find a match for "SQL" because it is all caps and is folowed by a space
    # In last two examples above, the match "SQL" is converted to "xxxbxxxsqlxxx/bxxx"
    literals = re.findall("[A-Z][A-Z_-]+(?=[^a-zA-Z])", text)
    for lit in literals:
        text = text.replace(lit, "xxxbxxx" + lit.lower() + "xxx/bxxx", 1)

    #Finds a second type of literal, anything surrounded by quotes
    literals = re.findall("\".*?\"", text)
    for lit in literals:
        replacement = lit.lower()[1:-1]
        text = text.replace(lit, "xxxbxxx" + replacement + "xxx/bxxx", 1)

    # Escape '&', '<', and '>' 
    text = saxutils.escape(text)

    # Wrap the terms detected above with html markup 
    text = text.replace("xxxbxxx", "<code>")
    text = text.replace("xxx/bxxx", "</code>")

    # Wrap the literals detected above with html markup 
    text = text.replace("xxxixxx", "<em>")
    text = text.replace("xxx/ixxx", "</em>")
    return text

def getLiterals(stanzas, user, namespace):
    literals = {}
    commands = utils.getAllCommands(stanzas, user, namespace)
    
    for command in commands:
        myliterals = set()
        cname = command+"-command"
        if cname not in stanzas:
            continue
        unexpanded = {}
        stanza = stanzas[cname]
        syntax = recurseSyntax(command, stanzas, stanza, unexpanded, False)
        syntax = cleanSyntax(syntax)
        uppers = re.findall("[A-Z][A-Z_-]+(?=[^a-zA-Z])", syntax)
        myliterals.update(uppers)
        quoted = re.findall('"(.*?)"', syntax)
        myliterals.update(quoted)
        terms = re.findall("(?<![<a-zA-Z0-9_-])([a-zA-Z0-9_-]+)", syntax)
        myliterals.update(terms)
        literals[command] = myliterals
    return literals


def getValue(stanza, field, defaultval = ""):
    return stanza.get(field, defaultval)

def describeCommand(stanzas, key, useSimpleSyntax, prod_type=None):

    # pair of (example, comment)
    description = {'name':None, 'shortdesc':None, 'details':None, 'syntax':None, 'examples': None }
    command = key
    if not key.endswith("-command"):
        key += "-command"
    if key not in stanzas.stanzas:
        return None
    unexpanded = {}
    stanza = stanzas[key]

    # No description/help for the deprecated or unlisted commands !
    if not utils.isPublic(stanza) or not utils.isListed(stanza, prod_type):
        return None

    syntax = cleanSyntax(recurseSyntax(command, stanzas, stanza, unexpanded, useSimpleSyntax))
    if useSimpleSyntax:
        exp = parser.getExp(syntax)
        syntax = exp.toSimpleRegex(True)        
    syntax = stylizeVariables(syntax).replace("\n", "<br/>")    

    examples = []
    for attr in stanza:
        if attr.startswith("example"):
            example = getValue(stanza, attr)
            suffix = attr[len("example"):]
            commentid = "comment" + suffix
            comment = "Example usage"
            if commentid in stanza:
                comment = getValue(stanza, commentid)
            if "cheat" in suffix: # put cheatsheet examples at the top
                examples.insert(0, (example, comment))
            else:
                examples.append((example, comment))

    description['name'] = saxutils.escape(key[0:-8])
    description['shortdesc'] = removeWhitespaces(stylizeVariables(getValue(stanza, "shortdesc")))
    description['details'] = removeWhitespaces(stylizeVariables(getValue(stanza, "description"))).replace("\n", " ")
    description['syntax'] = syntax
    description['examples'] = examples
    description['aliases'] = getValue(stanza, "alias", "")
    description['related'] = getValue(stanza, "related", "")
    description['category'] = getValue(stanza, "category", "")
    
    # ack! we have no short description
    if len(description['shortdesc']) == 0:
        # if details is short, use that
        if len(description['details']) < 100:
            description['shortdesc'] = description['details']
            description['details'] = ''
        else:
            # otherwise give generic shortdesc
            description['shortdesc'] = 'See details below'
    
    return description

leaf_datatypes = set(["sp", "field-and-value", "field-and-value-list", "no-ws", "int", "num", "wc-str", "string", "bool", "field", "field-list",
                      "sqlite-expression", "wc-field", "wc-field-list", "wc-string", "tag", "tag-list", "filename", "true", "false", "term",
                      "sed-expression", "search-pipeline"])

def isLeafDataType(typename):
    return typename in leaf_datatypes

def recurseSyntax(command, stanzas, stanza, unexpanded, simplesyntax = True, depth=0, max_len=MAX_SYNTAX_LEN):
    syntax = getValue(stanza, "syntax")
    if simplesyntax and "simplesyntax" in stanza:
        syntax = stanza["simplesyntax"]

    terms = re.findall("<([a-zA-Z][a-zA-Z0-9_/:=-]*)>", syntax)
    REGEX = re.compile("([a-zA-Z0-9_/-]+)(?::([^=]+))?(=.*)?")
    for term in terms:
        breakdown = REGEX.findall(term)
        datatype   = breakdown[0][0]
        variable   = breakdown[0][1]
        defaultval = breakdown[0][2]
        #print("!datatype %s variable %s defaultval %s " % (datatype, variable, defaultval))

        if datatype in unexpanded:
            continue
        if isLeafDataType(datatype):
            continue
        # never expand eval-expression unless it's for the eval command
        if datatype == "eval-expression" and command != "eval":
            continue
        
        if datatype not in stanzas.stanzas:
            logger.warn("Ignoring undefined stanza: %s" % datatype)            
            continue
        substanza = stanzas[datatype]
        if substanza == stanza:
            logger.warn("Ignoring recursive definition: %s" % datatype)
            continue
        toobig = False
        if (depth > 10):
            logger.warn("aborting expanding syntax at maxdepth of recursion! trying to define %s" % (datatype))
            toobig = True            
        elif len(syntax) > max_len:
            logger.warn("aborting monstrously huge syntax for %s -- %s" % (datatype, syntax))
            toobig = True
        if toobig: 
            unexpanded[datatype] = ()
            mysyntax = recurseSyntax(command, stanzas, substanza, unexpanded, simplesyntax, 10, max_len)
            unexpanded[datatype] = (stanzas[datatype].get('description', 'No description'), mysyntax, variable, defaultval, depth, max_len)
        else:
            syntax = syntax.replace("<%s>" % term, "(%s)" % recurseSyntax(command, stanzas, substanza, unexpanded, simplesyntax, depth+1, max_len) )
    return syntax
