from __future__ import absolute_import
from builtins import object
import logging
from builtins import range
import re
import string

import splunk
import splunk.entity as entity
import splunk.util as util

logger = logging.getLogger('splunk.parser')

###########################################################
### Utils 


# key names for each intention
INAME = "name"
IARG  = "arg"
IFLAGS = "flags"

NULL_VAL = "-=NULL=-"    # NULL VALUE FROM  DRILLDOWN

reportingCommands = ['chart', 'timechart', 'top', 'rare']

def tokenize(searchString):
    """
    Tokenize a search string.
    Ported over from the Javascript version in 
    query.js (Command.prototype.parseSimpleSearch)

    Please note this is not really in any way a tokenizer.  
    It actually returns, not tokens, but search phrases or clauses. --jrod
    >>> tokenize("hi i like beans NOT (frijoles_negros OR garbanzos)"
    ["hi", "i", "like", "beans", "NOT (frijoles_negros OR garbanzos)"]
    >>> tokenize("val1 > 5 val2>6")
    ["val1", ">", "5", "val2>6"]
    """
    if not searchString:
        return []

    # the splunkd parser does some funky aliasing that turns
    # "sourcetype=<something>" to "sourcetype::<something>"
    # replace all occurences of '::' with '=' to reverse this
    colonectomyRe = re.compile(r'(?<=sourcetype)(::)(?=\w+)', re.IGNORECASE)
    if isinstance(searchString, list):
        searchString = ' '.join(searchString)
    searchString = colonectomyRe.sub('=', searchString)

    # more odd behaviour related to sourcetype
    # remove the (, )'s surrounding the sourcetype term

    chars = searchString
    inSquote = False
    inDquote = False
    inEscSeq = False
    pDepth = 0
    bDepth = 0
    terms = []
    buffer = []

    for i in range( len(chars) ):
        c = chars[i]

        if inEscSeq:
            inEscSeq = False
            buffer.append(c)
            continue

        if c == '\\':
            inEscSeq = True
            buffer.append(c)
            continue
        elif c == ' ':
            if inDquote or inSquote or (pDepth > 0) or (bDepth > 0):
                buffer.append(c)
                continue
            if len( ''.join(buffer).strip() ) > 0:
                terms.append( ''.join(buffer) )
                buffer = []
                continue
        elif c == '"':
            inDquote = not inDquote
            buffer.append(c)
            continue
        elif c == "'":
            inSquote = not inSquote
            buffer.append(c)
            continue
        elif c == "[":  # handle square brackets, likely subsearches
            if not inDquote and not inSquote:
                bDepth = bDepth + 1
            buffer.append(c)
            continue
        elif c == "]": 
            if inDquote or inSquote:
                buffer.append(c)
                continue
            if bDepth > 0:
                bDepth = bDepth - 1
            if bDepth >= 0:
                buffer.append(c)
                continue
            else:
                terms.append( ''.join(buffer) )
                buffer = []
                bDepth = 0
                continue
        elif c == "(":  # handle parenthesis, likely conditionals
            if not inDquote and not inSquote:
                pDepth = pDepth + 1
            buffer.append(c)
            continue
        elif c == ")":
            if inDquote or inSquote:
                buffer.append(c)
                continue
            if pDepth > 0:
                pDepth = pDepth - 1
            if pDepth >= 0:
                buffer.append(c)
                continue
            else:
                terms.append( ''.join(buffer) )
                buffer = []
                pDepth = 0
                continue
        else:
            buffer.append(c)
            continue

    if len(buffer) > 0:
        terms.append( ''.join(buffer) )

    # keep the NOT terms along with the term they are negating
    # clean up the ( and ) from sourceterm
    joinedNot = []
    nextIsNot = False
    for term in terms:
        if term == "NOT":
            nextIsNot = True
            continue
        elif nextIsNot:
            joinedNot.append("NOT %s" % term)
            nextIsNot = False
        else:
            if term.lower().find("sourcetype") > -1:
                unParenRE = re.compile(r'\(\s(sourcetype=\w+)\s\)', re.IGNORECASE)
                matchObj = re.match(unParenRE, term)
                if matchObj is not None:
                    term = matchObj.group(1)
            joinedNot.append(term)

    return joinedNot

def tokenizeFieldsString(fields):
    if fields is not None: return [ s.strip() for s in fields.split(',') ]
    else: return[]

