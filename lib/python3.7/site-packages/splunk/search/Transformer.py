from __future__ import absolute_import
from builtins import range
from builtins import map
from builtins import filter
from builtins import object
import copy
import inspect
import logging
import re
import splunk
import logging
import splunk.entity as entity
import splunk.util as util
import splunk.search.TransformerUtil as TransformerUtil
from splunk.search.Parser import ParsedSearch, deClause
from splunk.search import Parser

logger = logging.getLogger('splunk.search')

###########################################################
### searchTransformer.py
### Responsible for taking ParsedSearch objects and
### munging them

class SearchTransformerException(Exception):
    """ The Transformer can't handle this search """
    pass


def applyIntention(namespace, owner, search, intent, args=None, flags=None):
    """ Factory method for dishing out the correct transform object given an intent """

    if not isinstance(search, ParsedSearch):
        return None

    intentMap = _gatherTransformers('transform')

    if intent in intentMap:
        transformer = intentMap[intent]
    else:
        return search

    argscopy = copy.deepcopy(args)

    # if the transformer requires a reparse (i.e., it needs to know
    # the property flags for search commands), and the search has
    # changed since it was last parsed (i.e., meaning an intention was
    # applied since the last parse)
    if transformer.requiresReparse() and search.isDirty():
        search = Parser.parseSearch(str(search), namespace=namespace, owner=owner)

    return transformer.transform(namespace, owner, parsed=search, args=argscopy, flags=flags)

def decomposeSearch(namespace, owner, parsed, q=None, checkp=True):
    """
    Given a parsed search, decompose the search into a set of intentions that
    could have generated the search.

    Returns a list of intentions and args.
    Order of intentions applied should not matter, so decomposed order shouldn't either.
    """

    import splunk.searchhelp.utils as shutils
    if q != None and '`' in shutils.removeQuotedParts(q):
        raise SearchTransformerException("Not decomposable because search contains a macro.")

    if not isinstance(parsed, ParsedSearch):
        return None

    isDecomp, reason = _isDecomposable(parsed)
    if not isDecomp:
        raise SearchTransformerException("Not decomposable because %s." % reason)

    # no all intentions are decomposble. list only the decomposable here.
    # e.g. how to decompose removeterm?
    decomposableMap = _gatherTransformers('untransform', namespace)

    # each transform should have an untransform/decompose method that
    # that decomposes an intent or set of intents, and returns the decomposed
    # search for the next intent to decompose.

    decomposers = []
    for v in decomposableMap.values():
        decomposers.append(v)

    # sort the decomposers by priority
    decomposers.sort(key=lambda obj: obj.priority)
    decomposers.reverse()

    # make deep copy of original search
    originalParsed = copy.deepcopy(parsed)

    decomposedIntentions = []
    commandlist = [c.command for c in parsed.clauses]
    # from decomposers in order of actual search
    for command in commandlist:
        # for each command, the interested decomposers are allowed to run from highest to lowest priority.  the first to make a change, wins.
        for decomposer in decomposers:
            if command in decomposer.interested:
                parsed, decomposed = decomposer.untransform(namespace, parsed)
                if decomposed != []:
                    decomposedIntentions.extend(decomposed)

    if checkp and _untrustworthyDecomposition(namespace, owner, originalParsed, parsed, decomposedIntentions):
        msg = "Decomposition is not trusted."
        logger.error(msg)
        raise SearchTransformerException(msg)

    return (parsed, decomposedIntentions)

def _untrustworthyDecomposition(namespace, owner, original, decomposedParse, decomposedIntentions):
    try:
        recomposed = copy.deepcopy(decomposedParse)
        # deepcopy the intentions because ivan's plot intention is
        # absurdly modifying the intention (should be readonly).  it
        # trashes the 'field' value and only the field value.
        decompcopy = copy.deepcopy(decomposedIntentions)

        # move addterm intentions to the end because they know where they go intelligently,
        # but if not at the end, then they get applied before commands they should be after
        ordereddecomp  = [i for i in decompcopy if not i[TransformerUtil.INAME].startswith("addterm")]
        ordereddecomp += [i for i in decompcopy if i[TransformerUtil.INAME].startswith("addterm")]

        for intent in ordereddecomp:
            name = intent[TransformerUtil.TransformerUtil.INAME]
            arg  = intent[TransformerUtil.IARG]
            flags= intent.get(TransformerUtil.IFLAGS, None)
            recomposed = applyIntention(namespace, owner, recomposed, name, arg, flags)

        origorder   = [clause.command.lower() for clause in original.clauses]
        recomporder = [clause.command.lower() for clause in recomposed.clauses]

        if origorder != recomporder:
            logger.debug("search original:   %s" % original)
            logger.debug("decomp recomposed: %s" % recomposed)
            # logger.error("-----decomposedParse:   %s" % decomposedParse)
            # logger.error("---- search original:   %s" % original)
            # logger.error("---- decomp recomposed: %s" % recomposed)
            # logger.error("____ decomposedIntentions: %s " % decomposedIntentions)
            return True

    except Exception as e:
        logger.error("Error testing believability of decomposition: %s" % e)
        import traceback
        logger.error(traceback.format_exc())
        # oops there was an exception while applying intentions. Sounds like
        # decomposition is untrustworthy
        return True
    return False


def _gatherTransformers(filter_s, namespace=None):
    """ return a list of the transformer classes """

    intentTransformMap = {}
    transformers = [o for k, o in globals().items() if inspect.isclass(o) and issubclass(o, BaseTransformer) ]
    transformers = [t for t in transformers if hasattr(t, filter_s) ]

    for transformer in transformers:
        intentTransformMap[transformer.name] = transformer()

    # allow app specific decomposition, hack for SPL-32478
    if namespace and filter_s == "untransform":
        web_conf = splunk.bundle.getConf('web', namespace=namespace)
        # get stanza without failure if not present
        settings = web_conf.get("settings")
        if not "enabled_decomposers" in settings:
            # no decomposers wanted
            return {}
        enabled_decomposers = re.split('[, ]+', settings["enabled_decomposers"])
        enabled_decomposers = list(map(str.strip, enabled_decomposers))
        enabled_checker = lambda item: item[0] in enabled_decomposers
        enabled_map = dict(list(filter(enabled_checker, list(intentTransformMap.items()))))
        return enabled_map
    else:
        # not in an app, or for composition
        return intentTransformMap

def _isDecomposable(parsed):
    """
        Determine if the parsed search can be decomposable by this Transformer
        It's not decomposable if...
    """
    unsupportedCommands = ['buckets', 'dedup', 'eval', 'kv', 'rex', 'head', 'stats', 'transam', 'transactions']

    # we can support more than one search clause now.  at least two: an index search and a filter at the end of the eventsearch
    # ... there is more than one 'search' clause
    #if len(getClausesWithCommand(parsed, 'search') ) > 1:
    #    return (False, "more than one search command")

    # ... has unsupported commands (rex, eval, etc.)
    for c in parsed.clauses:
        if c.command in unsupportedCommands:
            return (False, "the %s command is not presently decomposible" % c.command)

    return (True, "OK")

###########################################################
### Transformers cranked out by the factory method above

class BaseTransformer(object):
    # this is the 'null' un/transform
    pass

    name = ''
    priority = 0
    interested=[]

    def requiresReparse(self):
        return False

    #def transform(self, namespace, owner, parsed=None, args=None, flags=None):
    #    return parsed
    #def untransform(owner, parsed=None):
    #    return parsed, []

class UnsupportedCommand(BaseTransformer):
    """ Pulls out commands that are not yet supported by the intents layer and handles them generically """
    name = 'addcommand'
    unsupportedCommands = ['buckets', 'dedup', 'eval', 'kv', 'rex', 'head']
    interested = unsupportedCommands

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        if 'command' in args and 'args' in args:
            command = args.get('command')
            parsed = TransformerUtil.appendClause(parsed, command, args.get('args') )
            newClause = TransformerUtil.getClausesWithCommand(parsed, command ).pop()
            newClause.properties['rawargs'] = args.get('args')

        return parsed

    def untransform(self, namespace, parsed=None):
        actions = []
        killTheseClauses = []
        for clause in parsed.clauses:
            if clause.command.lower() in self.unsupportedCommands:
                actions.append({TransformerUtil.INAME: self.name,
                                TransformerUtil.IARG : {'command': clause.command,
                                        'args'   : clause.args
                               } } )
                killTheseClauses.append(clause.command)

        for c in killTheseClauses:
            TransformerUtil.removeClause(parsed, c)

        return (parsed, actions)

