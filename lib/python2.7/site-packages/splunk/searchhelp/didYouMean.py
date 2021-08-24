from __future__ import absolute_import
from builtins import range
import difflib
import re

from splunk.searchhelp import utils


# how many related fields should we suggest to the user
# when we discover a field not defined in fields.conf
# for eg: 
#  incorrect field: 'indx'
#  related known fields: index1, index2, index3, index4, index5
#  this CONSTANT limits number of related fields to be suggested.
MAX_SUGGESTIONS_PER_FIELD = 3

# of all unknown fields in search, for how many should we 
# provide suggestions
# for eg:
#     incorrect fields in search: indx, line_count, sourcctype
# this CONSTANT limits number of fields for which we show DYM
MAX_FIELD_SUGGESTIONS_PER_SEARCH = 1

# stub gettext if not running from CP
try:
    _
except NameError:
    def _(message):
        return message


# WISH LIST
#   - match fields against tags/descriptions in fields.conf
#   - match whole search commands args to description:
#     - [most common values of a field] = | top FIELD

def help(output, bnf, sessionKey, namespace, user, search, usersquery):
    """did you mean ________?"""
    # if the user entered unknown search commands, suggest some
    #output['notices'].extend(didYouMeanCommands(bnf, search))

    if '|' in usersquery:
        #start = time.time()  #### DEBUG            
        suggestedcommands, othercommands = didYouMeanCommands(bnf, search, user, namespace)
        #logger.error("SHELPER TIMING %s DIDYOUMEAN: commands=%6f" % (sessionKey, time.time() - start)) #### DEBUG
        
        s = usersquery.strip()
        s = s[:s.rindex('|')].strip()
        # make triplets of (command, description, replacement)
        output['autonexts'] = [(x, utils.getAttr(bnf, x, "shortdesc", ""), s + " | " + x) for x in suggestedcommands]
        output['nexts'] = [(x, utils.getAttr(bnf, x, "shortdesc", ""), s + " | " + x) for x in othercommands]

    #start = time.time()  #### DEBUG            
    # if the user entered fields that match very closely to fields in fields.conf, suggest them
    output['notices'].extend(didYouMeanFields(sessionKey, user, namespace, bnf, search))
    #logger.error("SHELPER TIMING %s DIDYOUMEAN: fields=%6f" % (sessionKey, time.time() - start)) #### DEBUG
        
QUALITY_MATCH = 0.8
MEDIUM_MATCH = 0.7
# for unknown search commands, suggest best matches     
def didYouMeanCommands(bnf, search, user, namespace):
    output = []
    # get list of public commands
    knownCommands = utils.getAllCommands(bnf, user, namespace)
    # get list of commands user entered
    userCommandsAndArgs = utils.getCommands(search, None)[-1:] # just last
    searchCommands = [c.strip() for search in userCommandsAndArgs for c, a in search ]
    # get mapping of tags to commands
    tagmap = getTagsToCommands(bnf, knownCommands)

    # for each command user entered 
    for searchCommand in searchCommands:
        # if not known, suggest something
        if not searchCommand in knownCommands:
            suggestion = getSuggestions(knownCommands, searchCommand, tagmap)
            if suggestion != "":
                output.extend(suggestion) #output.append(_('Unknown command "%(command)s". %(suggestion)s' % {'command':searchCommand, 'suggestion':suggestion}))

    return output, knownCommands

def didYouMeanFields(sessionKey, username, namespace, bnf, search):
    knownFields = list(utils.getStanzas("fields", sessionKey, username, namespace).stanzas.keys())
    knownFields = [field.lower() for field in knownFields] # lowercase knownfields
    # preserve the order, do not make a set
    searchFields = re.findall("([a-zA-Z0-9-_]+)=", search.lower())
    suggested = []
    suggestions = []
    # for the last n incorrect fields show suggestions
    for field in reversed(searchFields):
        if len(suggestions) >= MAX_FIELD_SUGGESTIONS_PER_SEARCH:
            break
        # since it is a list, can contain duplicates.
        if field in suggested:
            continue
        
        if field not in knownFields:
            fieldmatches = difflib.get_close_matches(field, knownFields, n=MAX_SUGGESTIONS_PER_FIELD, cutoff=QUALITY_MATCH)
            if len(fieldmatches) > 0:
                #suggestions.append("Unknown field: '%s'. %s" % (field, formatSuggestions(fieldmatches, "field")))
                suggestions.append("%s" % (formatSuggestions(fieldmatches, "field")))
                suggested.append(field)
    return suggestions                                                        

def getSuggestions(commands, command, tagmap):
    # get suggestions of commands that are misspelled
    suggestions = difflib.get_close_matches(command, commands, cutoff=MEDIUM_MATCH)
    if len(suggestions) == 0:
        tags = list(tagmap.keys())
        # see if command matches a tag of a command
        tagmatches = difflib.get_close_matches(command, tags, cutoff=QUALITY_MATCH)
        # for each tag this command is similar to...
        for tag in tagmatches:
            matchingcommands = tagmap[tag]
            # for each command that has that tag...
            for matchingcommand in matchingcommands:
                # if not added as a suggested command, add it
                if not matchingcommand in suggestions:
                    if command != tag:
                        suggestions.append(matchingcommand) # "%s(i.e., %s)" % (matchingcommand, tag))
                    else:
                        suggestions.append(matchingcommand)
    for c in commands:
        if command in c and c not in suggestions:
            suggestions.append(c)
    if len(suggestions) == 0:
        return ""
    suggestions = sortSuggestions(command, suggestions)
    return suggestions
    #return formatSuggestions(suggestions, "", " ")

def sortSuggestions(command, suggestions):
    ordered = []
    # prefix = best matches
    for s in suggestions:
        if s.startswith(command):
            ordered.append(s)
    # subsearch(notprefix) = next best matches            
    for s in suggestions:
        if command in s and not s.startswith(command):        
            ordered.append(s)
    # rest
    for s in suggestions:
        if s not in ordered:
            ordered.append(s)
    return ordered

    

def getTagsToCommands(bnf, knownCommands):
    tagmap = {}
    SEP = re.compile("[, ]+")
    for command in knownCommands:
        cname = command+"-command"
        if cname in bnf:
            tagtext = bnf[cname].get('tags', "")
            tags = SEP.split(tagtext)
            for tag in tags:
                tagmap[tag] = tagmap.get(tag, []) + [command]
    return tagmap
    

def formatSuggestions(suggestions, unitname, determiner = " the "):
    text = _("Did you mean") + determiner
    count = len(suggestions)
    for i in range(0, count):
        if i > 0:
            if i == count-1:
                text += " or "
            else:
                text += ", "
        term = suggestions[i]
        if '(' in term:
            paren = term.index('(')
            text += "'%s' %s" % (term[:paren], term[paren:])
        else:
            text += "'%s'" % (term)
    if unitname != "":
        text += " " + unitname
        if count > 1:
            text += "s"
    text += "? "
    return text