def unfilterize(searchString):
    """
    The splunkd search parser now returns our search strings in a format wrapped up
    to apply search filters. This function unwraps our search terms.
    """
    if searchString is not None:
        unfilterPattern = re.compile( r'^\( (.+) \) \( \( \S+ \) \)$' )
        searchTerms = unfilterPattern.search( searchString.strip() )

        if searchTerms is None:
            return searchString

        logger.debug("Unfilterized: " + searchString + " --> " + searchTerms.group(1) )
        return str(searchTerms.group(1) ).strip()
    else:
        return None

def needsQuotes(s):
    def _hasQuotes(s):
        if isinstance(s, util.string_type):
            return s.startswith('"') or s.endswith('"')
        return False

    def _isInParens(s):
        if isinstance(s, util.string_type):
            return s.startswith('(') and s.endswith(')')
        return False

    if not isinstance(s, util.string_type):
        return False
    if _hasQuotes(s) or  _isInParens(s) or re.match("NOT\W", s) != None:
        return False
    specialCharsToQuote = "<=>[]`| "
    for c in s:
        if c in specialCharsToQuote:
            return True
    return False

# 'foo"bar' -> 'foo\"bar'
# 'foo\"bar' -> 'foo\"bar'
def quoteUnescapedInternal(v):
    # tmp remove all \\ and \" with "  ", leaving only unescaped quotes
    tmp = v.replace("\\\\", "  ").replace("\\\"", "  ")
    start = 0
    offset = 0
    # fix all occurrances of unescaped quotes in original string
    while True:
        quotepos = tmp.find('"', start)
        if quotepos < 0:
            break
        start = quotepos + 1        
        quotepos += offset
        v = v[:quotepos] + "\\" + v[quotepos:]
        offset += 1
    return v

def escVal(v):
    if not isinstance(v, util.string_type):
        return v
    quoted = False
    prefix = ''
    if v.startswith('NOT '):
        prefix = 'NOT '
        v = v[4:].strip()
    if v.startswith('"') and v.endswith('"'):
        quoted = True
        # '"foo"bar"' -> 'foo"bar'
        v = v[1:-1]

    # v = quoteUnescapedInternal(v)
    v = v.replace('\\', '\\\\').replace('"', '\\"')  

    # 'foo\"bar' -> '"foo\"bar"'
    if quoted: v = '"%s"' % v
    v = prefix + v
    return v

# 'k="v"' -> 'k="v"'
# '"k=v"' -> '"k=v"'
# '"foo"bar' -> '\\"foo\\"bar'
# '"foo"bar"' -> '"foo\\"bar"' 
def escQuote(text):
    """ escape quote character if not surrounding the text value """
    if isinstance(text, util.string_type):
        # '"foo=bar"' -> same
        if text.startswith('"') and text.endswith('"'):
            return escVal(text)
            
##         eq = text.split('=',1)
##         # if this is a attr=val pattern
##         if len(eq) > 1:
##             k, v = eq
##             # 'elvis="foo"bar"'  -> 'elvis="foo\"bar"'                
##             text = '%s=%s' % (k,escVal(v))
##         else:
        text = escVal(text)
        #if not text.startswith('"') or not text.endswith('"'):
        #    return text.replace('"', '\\"')
    return text


def hasSpan(args):
    if 'xfieldopts' in args and 'clauses' in args['xfieldopts']:
        for val in args['xfieldopts']['clauses']:
            if val.startswith("span"):
                return True
    return False

class SpanRange(object):
    def __init__(self, minval, maxval):
        self.min = minval
        self.max = maxval

def splitSpan(span):
    match = re.match("(-?[^-]+)-(-?.+)", span)
    if match == None:
        return span
    minval, maxval = match.groups()
    return SpanRange(minval, maxval)