class Stats(BaseTransformer):
    """ Implements the 'stats' command """
    name = 'stats'
    interested = ['stats']
    priority = 0

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        buffer = []

        fields = args.get('fields', None)
        if fields != None:
            for f in fields:
                if f == ['count', '__events', None]:
                    buffer.append('count')
                    continue
                buffer.append('%s(%s)' % (f[0], f[1]) )
                if f[2] != None:
                    buffer.append('as %s' % f[2] )

        groupby = args.get('groupby', None)
        if groupby != None:
            buffer.append( "by %s"   % ' '.join(groupby) )

        parsed = TransformerUtil.appendClause(parsed, 'stats', {'search': ' '.join(buffer) })
        return parsed

    def untransform(self, namespace, parsed=None):
        actions = []
        intent = { TransformerUtil.INAME: self.name, TransformerUtil.IARG: {} }

        statsClause = TransformerUtil.getClauseWithCommand(parsed, "stats")
        if statsClause is not None:

            pDict = statsClause.args

            if 'stat-specifiers' in pDict:
                fields = []
                # pull the statoperators out

                statspec = pDict.get('stat-specifiers')
                if isinstance(statspec, dict):
                    statspec = statspec['clauses']
                for s in statspec:
                    if s['rename'] == 'count':
                        fields.append( ['count', '__events', None] )
                        continue

                    function = s.get('function', None)
                    field = s.get('field', None)
                    rename = s.get('rename', None)

                    fields.append( [function, field, rename] )
                intent[TransformerUtil.IARG]['fields'] = fields

            if 'groupby-fields' in pDict:
                intent[TransformerUtil.IARG]['groupby'] = pDict.get('groupby-fields')

            actions.append( intent )

        parsed = TransformerUtil.removeClause(parsed, "stats")
        return (parsed, actions)

class TermAdd(BaseTransformer):
    """ Add a term to the search clause """

    name = 'addterm'
    priority = -1

    interested = ['search']

    def requiresReparse(self):
        return True


    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        term = args
        indexedTerm = flags and 'indexed' in flags
        forceLast   = flags and 'last' in flags
        quoteSpecial = flags == None or 'QUANT' not in flags
        needsEscaping = not (flags != None and 'ESCAPED' in flags)

        # if arg is a dictionary, get term
        if isinstance(args, dict):
            term = args.get('term', None)
            # support for old attr:val dict.  {'userid':'6'}
            if term == None:
                # the 'term' is a dict that addTerm will know how to deal with
                term = args
        # if just a simple "search foo", add term to that clause
        if indexedTerm or (len(parsed.clauses) == 1 and parsed.clauses[0].command == "search"):
            # if adding index term when search isn't first command: "|
            # crawl" add search before.  hey, if you ask for something
            # stupid it's the best thing to do, rather than die.
            if indexedTerm and parsed.clauses[0].command != "search":
                searchClause = Parser.ParsedClause(command='search')
                parsed.clauses.insert(0, searchClause)
            TransformerUtil.addTerm(parsed.clauses[0], term, quoteSpecial, needsEscaping)
            return parsed

        # find the end of the eventSearch and the begining of the reportSearch
        reportingIdx = -1
        if forceLast:
            reportingIdx = 0# len(parsed.clauses)
            #print("LAST: %s" % parsed.clauses[reportingIdx])
        else:
            for pos, c in enumerate(parsed.clauses):
                if TransformerUtil.isReportingClause(c):
                    reportingIdx = pos #print("BREAKING AT %s POS %s" % (c.command, pos))
                    break
        searchClause = None
        # search | ... | stats | ...
        if reportingIdx > 0:
            # lucky day!  found an existing search at the end of the eventsearch
            # 'search | stats' or 'search | rex | search | stats'.  search clause is one before stats (end of event search)
            if parsed.clauses[reportingIdx-1].command == "search":
                searchClause = parsed.clauses[reportingIdx-1]
            else:
                # else make a search clause with term
                searchClause = Parser.ParsedClause(command='search')
                #searchClause = getClauseWithCommand(parsed, 'search')
                # and insert before first reporting command
                parsed.clauses.insert(reportingIdx, searchClause)
        else: # no reporting search.
            # handle case where already ends in search.
            # search | rex | search.  search clause is last search
            if parsed.clauses[-1].command == "search":
                searchClause = parsed.clauses[-1]
            else:
                # handle case where no search at end
                # search | rex.  search class is new search at end of search
                TransformerUtil.appendClause(parsed, 'search')
                searchClause = TransformerUtil.getClausesWithCommand(parsed, 'search').pop()

        TransformerUtil.addTerm(searchClause, term, quoteSpecial, needsEscaping)
        return parsed

    def untransform(self, namespace, parsed=None):
        actions = []
        searchClauses = TransformerUtil.getClausesWithCommand(parsed, "search")
        if searchClauses is []:
            return (parsed, [])

        # ignore 'search *' as first search for addterm
        if searchClauses[0].command == 'search' and searchClauses[0].args['search'] == '*':
            searchClauses = searchClauses[1:]
        searchClauses =  [searchClauses[0]]

        flags = ['ESCAPED']
        for searchClause in searchClauses:
            indexedTerm = False
            if parsed.clauses.index(searchClause) == 0:
                indexedTerm = True
                flags.append('indexed')

            # process all the tokens in the search arg
            searchTokens = TransformerUtil.tokenize( searchClause.args['search'])
            returnTokens = TransformerUtil.tokenize( searchClause.args['search'])
            for token in searchTokens:
##                 if token == '*' and indexedTerm == False:
##                     returnTokens.remove(token)
##                     continue
                arg = token
                # leave = and :: alone if they are passed in a separate tokens
                if token in ['=','::']:
                    actions.append( { TransformerUtil.INAME: self.name, TransformerUtil.IARG:arg, TransformerUtil.IFLAGS:flags } )
                    returnTokens.remove(token)
                    continue

                # leave parenthesized, quoted, and negated tokens alone
                parenSurround = token.startswith('(') and token.endswith(')')
                quoteSurround = token.startswith('"') and token.endswith('"')
                subSurround   = token.startswith('[') and token.endswith(']')

                startsWithNOT = re.match("NOT\W", token) != None
                if parenSurround or quoteSurround or subSurround or startsWithNOT:
                    # don't extract tokens in subsearches.  too complicated and weird quoting issues
                    if not subSurround:
                        actions.append( { TransformerUtil.INAME: self.name, TransformerUtil.IARG:arg, TransformerUtil.IFLAGS:flags } )
                        returnTokens.remove(token)
                    continue

                # things that look like kv-pairs should be split out
                if token.find("=") > -1:
                    k, v = token.split("=", 1)
                    mismatchParen = k.count('(') != k.count(')')
                    if mismatchParen:
                        actions.append( { TransformerUtil.INAME: self.name, TransformerUtil.IARG:arg, TransformerUtil.IFLAGS:flags } )
                        returnTokens.remove(token)
                        continue
                    if v.startswith('"') and v.endswith('"'):
                        v = v[1:-1]
                    actions.append( { TransformerUtil.INAME: self.name, TransformerUtil.IARG:{k:v}, TransformerUtil.IFLAGS:flags})
                    returnTokens.remove(token)
                    continue
                elif token.find("::") > -1:
                    # for tag::host::value, tag::host is the key
                    k,v = token.rsplit("::", 1)
                    actions.append( { TransformerUtil.INAME: self.name, TransformerUtil.IARG:{k:v}, TransformerUtil.IFLAGS:flags} )
                    returnTokens.remove(token)
                    continue

                # ignore these following tokens
                elif token == "*":
                    continue
                elif (token.find(">")>-1):
                    continue
                elif (token.find("<")>-1):
                    continue

                actions.append( {TransformerUtil.INAME: self.name, TransformerUtil.IARG:TransformerUtil.stringToSearchKV(token, scrub=True), TransformerUtil.IFLAGS:flags} )
                returnTokens.remove(token)

            searchClause.args['search'] = ' '.join(returnTokens)

            if len(searchClause.args['search'].strip()) is 0:
                # if this is the first search, keep it
                if indexedTerm:
                    searchClause.args['search'] = '*'
                else: # otherwise remove it. don't need "search * | search *"
                    parsed.clauses.remove(searchClause)
        #print("CCC %s DDD %s" % (parsed, actions))
        return (parsed, actions)

