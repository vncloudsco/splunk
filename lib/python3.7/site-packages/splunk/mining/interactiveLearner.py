from __future__ import absolute_import
from __future__ import print_function
# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

# runs shell that allows user to teach the system to extract fields interactively

import splunk.mining.dcutils as dcutils
import splunk.mining.positionalsynonyms as positionalsynonyms
from splunk.mining.interactiveutils import printLineSamplings, printQuestion, prompt,addListItems, askYesNoQuestion
from splunk.mining.interactiveutils import getFileNames, askMultipleChoiceQuestion

MAX_LINES_TO_PROCESS = 10000
def presentCandidateExtraction(filenames, fieldname, goodterms, badterms):
    rules = []
    terms = set()
    for filename in filenames:
        theserules, newterms = positionalsynonyms.interactivelyLearn(filename,  fieldname, goodterms, badterms, 5, MAX_LINES_TO_PROCESS)
        rules.extend(theserules)
        terms.update(newterms)
    return rules, terms

def getFieldInfo(filenames):

    printLineSamplings(filenames)

    printQuestion("Specify this field's name.")
    fieldname = prompt("fieldname", False)
    badTerms = []
    goodTerms = []
    rules = []
    done = False
    while not done:
        goodTerms.sort()
        badTerms.sort()
        addListItems("Please specify examples of values to extract.", "good value", goodTerms)
        addListItems("If there are any bad terms extracted, enter them.", "bad value", badTerms)
        rules, terms = presentCandidateExtraction(filenames, fieldname, goodTerms, badTerms)
        print("%u rules" % len(rules))
        orderedTerms = sorted(terms)
        print("Terms Learned: %s" % orderedTerms)
        done = askYesNoQuestion("Are the terms extracted good enough?", True)

    if done == None:
        return None
    print("")
    print("Using values:")
    print("\tFieldname: %s" % fieldname)
    print("\tFiles: %s" % filenames)
    print("\tGoodTerms: %s" % goodTerms)
    print("\tBadTerms: %s" % badTerms)
    return (fieldname, filenames, goodTerms, badTerms, rules)

def getFieldsInfo():
    "process fields"
    fieldsInfo = []
    while True:
        filenames = getFileNames()
        if filenames == None or len(filenames) == 0:
            break
        while True:
            info = getFieldInfo(filenames)
            if info != None:
                fieldsInfo.append(info)
            if not askYesNoQuestion("Learn more fields for this filetype?"):
                break
        if not askYesNoQuestion("Learn fields for additional filetypes?"):
            break
    return fieldsInfo


def  updateRules(rulesdict, fieldsInfo):
    "for each field, add rules to dictionary of rules"
    for fieldInfo in fieldsInfo:
        fieldName, filenames, goodTerms, badTerms, rules = fieldInfo
        positionalsynonyms.addRulesToDict(rulesdict, rules)

def learnFieldsShell():
    "Interactive shell to learn fields for various filetypes"
    fieldsInfo = getFieldsInfo()
    if len(fieldsInfo) > 0 and askYesNoQuestion("Save rules learned?"):
        rulesfile = positionalsynonyms.defaultRulesFile()
        propsfile = positionalsynonyms.defaultPropsFile()
        if not askYesNoQuestion("Runtime system uses the transform configuration file '" + rulesfile + "'.  \nDo you wish to save to this file?"):
            rulesfile = prompt("rules filename", False).strip()
        if not askYesNoQuestion("Runtime system uses the property configuration file '" + propsfile + "'.  \nDo you wish to save to this file?"):
            propsfile = prompt("props filename", False).strip()

        rulesdict = {}
        updateRules(rulesdict, fieldsInfo)
        positionalsynonyms.saveRules(rulesfile, propsfile, positionalsynonyms.getRulesListFromDict(rulesdict))

def testShell():
    import os
    logfile = prompt("full logfile name", False).strip()
    reportexe = os.environ['SPLUNK_HOME'] + '/bin/report'
    os.system('"%s" %s' % (reportexe, logfile))
       
def shell():
    while True:
        try:
            operation = askMultipleChoiceQuestion("What operation do you want to perform? (default=learn)", ['learn', 'test', 'quit'], 'learn')        
            if operation == 'learn':
                learnFieldsShell()
            elif operation == 'test':
                testShell()
            elif operation == 'quit':
                break
        except KeyboardInterrupt:
            print("\n\nReturning to main menu...\n")
            pass
        
if __name__ == '__main__':
    shell()