def addTerm(clause, term, quoteSpecials=False, needsEscaping=True):
    """ given a search command clause, add the given search term """
    if clause.args is None:
        logger.debug("Adding term to empty clause.")
        clause.args = {
            'search' : ''
        }

    tokens = tokenize( clause.args['search'] )

    # simplejson decodes all strings into unicode, we have to check for both
    if isinstance(term, util.string_type):
        # chars that need quoting are Python's string.punctuation minus the *

        if needsEscaping:
            term = escQuote(term)

        if quoteSpecials and needsQuotes(term):
            term = '"%s"' % term
        if tokens == ['*']: 
            clause.args['search'] = term
            return clause
        else:
            tokens.append(term)
    elif isinstance(term, dict):
        for k, v in term.items():
            if needsEscaping:
                v = escVal(v)
            if tokens == ['*']:
                if v == NULL_VAL:
                    clause.args['search'] = "NOT %s=*" % k
                else:
                    if isinstance(v, SpanRange):
                        clause.args['search'] = "%s>=%s %s<%s" % (k, v.min, k, v.max)
                    else:
                        clause.args['search'] = "%s=%s" % (k, searchVToString(v) )
                return clause

            ### if we have the earliest or latest timeterms, just pop them in w/o quotes
            if k in ['earliest', 'latest']:
                tokens.append( "%s=%s" % (k, v ) )
            else:
                if v == NULL_VAL:
                    tokens.append( "NOT %s=*" % k)
                else:
                    if isinstance(v, SpanRange):
                        tokens.append("%s>=%s %s<%s" % (k, v.min, k, v.max))
                    else:
                        tokens.append( "%s=%s" % (searchKToString(k), searchVToString(v) ) )
    else:
        # We can only add strings, unicode strings, or kv-pairs stored in dictionary form.
        raise TypeError("Adding a term that is neither a str, unicode, nor dict is not valid. '%s' is of type '%s'." % (term, type(term)))

    clause.args['search'] = ' '.join(tokens)
    return clause

def addNegatedTerm(clause, term):
    """ given a search command clause, add the given search term negated with 'NOT' """
    if clause.args is not None:
        tokens = tokenize( clause.args['search'] )

        # simplejson decodes all strings into unicode, we have to check for both
        if isinstance(term, util.string_type):
            if term in tokens:
                tokens.remove(term)
            tokens.append("NOT %s" % escVal(term))
        elif isinstance(term, dict):
            for item in term.items():
                tokens.append("NOT %s" % searchKVToString(term) )
        else:
            # We can only add strings, unicode strings, or kv-pairs stored in dictionary form.
            raise TypeError("Adding a term that is neither a str, unicode, nor dict is not valid.")

        clause.args['search'] = ' '.join(tokens)
    else:
        logger.debug("Adding term to empty clause.")
        clause.args = {
            'search' : term 
        }
    return clause

def removeTerm(clause, term):
    """ remove a search term from the given search command clause """

    if clause.args is not None:
        tokens = tokenize( clause.args['search'] )
        def remove_token(token_list, term):
            term_i = tokens.index(term)
            bool_expressions = ['AND', 'OR']
            # foo OR bar, remove bar
            if term_i > 0 and token_list[term_i - 1] in bool_expressions:
                token_list.pop(term_i - 1)
            # foo OR bar, remove foo
            elif len(token_list) > (term_i + 1) and \
                    token_list[term_i + 1] in bool_expressions:
                token_list.pop(term_i + 1)
            token_list.remove(term)

        # simplejson decodes all strings into unicode, we have to check for both
        if isinstance(term, util.string_type):
            qterm = '"%s"' % escVal(term)
            if term in tokens:
                remove_token(tokens, term)
            elif qterm in tokens:
                remove_token(tokens, qterm)
            elif term.find("=") > -1:
                k, v = term.split('=', 1)
                to_remove = []
                for token in tokens:
                    if _equalKVStringTerms(term, token): 
                        to_remove.append(token)

                for term in to_remove:
                    remove_token(tokens, term)

                if k in clause.args:
                    if clause.args[k] == v: 
                        del clause.args[k]

        elif isinstance(term, dict):
            for k, v in term.items():
                v = escVal(v)
                kvString = "%s=%s" % (k, searchVToString(v) )

                if k in clause.args:
                    del clause.args[k]
                elif kvString in tokens:
                    remove_token(tokens, kvString)
                else:
                    to_remove = []
                    for token in tokens:
                        if _equalKVStringTerms(kvString, token): 
                            to_remove.append(token)
                    for term in to_remove:
                        remove_token(tokens, term)

        if len(tokens) == 0:
            clause.args['search'] = '*'
        else:
            clause.args['search'] = ' '.join(tokens)

    return clause