class TermNegate(BaseTransformer):
    """ Negate a term from the search clause """

    name = 'negateterm'
    interested = ['search']

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        TransformerUtil.addNegatedTerm(parsed.clauses[0], args)
        return parsed

class TermRemove(BaseTransformer):
    """ Remove a simple bare term from the search clause """

    name = 'removeterm'
    interested = ['search']

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        TransformerUtil.removeTerm(parsed.clauses[0], args)
        return parsed

class TermToggle(BaseTransformer):
    """ Toggle simple bare term from the search clause """

    name = 'toggleterm'
    interested = ['search']

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        #if needsQuotes(args):
        #    args = '"%s"' % args

        clause = TransformerUtil.findSearchClauseWithTerm(parsed, args)
        if clause:
            TransformerUtil.removeTerm(clause, args)
            # if the clause is not the first search clause and its
            # search terms are now empty, remove it. don't need
            # "search * | fields | search *"
            if parsed.clauses.index(clause) != 0 and clause.args.get('search', None) == '*':
                parsed.clauses.remove(clause)
        else:
            brother = TermAdd()
            brother.transform(namespace, owner, parsed, args, flags)
        return parsed

class QuantTerm(BaseTransformer):
    """ Class for dealing with quantitative terms.

        Don't handle floats, since floats are not roundtrip accurate.
        There are some decimal numbers that cannot be stored accurately, then
        we add in the formatting 0.0000002 -> 2e-07, lost implied precision,
        etc etc.
    """

    # regexen for greater-than and less-than looking terms
    quantTermRE = r'(?:^|\s+)([^ "]+)\s*%s\s*(\d+)+'

    def addQuantTerm(self, namespace, owner, parsed, args, sep):
        if isinstance(args, dict):
            brother = TermAdd()
            # just use TermAdd on each kv
            for k, v in args.items():
                parsed = brother.transform(namespace, owner, parsed, "%s%s%s" % (k, sep, v), ['QUANT'] )
            return parsed

    def decomposeQuantTerms(self, namespace, parsed, sign, intentName):
        actions = []
        intentDict = {TransformerUtil.INAME: self.name, TransformerUtil.IARG:{}}

        clause = TransformerUtil.getClauseWithCommand(parsed, "search")
        # get the search terms, from the search clause,
        # fail if the clause cannot be found
        if hasattr(clause, "rawargs"):
            searchArgs = clause.rawargs
        if hasattr(clause, "args"):
            searchArgs = clause.args['search']
        else:
            return (parsed, actions)

        if not isinstance(searchArgs, list):
            searchArgs = [searchArgs]
        signedTermRE = self.quantTermRE % sign
        for searchArg in copy.deepcopy(searchArgs):
            matches = re.finditer(signedTermRE, searchArg)
            for match in matches:
                text,k,v = match.group(0), match.group(1), int(match.group(2))
                actions.append({TransformerUtil.INAME: intentName, TransformerUtil.IARG:{k:v} } )
                searchArgs = [arg.replace(text, '') for arg in searchArgs]
        clause.args['search'] = searchArgs
        return (parsed, actions)

class QuantTermAddGreaterThan(QuantTerm):
    """ Class to add terms with greater-than sign """

    name = "addtermgt"
    priority = 1

    interested = ['search']

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        if isinstance(args, dict):
            return self.addQuantTerm(namespace, owner, parsed, args, '>')
        else:
            return parsed

    def untransform(self, namespace, parsed=None):
        return self.decomposeQuantTerms(namespace, parsed, '>', self.name)

class QuantTermAddLessThan(QuantTerm):
    """ Class to add terms with less-than sign """

    name = "addtermlt"
    priority = 1
    interested = ['search']

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        if isinstance(args, dict):
            return self.addQuantTerm(namespace, owner, parsed, args, '<')
        else:
            return parsed

    def untransform(self, namespace, parsed=None):
        return self.decomposeQuantTerms(namespace, parsed, '<', self.name)

class FieldsTransformer(BaseTransformer):

    # regexen for fields clause arg
    # optional group 2: +/-
    # group 3: comma separated field list
    fieldsRE = r'^((\+|\-)\s+)?([\w,_]+)$'

    def extractFieldsFromArgs(self, args=None):
        if args is None:
            return (None, None)

        # given the args from a fields Clause, regex out the
        # +/- and the fields
        m = re.match(self.fieldsRE, args.strip() )
        if m != None:
            op = m.group(2)
            fields = m.group(3).split(',')
        else: return (None, None)

        for f in fields:
            if len(f) < 1 or f is None: fields = None

        return (op, fields)

class FieldsSet(FieldsTransformer):
    """ Add a fields clause to set what fields are returned with results """
    name = 'setfields'
    interested = ['fields']

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        if TransformerUtil.getClauseWithCommand(parsed, "fields") is None:
            #parsed = appendClauseAfterCommand(parsed, "search", "fields")
            parsed = TransformerUtil.appendClause(parsed, "fields")

        fieldsClause = TransformerUtil.getClauseWithCommand(parsed, "fields")

        # append the new fields to the existing fields list
        if isinstance(args, dict):
            if isinstance(args.get('fields', None), list ):
                fieldsClause.args = ','.join(args.get('fields') )
            if args.get('exclusive', False):
                fieldsClause.args = "+ %s" % fieldsClause.args
        else: return parsed

        return parsed

    def untransform(self, namespace, parsed=None):
        # decompose the fields clause
        actions = []

        # find the fields clause, bail if there isn't one found.
        fieldsClause = TransformerUtil.getClauseWithCommand(parsed, 'fields')
        if fieldsClause == None: return (parsed, actions)

        fieldsArgs = fieldsClause.args
        op, fields = self.extractFieldsFromArgs(fieldsArgs)
        if op is None and fields is None: return (parsed, actions)

        intent = {
            TransformerUtil.INAME: self.name,
            TransformerUtil.IARG: {"fields": fields}
        }

        # if the '+' is present in front of the field list, it means
        # we should automatically include the _* fields.
        if op == None:  intent[TransformerUtil.IARG]['exclusive'] = False
        elif op == '+': intent[TransformerUtil.IARG]['exclusive'] = True
        else: return (parsed, actions)

        parsed = TransformerUtil.removeClause(parsed, "fields")
        actions.append(intent)
        return (parsed, actions)

class FieldsExclude(FieldsTransformer):
    """ Add a fields clause to filter out given fields from the results """
    name = 'excludefields'
    interested = ['fields']

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        if TransformerUtil.getClauseWithCommand(parsed, "fields") is None:
            parsed = TransformerUtil.appendClauseAfterCommand(parsed, "search", "fields")

        fieldsClause = TransformerUtil.getClauseWithCommand(parsed, "fields")

        # append the new fields to the existing fields list
        if isinstance(args, dict):
            if isinstance(args.get('fields', None), list ):
                fieldsClause.args = ','.join(args.get('fields') )
                fieldsClause.args = "- %s" % fieldsClause.args
        else: return parsed

        return parsed

    def untransform(self, namespace, parsed=None):
        # decompose the fields clause
        actions = []

        # find the fields clause, bail if there isn't one found.
        fieldsClause = TransformerUtil.getClauseWithCommand(parsed, 'fields')
        if fieldsClause == None: return (parsed, actions)

        fieldsArgs = fieldsClause.args
        op, fields = self.extractFieldsFromArgs(fieldsArgs)
        if op is None and fields is None: return (parsed, actions)
        if op != '-': return (parsed, actions)

        intent = {
            TransformerUtil.INAME: self.name,
            TransformerUtil.IARG: {"fields": fields}
        }

        parsed = TransformerUtil.removeClause(parsed, "fields")
        actions.append(intent)

        return (parsed, actions)


