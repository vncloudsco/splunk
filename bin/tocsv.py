#   Version 4.0
import os
import sys
import xml.etree.cElementTree as et

reportfile = ""
resultsfile = ""

def exportSearchResultsToCSV(resultstr):
  resultelement = et.fromstring(resultstr)
  foundEvents = ""
  foundReportEvents = ""
  for resultsChild in resultelement.getchildren(): 
    if resultsChild.tag == "results" : 
      if resultsChild.attrib["type"] == "reportEvents":
        foundReportEvents = resultsChild
      if resultsChild.attrib["type"] == "events":
        foundEvents = resultsChild
  rawOutput = []
  reportOutput = []
  if foundEvents:
    for segText in foundEvents.findall(".//segtext"):
      rawOutput.append("%s\r\n" % segText.text)
    f = open(resultsfile, 'w')
    for x in rawOutput:
      f.write(x)
    f.close()
  if foundReportEvents:
    columnList = foundReportEvents.find("cols")
    csvLine = ""
    for column in columnList.findall("col"):
      csvLine = "%s,%s" % (csvLine, column.text)
      # remove the one extra comma which will have been added in the above step
      csvLine = csvLine.lstrip(",")
      reportOutput.append("%s\r\n" % csvLine) # need the \r\n for windows. 
      # done with that - loop through and add the data now.
      for oneResult in foundReportEvents.findall("result"):
        csvLine = ""
        for oneCol in oneResult.findall("td"):
          # empty <td /> means no value for that field, let's move on.
          if not oneCol.text:
            csvLine = '%s,' % csvLine
          else:
            # instead of escaping all chars like \n & , for csv,
            # just quote it all, and escape " with "".
            # ie, a,bc"de"f,"g" --> "a","bc""de""f","""g"""
            csvLine = '%s,"%s"' % (csvLine, oneCol.text.replace('"', '""'))
        # remove the *ONE* extra comma that was added in the above step.
        if csvLine[0] == ',':
            csvLine = csvLine[1:]
        reportOutput.append("%s\r\n" % csvLine)
    f = open(reportfile, 'w')
    for x in reportOutput:
      f.write(x)
    f.close()
  return None

if __name__ == "__main__":
  splhome = os.environ.get("SPLUNK_HOME")
  if splhome == None:
    splhome = "/opt/splunk"
  reportfile = splhome + "/var/run/splunk/reportresults.csv"
  resultsfile = splhome + "/var/run/splunk/searchres.txt"
  filename = sys.argv[1]
  f = open(filename, 'r')
  xmlstr=""
  for x in f.readlines():
    xmlstr += x
  exportSearchResultsToCSV(xmlstr)
  sys.exit(0)