def hasTerm(clause, term):
    """ Does clause contain the given search term? """

    # is term in there as a string? 
    if _hasStringTerm(clause, term):
        return True

    # is {k:v} given term in there as a string?
    if isinstance(term, dict):
        for k, v in term.items():
            kvString = "%s=%s" % (k, searchVToString(v) )
            if _hasStringTerm(clause, kvString):
                return True

    # is {k:v} given term in there as a {k:v}?
    if _hasKVTerm(clause, term):
        return True

    return False

def _hasKVTerm(clause, term):
    """ given term is of form {key:value} """
    if isinstance(term, dict):
        for k, v in term.items():
            if k in clause.args:
                if clause.args[k] == v:
                    return True   # this should match the {k:v} case,
    return False

def _equalKVStringTerms(term1, term2):
    splitters = '<=>'

    for splitter in splitters:
        if term1.find(splitter) > -1 and term2.find(splitter) > -1:
            k1, v1 = term1.split(splitter, 1)
            k2, v2 = term2.split(splitter, 1)
            v1, v2 = v1.strip("\"'"), v2.strip("\"'")
            if k1 == k2 and v1 == v2: return True

    return term1 == term2

def _hasStringTerm(clause, term):
    """ given term is of form "type" or "key=value" """
    tokens = tokenize( clause.args['search'] )
    if isinstance(term, str) or isinstance(term, unicode):
        for token in tokens:
            if '=' in token and '=' in term and not (token.startswith("(") and token.endswith(")") ):
                if _equalKVStringTerms(token, term): return True
            else:
                if term == token: return True
        if term in tokens:
            # this should match the "k=v" and "term" type cases,
            return True
    return False

def searchKVToString(pairs):
    """ Take a dict of KV and spit out a list of k="v" """
    outList = []
    
    if isinstance(pairs, dict):
        for k, v in pairs.items():
            outList.append( "%s=%s" % (searchKToString(k), searchVToString(v) ) )
    else:
        return None

    if len(outList) > 1:
        return outList
    elif len(outList) == 1:
        return outList[0]
    else:
        return []

def searchKToString(k):
    """ Return a quoted version of a fields k, if needed """
    quotedChars = [" "]
    for q in quotedChars:
        if q in k: return '"%s"' % k.strip('"')
    return k

def searchVToString(v):
    """ Given a value, return a search string term in the proper format. """
    if isinstance(v, util.string_type):
        if v.startswith('"') and v.endswith('"') and (len(v)<=2 or v[-2]!="\\"):
            v = v.strip('"')
        return '"%s"' % v
    elif isinstance(v, (float, int)):
        return '%s' % v
    elif isinstance(v, list):
        return ",".join(v)
    return None

def stringToSearchKV(searchString, keepNonKV=True, scrub=False):
    """ convert anything that looks like a k=v pair into dict keys, anything left over
        is put in the 'search' key """
    badStarters = ['(', '[']
    badEnders   = [')', ']']

    if isinstance(searchString, str) or isinstance(searchString, unicode):
        tokens = tokenize(searchString)
        argsDict = {}
        nonKV = []

        for term in tokens:
            if term.find('=') > -1 and not (term[0] in badStarters or term[-1] in badEnders) :
                argsDict[ term.split('=')[0] ] = term.split('=')[1].strip('"')
            else:
                if scrub:
                    return term 

                nonKV.append(term.strip() )

        # are we keeping the tokens that couldn't be split?
        if keepNonKV and not scrub:
            argsDict['search'] = ' '.join(nonKV)

        return argsDict

    else:
        return None

def addSearchKV(clause, key, value, replace=True, seperator='='):
    """ add a kv pair to the args of a clause """

    if clause.args is not None:
        if not isinstance(clause.args, dict):
            clause.args = stringToSearchKV(clause.args)

        if clause.args is None:
            clause.args = {key: value}
        else:
            if (key not in clause.args ) or replace:
                clause.args[key] = value
    else:
        clause.args = {key: value}
    return clause 

def appendClause(pSearch, command, args=None):
    from splunk.search import Parser
    pSearch.clauses.append(Parser.ParsedClause(command=command, args=args))
    return pSearch

def appendClauseAfterCommand(pSearch, command, newCommand):
    """
        Appends a new clause after the clause with the given command.
        Returns a ParsedSearch with the new clause if successful.
        Returns None if not (e.g.
    """
    from splunk.search import Parser
    # default is to append the clause at the end.
    foundIdx = len(pSearch.clauses)
    newCommand = Parser.ParsedClause(command=newCommand)

    # find the clause with the given command
    for clause in pSearch.clauses:
        if clause.command == command:
            foundIdx = pSearch.clauses.index(clause)
            break;

    # insert the new clause
    pSearch.clauses.insert(foundIdx+1, newCommand)

    return pSearch