class Audited(BaseTransformer):
    """
        Run this search through the audit processor
        Adds an 'audit' command to a clause.
    """

    name = 'audit'
    interested = ['audit']

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        TransformerUtil.appendClause(parsed, "audit")
        return parsed

    def untransform(self, namespace, parsed=None):
        # delete the audit clause
        auditClause = TransformerUtil.getClauseWithCommand(parsed, "audit")
        if auditClause is not None:
            parsed = TransformerUtil.removeClause(parsed, "audit")
            return (parsed, [ {TransformerUtil.INAME: "audit"} ] )
        else:
            return (parsed, [] )

"""
    class TimeTermExtractor(BaseTransformer):
        Extract old-style time terms from the search string only.
        This does not compose time terms.

        returns an intention of either 'startTimeTerm' or 'endTimeTerm'
        with the following arguments

        args:
            'timeunit'
            'timequantity'
    """
"""
    name='timeterms'
    priority = 100

    timeFormatTermRE = re.compile(r'timeformat=')
    timeTermRE = re.compile(r'(start|end)(months|days|hours)?(time|timeu|ago)+(?:::|=)(\d+)')

    def _hasTimeFormat(self, parsed):
        searchClause = getClauseWithCommand(parsed, "search")
        terms = tokenize(searchClause.args['search'])
        for term in terms:
            if re.match(timeFormatTermRE, term):
                return True

        # if we haven't found any timeformat terms yet, prolly not there.
        return False

    def untransform(self, namespace, parsed=None):
        # extract time terms from the given search string.

        def _absorbTimeTerm(matchObj):
            action = {INAME:"", IARG:{} }

            action[INAME] = "%stimeterm" % matchObj.group(1)
            if matchObj.group(3) == "ago":
                action[IARG]['unit'] = matchObj.group(2)
                action[IARG]['quantity'] = matchObj.group(4)
            elif matchObj.group(3) == "timeu":
                action[IARG]['sinceepoch'] = matchObj.group(4)

            return action

        actions = []
        searchClause = getClauseWithCommand(parsed, "search")
        if (searchClause is None):
            return (parsed, actions)

        searchString = searchClause.args['search']
        terms = tokenize(searchString)

        if searchString is '*': return (parsed, actions)
        if len(terms) < 1: return (parsed, actions)

        # iterate over the terms and extract the time terms
        for term in terms:
            m = re.match(self.timeTermRE, term)
            if m is not None:
                actions.append( _absorbTimeTerm( m ) )

        searchString = re.sub(self.timeTermRE, '', searchString)
        searchClause.args['search'] = searchString

        return (parsed, actions)
"""
"""

class RelativeTimeTermExtractor(BaseTransformer):
        Extract the newer-style relative time terms from the search.
        This does not compose time terms.

        Returns "earliestTime" and/or "latestTime" intent(s)
    """
"""
    name='reltimeterms'
    priority = 101

    baseRelTimeRE = r'%s=((-?\d+)(y|mon|w|d|h|m|s))?(\s|$|@(y|mon|w|d|h|m|s))'

    def untransform(self, namespace, parsed=None):
        times = ['earliesttime', 'latesttime']
        shorttimes = ['earliest', 'latest']
        intents = []

        searchClause = getClauseWithCommand(parsed, 'search')
        if searchClause == None: return (parsed, intents)
        tokens = tokenize(searchClause.args['search'])
        if len(tokens) < 1: return (parsed, intents)

        times.extend(shorttimes)
        for time in times:
            if time in shorttimes: relTimeIntentName = "%stime" % time
            else: relTimeIntentName = time

            action = {INAME:relTimeIntentName, IARG:{} }
            relTimeRE = self.baseRelTimeRE % time

            for token in tokens:
                m = re.match(relTimeRE, token)
                if m is not None:
                    searchClause.args['search'] = re.sub(relTimeRE, '', searchClause.args['search'])
                    groupMap = [
                        (2, 'count'),
                        (3, 'unit'),
                        (5, 'snapUnit')
                    ]
                    for g,l in groupMap:
                        if m.group(g) is not None: action[IARG][l] = m.group(g)
                    intents.append(action)

        return (parsed, intents )
"""

class Sort(BaseTransformer):
    """ Sort search results """
    # sort [<maxResults>] +/- <comma-sep fields>
    # keys:
    # fields := JSON list of fields
    # ascending := T/F
    # [maxresults : = integer]

    # This sort transform does not allow for per-field sorting orders,
    # it also does not do conversions on fields, e.g. sort +ip(host_addr)

    name = 'sort'
    interested = ['sort']
    priority = -1

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        try:
            maxresults = args.get('maxresults', '')
        except ValueError:
            # oops, either the optional maxresults arg was not given
            # or it is not parsable as an integer, default to nothing.
            maxresults = ''
        if args['ascending']:
            order = ''
        else:
            order = '- '

        # fields is given as comma-separated field
        fields = ','.join(args['fields'])

        sortArgs = ("%s %s%s" % (maxresults, order, fields) ).strip()

        TransformerUtil.appendClause(parsed, "sort")
        TransformerUtil.addTerm(parsed.clauses[-1], sortArgs)

        return parsed

    def untransform(self, namespace, parsed=None):
        # decompose the sort clause

        sortClause = TransformerUtil.getClauseWithCommand(parsed, "sort")

        # only process if we actually have a sort clause present
        if sortClause is not None:

            args = sortClause.args.strip()
            limit = re.findall("limit=(\d+)", args)
            if len(limit) > 0:
                args = re.sub("(limit=\d+)", "", args)

            # group(1) should be the optional maxresults
            # group(2) should be the asc/desc option
            # group(3) should be the field list
            sortMatch = re.match('(\d*)\s*([+-]?)\s*(.+)', args)
            if sortClause is not None:
                intentDict = {TransformerUtil.INAME: self.name, TransformerUtil.IARG:{}}

                # set the optional maxresults
                if len(sortMatch.group(1)) > 0:
                    intentDict[TransformerUtil.IARG]['maxresults'] = sortMatch.group(1)
                # or if not there, use the limit= value
                elif len(limit) > 0:
                    intentDict[TransformerUtil.IARG]['maxresults'] = limit[0]

                # set the sort direction
                if sortMatch.group(2) is '-':
                    intentDict[TransformerUtil.IARG]['ascending'] = False
                else:
                    intentDict[TransformerUtil.IARG]['ascending'] = True

                intentDict[TransformerUtil.IARG]['fields'] = TransformerUtil.tokenizeFieldsString( sortMatch.group(3) )

                del parsed.clauses[parsed.clauses.index( sortClause ) ]

                return (parsed, [ intentDict ] )

        return (parsed, [] )