def removeClause(pSearch, command):
    for clause in pSearch.clauses:
        if clause.command == command:
            pSearch.clauses.remove(clause)
    return pSearch


def getClauseWithCommand(pSearch, command):
    "Given a ParsedSearch and a command, return the first clause with that command"
    for clause in pSearch.clauses:
        if clause.command.lower() in command:
            if isinstance(clause, dict):
                clause = clause['clauses']
            return clause
    return None

def getClausesWithCommand(pSearch, command):
    "Given a ParsedSearch and a command, return a list of clauses with that command"
    clauses = []
    for clause in pSearch.clauses:
        if clause.command.lower() in command:
            clauses.append(clause)
    return clauses

def getReportingClause(pSearch):
    "Given a ParsedSearch, return the first clause with a reporting operator"
    
    # first, search for a clause that has is transforming, this is in the case that the
    # search has already been through the splunkd parser where these properties are set
    for clause in pSearch.clauses:
        if "isTransforming" in clause.properties and clause.properties['isTransforming']:
            return clause

    # in the case that we are dealing with a search we have not yet committed through the
    # search parser: just look for a clause with one of the reporting commands.
    for clause in pSearch.clauses:
        if clause.command in reportingCommands:
            return clause

    return None


def isReportingClause(clause):

    retainsEvents       = splunk.util.normalizeBoolean(clause.properties.get("retainsEvents", "True"))
    isStreaming         = splunk.util.normalizeBoolean(clause.properties.get("isStreaming", "True"))
    isStatefulStreaming = splunk.util.normalizeBoolean(clause.properties.get("isStatefulStreaming", "True"))
    isGenerating        = splunk.util.normalizeBoolean(clause.properties.get("isGenerating", "False"))
    isPrinceStreaming   = clause.properties.get("streamType", None) in ['SP_STREAMREPORT', 'SP_REPORT']
    return isPrinceStreaming or (not retainsEvents and not isStreaming and not isStatefulStreaming and not isGenerating)


def findSearchClauseWithTerm(parsed=None, args=None):
    import copy
    
    term = args
    indexedTerm = False
    # if arg is a dictionary, get term and whether it's an indexed term
    if isinstance(args, dict):
        term = args.get('term', None)
        indexedTerm = args.get('indexed', False)
        # support for old attr:val dict.  {'userid':'6'}
        if term == None:
            # the 'term' is a dict that addTerm will know how to deal with
            term = args

    for pos, c in enumerate(parsed.clauses):
        if isReportingClause(c):            
            break
        if c.command == "search":
            ccopy = copy.deepcopy(c)
            
            removeTerm(ccopy, term)
            cSearchStr = re.sub(' +', ' ', str(c))
            ccopySearchStr = re.sub(' +', ' ', str(ccopy))
            
            if cSearchStr != ccopySearchStr:
                #print("C1 %s            C2 %s" % (c, ccopy))
                return c
            
    return None




###########################################################
### Unit tests