class ChartTransformer(BaseTransformer):
    """ Transformers for Reporting clauses """
    # reporting intents.
    # fields <field> [useother=<bool>] [usenull=<bool>] [ | outlier]
    # top|rare limit=<limit> <field> [useother=<bool] [usenull=<bool>] [ | outlier]
    # timechart mode|sum|stdev|var|max|min|range|avg|count|distict_count(<field>)+ [useother=<bool] [usenull=<bool>] [ | outlier]
    # chart mode|sum|stdev|var|max|min|range|avg|count|distinct_count(<field1>) [by <field2>] [useother=<bool] [usenull=<bool>] [ | outlier]

    # keys:
    # statops := mode|sum|stdev|var|max|min|range|avg|count|distict_count
    # normalizeOutliers, suppressNull, suppressOther

    # intentMap TOC:
    # suppressNull = T/F
    # suppressOther = T/F
    # normalizeOutliers = T/F
    # bins = int
    # span = str
    # mode = chart, time, top, rare
    # fields = List
    # splitby = str
    # statop = mode|sum|stdev|var|max|min|range|avg|count|distict_count

    name = 'plot'
    chartingCommands = ['chart', 'timechart', 'top', 'rare']
    interested = chartingCommands
    agg_funcs = ['mode', 'sum', 'stdev', 'stdevp', 'var', 'varp', 'min', 'max', 'range', 'avg', 'count', 'c', 'distinct_count', 'dc', 'per_second']
    options = ['usenull', 'useother', 'bins', 'span']

    def _processOptions(self, parsed, args):
        """ process any additional options for reporting """
        if not isinstance(args, dict):
            return parsed

        reportingClause = TransformerUtil.getReportingClause(parsed)

        # hide the display of null values in the chart? can only be applied to searches with report clauses
        if 'suppressNull' in args and util.normalizeBoolean(args['suppressNull']):
            TransformerUtil.addSearchKV(reportingClause, 'usenull', 'f', replace=True)

        # hide the display of 'other' values in the chart? can only be applied to searches with report clauses
        if 'suppressOther' in args and util.normalizeBoolean(args['suppressOther']):
            TransformerUtil.addSearchKV(reportingClause, 'useother', 'f', replace=True)

        # only timechart can have bins
        if (args['mode'].lower() == 'timechart') and 'bins' in args:
            TransformerUtil.addSearchKV(reportingClause, 'bins', args['bins'], replace=True)

        # only timechart can have spanss
        if (args['mode'].lower() == 'timechart') and 'span' in args:
            TransformerUtil.addSearchKV(reportingClause, 'span', args['span'], replace=True)

        # Normalize outlier values
        if 'normalizeOutliers' in args and util.normalizeBoolean(args['normalizeOutliers']):
            TransformerUtil.appendClause(parsed, "outlier")


        return parsed

    def _isUserEntered(self, command, args=None):
        if command == None: return False
        if args == None: return False

        tokens = TransformerUtil.tokenize(args)
        # tokens that tell us we are unable to decompose these arguments
        stopTokens = ['as']
        for stopToken in stopTokens:
            if stopToken in tokens: return True

        if command in ['timechart', 'chart']:
            # ignoring tokens after the 'by' word, are all the other tokens decomposable?
            # if any are not decomposable, these args were user entered and we must give up.
            if 'by' in tokens:
                tokens = tokens[:tokens.index('by')]

            chartingRE = re.compile(r'by|(%s)\(\S+\)|(%s)=\w+|count' % ("|".join(self.agg_funcs), "|".join(self.options) ) )
            for token in tokens:
                if not chartingRE.match(token): return True

        return False


    def transform(self, namespace, owner, parsed=None, args=None, flags=None):
        # find an existing clause, if not there, create one
        chartingClause = TransformerUtil.getClauseWithCommand(parsed, self.chartingCommands)
        if chartingClause is None:
            chartingClause = TransformerUtil.getClauseWithCommand( TransformerUtil.appendClause(parsed, "chart"), self.chartingCommands)
        chartingClause.args = {"search":""}

        # what command/mode is this charting command?
        if 'mode' in args:
            if args['mode'] == 'userEntered':
                chartingClause.command = args['userEnteredCommand']
                chartingClause.args    = args['userEnteredArgs']
                return parsed

            if 'fields' in args:
                chartingClause.command = args['mode']
                parsed = self._processOptions(parsed, args)

                # top or rare add clause and the field
                if args['mode'].lower() in ["top", "rare"]:
                    chartingClause.command = args['mode']

                    fields = args['fields']
                    if isinstance(fields, dict):
                        fields = fields['clauses']
                        args['fields'].pop('clauses')
                    elif isinstance(fields, list):
                        pass #args['fields'].pop()
                    else:
                        raise splunk.SearchException("%s: Must have one field here." % self.name)
                    if not isinstance(fields, list) or ( len(fields) == 0 ):
                        raise splunk.SearchException("%s: Must have one field here." % self.name)

                    #chartingClause.args = ",".join(fields) # chartingClause.args = "%s" % args['fields'].pop()
                    chartingClause.args = ''
                    for field in fields:
                        if chartingClause.args != '':
                            chartingClause.args += ','
                        if TransformerUtil.needsQuotes(field):
                            chartingClause.args += '"%s"' % field
                        else:
                            chartingClause.args += field

                    if 'splitbyfields' in args:
                        chartingClause.args += " by %s" % ','.join(deClause(args['splitbyfields'] ))

                    # put back attrs
                    fs = ['limit', 'showperc', 'showcount', 'countfield', 'percentfield']
                    for f in fs:
                        if f in args:
                            TransformerUtil.addSearchKV(chartingClause, f, args[f], replace=True)

                elif args['mode'].lower() in ['timechart', 'chart']:
                    chartingClause.command = args['mode']

                    # drop in the desired statop and optional split by clause for time or chart
                    if 'statop' in args:
                        raise splunk.SearchException("The 'statop' argument has been deprecated.")

                    # 'fields' should now look like [['avg','field1'],['max','field2'],['min','field3']]
                    if ('fields' in args) and (isinstance(args['fields'], list)):
                        for statfieldpair in args['fields']:
                            if isinstance(statfieldpair, list) or isinstance(statfieldpair, tuple):
                                statop, field = statfieldpair

                                #special case here for the 'timechart count' shortcut
                                if statop == 'count' and field == '__events':
                                    TransformerUtil.addTerm(chartingClause, "count")
                                    continue

                                TransformerUtil.addTerm(chartingClause, "%s(%s)" % (statop, field) )
                            elif isinstance(statfieldpair, str):
                                # for cases like adding 'timechart count'
                                TransformerUtil.addTerm(chartingClause, field)

                        if ('splitby' in args):
                            if (len(args['fields']) <= 1):
                                TransformerUtil.addTerm(chartingClause, "by %s" % args['splitby'] )
                            else:
                                raise splunk.SearchException("%s: Cannot split when specifying more than one field." % self.name)

                    else:
                        # if no 'fields' are specified, default to 'timechart count'
                        chartingClause.command = 'timechart'
                        chartingClause.args = "count"
            else:
                # if no 'fields' are specified, default to 'timechart count'
                chartingClause.command = 'timechart'
                chartingClause.args['search'] = "count"
        return parsed


    def untransform(self, namespace, parsed=None, deleteClause=True):
        # decompose a charting clause

        chartClause = None
        chartingCommand = None
        chartingArgs = None
        chartingTokens = []
        intentDict = {TransformerUtil.INAME: self.name, TransformerUtil.IARG:{}}


        # 1. find the charting clause and extract it
        chartClause = TransformerUtil.getClauseWithCommand(parsed, self.chartingCommands)
        if chartClause is not None:

            chartingCommand = chartClause.command

            chartingTokens = TransformerUtil.tokenize(chartingArgs)
            intentDict[TransformerUtil.IARG]['mode'] = chartingCommand

            #if len(chartClause.rawargs) > 0:
            #    chartingArgs = chartClause.rawargs
            #else:
            #    chartingArgs = chartClause.args
            chartingArgs = chartClause.rawargs

            if deleteClause:
                del parsed.clauses[parsed.clauses.index( chartClause ) ]
        else:
            return (parsed, [] )

        # 1.5 does this look like a user-entered 'plot'?
        #    if so, just dump out the rawargs, delete the clause, and call it day.
        if self._isUserEntered(chartingCommand, chartingArgs):
            intentDict[TransformerUtil.IARG]['mode'] = 'userEntered'
            intentDict[TransformerUtil.IARG]['userEnteredArgs'] = chartingArgs
            intentDict[TransformerUtil.IARG]['userEnteredCommand'] = chartClause.command
            return (parsed, [ intentDict ] )

        # 2. extract the optional charting options
        # normalizeOutliers
        outlierClause = TransformerUtil.getClauseWithCommand(parsed, "outlier")
        if outlierClause is not None:
            intentDict[TransformerUtil.IARG]["normalizeOutliers"] = True
            del parsed.clauses[parsed.clauses.index( outlierClause ) ]
        else:
            intentDict[TransformerUtil.IARG]["normalizeOutliers"] = False

        # 3. extract the bins/span args
        if chartingCommand == 'timechart':
            binspanREs = {
                'bins': r'bins=(\d+)',
                'span': r'span=(\S+)'
            }
            for x in binspanREs:
                xRE = re.compile(binspanREs[x])
                xs = xRE.findall(chartingArgs)
                if len(xs) > 0:
                    if x == 'bins':
                        intentDict[TransformerUtil.IARG][x] = int(xs.pop())
                    elif x == 'span':
                        intentDict[TransformerUtil.IARG][x] = xs.pop().strip("\"\'")
                    else:
                        intentDict[TransformerUtil.IARG][x] = xs.pop()
                    re.sub(xRE, '', chartingArgs)

        # 4. process suppressNull/Others; set the defaults first
        intentDict[TransformerUtil.IARG]["suppressNull"] = False
        intentDict[TransformerUtil.IARG]["suppressOther"] = False
        optionsDict = TransformerUtil.stringToSearchKV(chartingArgs)
        if optionsDict is not None:
            for k, v in optionsDict.items():
                if k.lower() == "usenull":
                    intentDict[TransformerUtil.IARG]["suppressNull"] = not util.normalizeBoolean(v)
                if k.lower() == "useother":
                    intentDict[TransformerUtil.IARG]["suppressOther"] = not util.normalizeBoolean(v)
        for term in ['usenull', 'useother']:
            chartingArgs = re.sub(r'%s=\w' % term, '', chartingArgs).strip()

        # 5. do untransforms by inspecting the parsedDictionary
        chartingRaw = chartClause.rawargs
        pDict = chartClause.args
        if chartingCommand in ['top', 'rare']:
            addArgIfNotDefault(pDict, intentDict, 'limit', '10')
            addArgIfNotDefault(pDict, intentDict, 'showperc', 'true')
            addArgIfNotDefault(pDict, intentDict, 'showcount', 'true')
            addArgIfNotDefault(pDict, intentDict, 'countfield', 'count')
            addArgIfNotDefault(pDict, intentDict, 'percentfield', 'percent')

            if "fields" in pDict:
                intentDict[TransformerUtil.IARG]['fields'] = pDict.get("fields")
            if 'splitbyfields' in pDict:
                intentDict[TransformerUtil.IARG]['splitbyfields'] = pDict['splitbyfields']


        elif chartingCommand in ['timechart', 'chart']:
            if "stat-specifiers" in pDict:
                fields = []

                # pull the statoperators out

                statspec = pDict.get('stat-specifiers')
                if isinstance(statspec, dict):
                    statspec = statspec['clauses']
                for s in statspec:
                    if s['rename'] == 'count':
                        fields.append( ['count', '__events'] )
                        continue

                    function = s.get('function', None)
                    field = s.get('field', None)
                    rename = s.get('rename', None)

                    # some of these statops get renamed internally, normalize them back
                    # e.g. dc(objects) => field: objects, function: distinct_count
                    if not rename.startswith(function):
                        function = rename.split('(')[0]

                    fields.append( [function, field] )
                intentDict[TransformerUtil.IARG]['fields'] = fields

            # timechart vs chart tread xfield and seriesfield differently
            if chartingCommand == 'timechart':
                if "seriesfield" in pDict:
                    intentDict[TransformerUtil.IARG]['splitby'] = pDict.get("seriesfield")
            elif chartingCommand == 'chart':
                if "xfield" in pDict and "seriesfield" in pDict:
                    intentDict[TransformerUtil.IARG]['splitby'] = "%s,%s" % ( pDict.get("xfield"), pDict.get("seriesfield") )
                elif "xfield" in pDict:
                    intentDict[TransformerUtil.IARG]['splitby'] = pDict.get("xfield")
        else:
            return (parsed, [] )

        # 6. PROFIT !
        return (parsed, [intentDict] )

class StringReplacement(BaseTransformer):
    """
        DEPRECATED by 'stringreplace'; see $sparkle/controllers/parser.py
        Replace tokens starting and ending with $ with new text.
        Can't be decomposed.

        name: 'replace'
        args: {
                'target' - which placeholder to replace; do not include the $'s
                'replacement' - string to put in place of target
              }
    """

    name = 'replace'

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):

        if 'replacement' in args and 'target' in args:
            targetRE = re.compile( r'\$%s\$' % args['target'] )

            for clause in parsed.clauses:
                if isinstance(clause.args, dict):
                    # handle case where that target is the key of a kv pair.
                    for k, v in clause.args.items():
                        if isinstance(v, list):
                            clause.args[k] = [targetRE.sub(args['replacement'], val ) for val in v]
                        else:
                            clause.args[k] = targetRE.sub(args['replacement'], v )
                elif isinstance(clause.args, str):
                        clause.args = targetRE.sub(args['replacement'], clause.args )

        return parsed






class DrillDown(BaseTransformer):
    """ returns the search that generated a table element
    # xfield:host xarg=server1 colunn=main val=9
    args: {'vals':[['host','server1'], ['avg(cpu)', 10.0]] } 'selected':'cell'}     -- cell click
    args: {'vals':[['host','server1'], ['avg(cpu)', 10.0]] } 'selected':'host'}     -- cell row
    args: {'vals':[['host','server1'], ['avg(cpu)', 10.0]] } 'selected':'avg(cpu)'} -- cell column
    """

    name = 'drilldown'

    #knownTableGenerators = set(['top','rare','stats','chart','timechart'])

    def requiresReparse(self):
        return True

    def transform(self, namespace, owner, parsed=None, args=None, flags=None):

        vals = args.get('vals', None)
        if vals == None or len(vals) == 0:
            raise SearchTransformerException("Drilldown error: 'vals' is empty.")

        selected = vals[1][1]
        if (vals[0][0] == vals[1][0] == vals[1][1] == None) and vals[0][1] != None:
            clickType = "eventTerm"
        elif vals[0][1] == selected:
            clickType = 'row'
        elif vals[1][0] == selected:
            clickType = 'column'
        elif vals[1][1] == selected:
            clickType = 'cell'
        else:
            raise SearchTransformerException("Drilldown error: unsupported dimensionality of clicking.")

        # this is some wacky use of drilldown for clicking on events.
        if clickType == 'eventTerm':
            # flags.append("indexed") # gui will call with indexed setting
            TermToggle().transform(namespace, owner, parsed, vals[0][1], flags)
            return parsed

        if clickType == 'column':
            return addSort(namespace, owner, parsed, vals[1][1])

        # print("CLICKTYPE: %s" % clickType)
        reportingIdx = -1
        for pos in range(len(parsed.clauses)-1, -1, -1):
            c = parsed.clauses[pos]
            if TransformerUtil.isReportingClause(c) or c.command=='dedup':
                reportingIdx = pos
                break
        #print("REPORTINGINDEX %s" % reportingIdx)
        if reportingIdx == 0:
            firstClause = parsed.clauses[0]
            # handle case where first command is reporting AND generating. e.g. metadata
            isGenerating = splunk.util.normalizeBoolean(firstClause.properties.get("isGenerating", "False"))
            if not isGenerating:
                raise SearchTransformerException("Drilldown error: there is no search before the reporting command (i.e., '%s')" %  parsed.clauses[0].command)

        if reportingIdx > 0:
            # keep copy of reporting search
            reportingClauses = parsed.clauses[reportingIdx:]
            checkSafeToDrillDown(reportingClauses, flags)

            vals = fixRenames(reportingClauses, vals)
            # set clauses to everything before reporting
            parsed.clauses = parsed.clauses[:reportingIdx]
            reportGenerator = reportingClauses[0].command
            # print("REPORTGENERATOR %s" % reportGenerator)

            # SPL-46580: don't append _time to the search string when clicked on _time cell
            if (vals[0][0] == vals[1][0] == '_time') and (vals[0][1] == vals[1][1]):
                return parsed

            # move condition to substitutecommand
            #if reportGenerator not in knownTableGenerators:
            #    raise SearchTransformerException("Drilldown is not supported for %s." % reportGenerator)
            postSearch = substituteCommand(reportGenerator, reportingClauses[0].args, vals, clickType, flags)
            #print("postSearch %s" % postSearch)
        else:
            # no reporting
            # append 'search column=val'
            #postSearch = substituteEvents(args, vals, clickType)
            # just use first column
            # search = 'search %s="%s"' % (xfield, xval)
            if clickType == 'column':
                raise SearchTransformerException("Drilldown error: unable to drill down on event '%s' clicks" % clickType)
            if clickType == 'row':
                pass # do nothing.  nick will handle time issues
            else:
                xfield = vals[1][0] #  name of column/y
                xval   = vals[1][1] #  value of column/y
                parsed = TermAdd().transform(namespace, owner, parsed, {xfield:xval})
            return parsed
        #parsed is guaranteed to have clauses at this point
        #verified fixing SPL-47422
        #pylint: disable=E1103
        cmd = parsed.clauses[-1].command
        args = parsed.clauses[-1].properties.get('rawargs', None)
        lastCommand = "%s %s" % (cmd, args)
        appendSearch(namespace, owner, parsed, postSearch, lastCommand)
        return parsed