if __name__ == "__main__":
    import unittest
    import splunk.auth
    from splunk.search import Parser

    class TestTransformUtil(unittest.TestCase):
        _sessionKey = splunk.auth.getSessionKey('admin', 'changeme')
        _hostPath   = splunk.mergeHostPath()

        def testHasTerms(self):
            """ Are terms found correctly in search strings? """

            searchString = 'search userid=6 username="nick" owner=ivan login'
            ps = Parser.parseSearch(searchString, hostPath=self._hostPath, sessionKey=self._sessionKey)

            sc = getClauseWithCommand(ps, "search")

            self.assert_( hasTerm(sc, "login") )
            self.assert_( hasTerm(sc, {"username":"nick"}) )
            self.assert_( hasTerm(sc, {"userid":6}) )

            self.assert_( hasTerm(sc, 'username="nick"') )
            self.assert_( hasTerm(sc, 'username=nick') )
            self.assert_( hasTerm(sc, 'owner="ivan"') )
            self.assert_( hasTerm(sc, 'owner=ivan') )
            self.assert_( hasTerm(sc, "userid=6") )

            self.assert_( not hasTerm(sc, "shouldNotBeHere") )
            self.assert_( not hasTerm(sc, {"username":"ivan"}) )
            self.assert_( not hasTerm(sc, {"userid":7}) )

        def testRemoveTerms(self):
            """ Are search terms correctly removed from search strings? """

            searchString = 'search loglevel=7 userid=6 username="nick" owner=ivan target="mars" destination=home login'
            ps = Parser.parseSearch(searchString, hostPath=self._hostPath, sessionKey=self._sessionKey)

            sc = getClauseWithCommand(ps, "search")

            removeTerm(sc, "login")
            self.assert_(sc.serialize().find("login") == -1 )

            removeTerm(sc, {"username" : "nick"} )
            self.assert_(sc.serialize().find('username="nick"') == -1 )

            removeTerm(sc, {"owner" : "ivan"} )
            self.assert_(sc.serialize().find('owner=ivan') == -1 )

            removeTerm(sc, {"userid" : 6} )
            self.assert_(sc.serialize().find('userid=6') == -1 )

            removeTerm(sc, 'target=mars' )
            removeTerm(sc, 'destination="home"' )

            removeTerm(sc, "loglevel=7")
            self.assert_(sc.serialize().find('loglevel=7') == -1 )

            # ELVIS print(sc.serialize())
            self.assert_( sc.serialize() == 'search *' )


            # SPL-32258
            searchString = 'search index=_internal sourcetype=splunkd OR sourcetype=searches'
            ps = Parser.parseSearch(searchString, hostPath=self._hostPath, sessionKey=self._sessionKey)
            sc = getClauseWithCommand(ps, "search")

            removeTerm(sc, {'sourcetype': 'searches'})
            self.assert_(sc, 'index="_internal" sourcetype="splunkd"')
            
            searchString = 'search index=_internal sourcetype=splunkd OR sourcetype=searches'
            ps = Parser.parseSearch(searchString, hostPath=self._hostPath, sessionKey=self._sessionKey)
            sc = getClauseWithCommand(ps, "search")

            removeTerm(sc, {'sourcetype': 'splunkd'})
            self.assert_(sc, 'index="_internal" sourcetype="searches"')

        def testRemoveTermsEscaped(self):
            '''
            Verify remove term behavior when presented with terms that contain
            escape character
            '''

            beforeSearchString = r'search this \\that foo'
            parser = Parser.parseSearch(beforeSearchString, hostPath=self._hostPath, sessionKey=self._sessionKey)
            searchClause = getClauseWithCommand(parser, 'search')
            removeTerm(searchClause, r'\\that')
            self.assertEquals(searchClause.serialize(), 'search this foo')

            beforeSearchString = r'search this \that foo'
            parser = Parser.parseSearch(beforeSearchString, hostPath=self._hostPath, sessionKey=self._sessionKey)
            searchClause = getClauseWithCommand(parser, 'search')
            removeTerm(searchClause, r'\that')
            self.assertEquals(searchClause.serialize(), 'search this foo')



        def testTokenize(self):
            """ Are search strings correctly tokenized? """

            tokenTests = [
                ( 'johnsmith',              ['johnsmith'] ),
                ( 'john smith',             ['john', 'smith'] ),
                ( 'x="y z"',                ['x="y z"'] ),
                ( 'user=Main.JohnSmith',    ['user=Main.JohnSmith'] ),
                ( 'superman "Lex Luther"',  ['superman', '"Lex Luther"'] ),
                ( 'sourcetype=bar',         ['sourcetype=bar'] ),
                ( 'sourcetype::bar',        ['sourcetype=bar'] ),
                ( '( sourcetype=bar )',        ['sourcetype=bar'] ),
                ( 'source="/var/log/*"',    ['source="/var/log/*"'] ),
                ( 'x=p',                    ['x=p'] ),
                ( 'x="p"',                  ['x="p"'] ),
                ( 'NOT x',                    ['NOT x'] ),
                ( 'x NOT y',                    ['x', 'NOT y'] ),
                ( 'x NOT y z',                    ['x', 'NOT y', 'z'] ),
                ( '(toBe OR notToBe) question',    ['(toBe OR notToBe)', 'question'] ),
                ( 'toBe OR notToBe) question',     ['toBe', 'OR', 'notToBe)', 'question'] ),
                ( 'toBe OR notToBe) ) question',   ['toBe', 'OR', 'notToBe)', ')', 'question'] ),
                ( 'toBe OR notToBe)) question',    ['toBe', 'OR', 'notToBe))', 'question'] ),
                ( '((toBe OR notToBe)) question',  ['((toBe OR notToBe))', 'question'] ),
                ( '((toBe OR notToBe question',    ['((toBe OR notToBe question'] ),
                ( '(toBe OR (notToBe)) question',  ['(toBe OR (notToBe))', 'question'] ),
                ( '(toBe (OR (not)ToBe)) question', ['(toBe (OR (not)ToBe))', 'question'] ),
                ( 'error OR failed OR severe OR ( sourcetype=access_* ( 404 OR 500 OR 503 ) ) starthoursago::24',\
                    ['error', 'OR', 'failed', 'OR', 'severe', 'OR', '( sourcetype=access_* ( 404 OR 500 OR 503 ) )', 'starthoursago::24']),
                ( 'error OR failed OR severe OR ( sourcetype="access_*" ( 404 OR 500 OR 503 ) ) starthoursago::24',\
                    ['error', 'OR', 'failed', 'OR', 'severe', 'OR', '( sourcetype="access_*" ( 404 OR 500 OR 503 ) )', 'starthoursago::24']),
                ('search foo [search bar | top host | format]', ['search', 'foo', '[search bar | top host | format]']),
                ('search foo [search bar [search wunderbar] | top host | format]', ['search', 'foo', '[search bar [search wunderbar] | top host | format]']),
                ('search "["', ['search', '"["']),
                ('search "]"', ['search', '"]"']),
                ('search "[[]"', ['search', '"[[]"']),
                ('search "("', ['search', '"("']),
                ('search "(["', ['search', '"(["']),
                ('search "]"', ['search', '"]"']),

                ('search this [search "]"]', ['search', 'this', '[search "]"]']),
                ('search this (that OR ")")', ['search', 'this', '(that OR ")")']),
            ]

            for test in tokenTests:
                self.assertEquals( tokenize(test[0]), test[1] )

        def testStringToKV(self):
            """ Are terms correctly tokenized in KV pairs? """

            self.assertEquals(stringToSearchKV( "index=_audit login" ), {"index":"_audit", "search":"login"} )

        def testEqualStringTerms(self):
            """ Are quotes in kv pairs ignored? """

            self.assert_( _equalKVStringTerms('hello=world', 'hello=world') )
            self.assert_( _equalKVStringTerms('hello=world', 'hello="world"') )
            self.assert_( _equalKVStringTerms("hello='world'", 'hello="world"') )
            self.assert_( _equalKVStringTerms("hello='world'", 'hello=world') )

            self.assertFalse( _equalKVStringTerms("hello='world'", 'hello=wxrld') )

        def testKToString(self):
            """ Are K fields correctly quoted when needed? """

            self.assertEquals(searchKToString("johnsmith" ), 'johnsmith' )
            self.assertEquals(searchKToString("john smith" ), '"john smith"' )
            self.assertEquals(searchKToString('boo'), 'boo' )

        def testKVToString(self):
            """ Are KV pairs correctly merged into search string terms? """

            self.assertEquals(searchVToString("johnsmith" ), '"johnsmith"' )
            self.assertEquals(searchVToString("john smith" ), '"john smith"' )
            self.assertEquals(searchVToString( 26 ), '26' )
            self.assertEquals(searchVToString( '26' ), '"26"' )
            self.assertEquals(searchVToString('"6"'), '"6"' )
            self.assertEquals(searchVToString('"boo"'), '"boo"' )
            self.assertEquals(searchVToString('boo'), '"boo"' )
            
        def testUnfilter(self):
            """ Are the search terms correctly parsed out of search filter wrappers? """

            self.assertEquals( unfilterize( "( index=_audit login ) ( ( * ) )" ), "index=_audit login")
            self.assertEquals( unfilterize( "  ( index=_audit login ) ( ( * ) )" ), "index=_audit login")
            self.assertEquals( unfilterize( "  ( index=_audit login ) ( ( * ) )  " ), "index=_audit login")

    # Execute test suite.
    transformSuite = unittest.TestLoader().loadTestsFromTestCase(TestTransformUtil)
    unittest.TextTestRunner(verbosity=3).run(transformSuite)