def deQuoteField(s):
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s

def checkSafeToDrillDown(reportingClauses, flags):

    # if user wants to fly without a safey net, no checking
    if flags != None and 'commando' in flags:
        return

    safePostCommands = set(['head', 'tail', 'reverse', 'dedup', 'fields', 'dedup', 'rename', 'sort', 'search', 'where'])
    for clause in reportingClauses[1:]:
        if clause.command not in safePostCommands:
            raise SearchTransformerException("Unable to drilldown because of post-reporting '%s' command" % clause.command)

def fixRenames(reportingClauses, vals):
    renameMap = {}
    for clause in reportingClauses[1:]:
        if clause.command.lower() == 'rename':
            args = clause.properties['rawargs']
            renames = re.findall('(?i)\s*((?:(?:[^ "]+)|(?:"[^"]*")))\s+as\s+((?:(?:[^ "]+)|(?:"[^"]*")))\s*', args)
            for field, rename in renames:
                field = deQuoteField(field)
                rename = deQuoteField(rename)
                renameMap[rename] = field

    if len(renameMap) > 0:
        newvals = []
        for k, v in vals:
            if k in renameMap:
                k = renameMap[k]
            newvals.append((k, v))
        vals = newvals
    return vals


def addSort(namespace, owner, parsed, field):

##     # chart's column ain't
##     for pos, c in enumerate(parsed.clauses):
##          if isReportingClause(c):
##              colField = c.args.get('seriesfield', None)
##              if colField != None:
##                  print("@@@@@@@@@@@@@@@@@@ SETTING SORT FIELD TO %s from %s" % (colField, field))
##                  field = colField
##                  break

    ascargs = "+%s" % field
    desargs = "-%s" % field
    newargs = ascargs
    # backwards from last command forward
    for pos in range(len(parsed.clauses)-1, -1, -1):
        cmd = parsed.clauses[pos].command
        args = parsed.clauses[pos].properties['rawargs'].strip()
        # if we see anything but a sort command, bail
        if cmd != 'sort':
            break
        # if we're already sorting on this field, remove it, noting
        # which way it was sorted and do the opposite.
        if args == ascargs or args == desargs:
            if args == ascargs:
                newargs = desargs
            deleteClause(parsed, pos)
            break

    sortCommand = [{}, "sort %s" % (newargs)]
    appendSearch(namespace, owner, parsed, sortCommand, 'sort')
    return parsed

def deleteClause(parsed, pos):
    parsed.clauses = parsed.clauses[:pos] + parsed.clauses[pos+1:]


def appendSearch(namespace, owner, parsed, postSearch, lastCommand):
    # do nothing case, caused by 'table' which is 'reporting' but not
    if postSearch == '':
        return
    if postSearch == None:
        raise SearchTransformerException("Drilldown error: unable to drill down from '%s'" % lastCommand)
    # return raw search if clicked on a legend that has no drilldown capability
    if len(postSearch) == 1 and postSearch[0] == {None:None}:
        return

    for a, v in postSearch[0].items():
        parsed = TermAdd().transform(namespace, owner, parsed, {a:v}, ['last'])
    postSearch = '|'.join(postSearch[1:])
    #We need to ensure we have parsed.clauses
    #verified durning fix of SPL-47422
    #pylint: disable=E1103
    parsed.clauses = parsed.clauses or {}
    for postClause in Parser.parseSearch(postSearch, namespace=namespace, owner=owner).clauses:
        parsed.clauses.append(postClause)



def statsSpecVal(args, attr, rename = None):
    vals = []
    statspec = args.get('stat-specifiers', None)
    if statspec != None:
        for c in statspec.get('clauses', []):
            if (rename == None or rename == c['rename']) and attr in c:
                vals.append(c[attr])
    return vals

def countableFunction(args, colfield = None):
    statspec = args.get('stat-specifiers', None)
    if statspec != None:
        # print("looking for colfield: %s" % colfield)
        for c in statspec.get('clauses', []):
            # print("%s COUNTABLE? %s %s" % (c.get('rename'), c.get('function', None), c.get('function', None) in ['count', 'c', 'distinct_count', 'dc']))
            if colfield == None or colfield == c.get('rename', None):
                return c.get('function', None) in ['count', 'c', 'distinct_count', 'dc']
    return False


def substituteCommand(command, args, vals, clickType, flags):
    search = None
    if command == 'stats':
        search = substituteStats(args, vals, clickType, flags)
    elif command == 'chart':
        search = substituteChart(args, vals, clickType, flags)
    elif command == 'timechart':
        search = substituteTimechart(args, vals, clickType, flags)
    elif command == 'top' or command == 'rare':
        search = substituteTop(args, vals, clickType, flags)
    elif command == 'table' or command == 'fields' or command == 'dedup':
        search = substituteEvents(args, vals, clickType, flags)
    return search;

#########
#########  NEED TO HANDLE RENAMES!!!!
########


"""
search foo
{'clauses': [{'args': {'search': ['foo']}, 'command': 'search'}], 'search': 'search foo'}
  - events table -- seems like should be the same as top use case.
    for example...
    - cell click on sourcetype value
      - args      = xfield=_time xval=1234567890 column=sourcetype val=syslog
      - newargs   = [(_time,1234567890),(sourcetype,syslog)]
      - searchout = | search sourcetype=syslog
    - row click
      - NOTE: can't really do a row click.  has to be a click on the first column (generally _time).  unclear what it would do anyway -- limit search to all values?
"""

def substituteEvents(args, vals, clickType, flags):

    # just use first column
    if clickType == 'column':
        raise SearchTransformerException("Drilldown error: unable to drill down on event '%s' clicks" % clickType)

    xfield = vals[1][0] #  name of column/y
    xval   = vals[1][1] #  value of column/y
    search = [{xfield : xval}]

    return search


"""
stats count(user) by host,group

{'search': ['foo ']}, 'command': 'search'}, {'args': {'stat-specifiers': {'clauses': [{'function': 'count', 'field': 'user', 'rename': 'count(user)'}]}, 'groupby-fields': {'clauses': ['host', 'group']}

host        group                   count(user)
localhost   per_sourcetype_thruput    4


    - Note: if function != dc/count, remove 'top'
    - cell
      - args      = xfield=host xval=localhost column=count(user) val=4
      - searchout = | search host=server1 | top user
    - row
      - args      = xfield=host xval=server1
      - searchout = | search host=server1

"""

def substituteStats(args, vals, clickType, flags):

    search = [{}]
    stat_specifiers = args['stat-specifiers']
    groupby_fields  = args.get('groupby-fields', {'clauses':[]})['clauses']

    renames = statsSpecVal(args, 'rename')
    click_field = vals[0][0]  # vals[1][0]
    if click_field not in renames:
        xval   = vals[0][1]       # vals[1][1]
        search = [{click_field : xval}]


    # print("CLICKFIELD: %s", click_field)
    # print("RENAME: %s", renames)
    colfield = vals[1][0]
    if colfield not in renames:
        colval   = vals[1][1]
        search[0][colfield] = colval

    usetop = flags == None or 'keepevents' not in flags
    if usetop and countableFunction(args, colfield):
        countfield = statsSpecVal(args, 'field', colfield)
        search.append('top %s' % countfield[0])
    return search


"""
chart count(user) over host
stats count(user) by   host       *** TODO
'args': {'xfield': 'host', 'stat-specifiers': {'clauses': [{'function': 'count', 'field': 'user', 'rename': 'count(user)'}]}}, 'command': 'chart'}
    host      count(user)
    server1   0
    localhost 10
    - Note: if function != dc/count, remove 'top'
    - cell
      - args      = xfield=host xval=server1 column=count(user) val=11
      - searchout = | search host=server1 | top user
    - row
      - args      = xfield=host xval=server1
      - searchout = | search host=server1

chart dc(date_minute) over group by series
'args': {'xfield': 'group', 'stat-specifiers': {'clauses': [{'function': 'distinct_count', 'field': 'date_minute', 'rename': 'dc(date_minute)'}]}, 'seriesfield': 'series'}

                NULL OTHER audittrail netstat ps
      GROUP  ------------------------------------
      mpool      60   0     60         0      60
      per_host   60   0     60         0      60

    - Note: if function != dc/count, remove 'top'
    - cell
      - args      = xfield=group xval=per_sourcetype_thruput column=netstat val=60
      - searchout = | search group=per_sourcetype_thruput series=netstat | top date_minute
      - NOTE: if column=OTHER then alert("segfault" + 0/0)
    - row
      - args      = xfield=group xval=per_sourcetype_thruput
      - searchout = | search group=per_sourcetype_thruput | top date_minute
"""

def substituteChart(args, vals, clickType, flags):

    if clickType == 'column':
        raise SearchTransformerException("Drilldown error: unable to drill down on chart '%s' clicks" % clickType)

    search = [{}]
    rowField = args['xfield']
    rowVal   = vals[0][1]

    legendClick = vals[0][0] == None and vals[0][1] == None and vals[1][1] == None
    if not legendClick:
        if TransformerUtil.hasSpan(args):
            rowVal = TransformerUtil.splitSpan(rowVal)
        search = [{rowField : rowVal}]

    column = vals[1][0]

    # no by clause
    if 'seriesfield' not in args:
        #if clickType != 'row': # if not on first column (row) then must be on count, which isn't allowed.
        #    raise SearchTransformerException("Drilldown error: unable to drill down on this column")
        # has by clause
        pass
        #if legendClick:
        #    raise SearchTransformerException("Drilldown error: unable to drill down on legend '%s'" % vals[1][0])


    else:
        if column == 'OTHER':
            raise SearchTransformerException("Drilldown error: unable to drill down on 'OTHER'")

        if clickType == 'cell' or legendClick:
            colField = args['seriesfield']
            colName  = vals[1][0]
            # if NULL drilldown (even by another name), use special value to tell addterm() to change it to a NOT field=*
            if colName == args.get('nullstr', 'NULL'): colName = TransformerUtil.NULL_VAL
            search[0][colField] = colName

    usetop = flags == None or 'keepevents' not in flags
    if usetop and countableFunction(args): #, column):
        countfield = statsSpecVal(args, 'field')
        # countfield will be empty if the user does "chart count ..."
        # which is implicit count(_raw), which is pretty meaningless.
        # don't do top then.
        if len(countfield) > 0:
            search.append("top %s" % countfield[0])

    return search


"""
timechart dc(date_second)
'args': {'xfield': '_time', 'stat-specifiers': {'clauses': [{'function': 'distinct_count', 'field': 'date_second', 'rename': 'dc(date_second)'}]}}

      - timechart  (chart where xfield=_time.  TO BE DECIDED somehow handle the earliest/latest values when clicking)
      - Note: if function != dc/count, remove 'top'
    - cell
      - args      = xfield=_time xval=<utctime/utctime> column=dc(date_second) val=60
      - searchout = | top date_second    (set earliest/latest)
    - row
      - args      = xfield=_time xval=<utctime/utctime> _sourcetype_thruput
      - searchout = |<nothing>   (set earliest/latest)

timechart dc(user) by group
'args': {'xfield': '_time', 'stat-specifiers': {'clauses': [{'function': 'distinct_count', 'field': 'user', 'rename': 'dc(user)'}]}, 'seriesfield': 'group'}

      - timechart  (chart where xfield=_time.  TO BE DECIDED somehow handle the earliest/latest values when clicking)
      - Note: if function != dc/count, remove 'top'
    - cell
      - args      = xfield=_time xval=<utctime/utctime> column=admins val=20
      - searchout = | search group=admins (set earliest/latest)  | top user
    - row
      - args      = xfield=_time xval=<utctime/utctime> _sourcetype_thruput
      - searchout = | top uesr (set earliest/latest)


"""

def substituteTimechart(args, vals, clickType, flags):

    search = [{}]

    if clickType != 'cell' and clickType != 'row':
        raise SearchTransformerException("Drilldown error: unable to drill down on timechart '%s' clicks" % clickType)

    # # nick ignores these and handles the time himself
    # # timerange = vals[0][1] #  value of row/x
    # # starttime,endtime = timerange.split('-')

    #print("!!!! Need way to set starttime=%s endtime=%s" % (starttime, endtime))
    # !!!!!!! HAVE TO SUPPORT MULTIPLE CLAUSES NOT JUST [0]
    # {'clauses': [{'function': 'count', 'rename': 'count'}, {'function': 'mean', 'field': 'date_minute', 'rename': 'avg(date_minute)'}]
    usetop = flags == None or 'keepevents' not in flags
    if usetop and countableFunction(args) and 'field' in args['stat-specifiers']['clauses'][0]:
        field = args['stat-specifiers']['clauses'][0]['field']
        search = [{}, "top %s" % field]

    legendClick = vals[0][0] == None and vals[0][1] == None and vals[1][1] == None

    # no by clause
    if 'seriesfield' not in args:
        if clickType == 'row':
            search = [{}]
        #if legendClick:
        #    raise SearchTransformerException("Drilldown error: unable to drill down on legend '%s'" % vals[1][0])

    # has by clause
    else:
        if clickType == 'cell' or legendClick:
            series = args['seriesfield']
            val = vals[1][0] #  value of column/y
            # if NULL drilldown (even by another name), use special value to tell addterm() to change it to a NOT field=*            
            if val == args.get('nullstr', 'NULL'): val = TransformerUtil.NULL_VAL
            search[0][series] = val

    return search

"""
top user,host,date_hour
'args': {'fields': {'clauses': ['user', 'host', 'date_hour']}, 'limit': '10'}

  - top user,host,date_hour
    - cell click on user value
      - args      = xfield=user xval=bob column=user val=bob (first column)
      - newargs   = [(user,bob),(user,bob)]
      - searchout = | search user=bob
    - row click
      - NOTE: this is very weird. row is more specific than clicking on cell. need all values other than count and percent
      - args      = vals:[(user,bob), (host,server1), (date_hour,11)
      - searchout = | search user=bob host=server1, date_hour=11

"""
def substituteTop(args, vals, clickType, flags):
    search = None
    if clickType == 'column':
        raise SearchTransformerException("Drilldown error: unable to drill down on top '%s' clicks" % clickType)
    field, val = vals[-1][0], vals[-1][1]
    if field == 'count' or field == 'percent':
        # SPL-28280 if user clicks on illegal column, fall back on row click
        # # raise SearchTransformerException("Drilldown error: unable to drill down on count or percent")
        field, val = vals[0][0], vals[0][1]
    search = [{field : val}]
    return search



def addArgIfNotDefault(inDict, outDict, field, defaultval):

    if field in inDict:
        val = inDict.get(field)
        if val != defaultval:
            outDict[TransformerUtil.IARG][field] = val
