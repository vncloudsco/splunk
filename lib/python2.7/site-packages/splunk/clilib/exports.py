from __future__ import absolute_import
#   Version 4.0
from builtins import map
import logging as logger
import splunk.clilib.cli_common as comm
import os, re, shutil, sys
from splunk.clilib.control_exceptions import FilePath
from splunk.clilib import bundle_paths
from splunk.clilib.bundle_paths import make_splunkhome_path

# TODO: should the server be up, down, or either for these operations?

def exUserSplunk(args, fromCLI):
  """
  Export users and splunks.
  """
  paramsReq = ("dir",)
  paramsOpt = ()

  comm.validateArgs(paramsReq, paramsOpt, args)

  bakDir = os.path.normpath(args["dir"])

  #
  # No errors found, continue.
  #

  logger.info("Backing up to dir: %s." % bakDir)

  PASS_NAME     = "passwd"
  PASS_FILE_BAK = os.path.join(bakDir, PASS_NAME)
  PASS_FILE     = make_splunkhome_path(["etc", PASS_NAME])

  if not os.path.isdir(bakDir):
    os.makedirs(bakDir)

  if not os.path.exists(PASS_FILE):
    raise FilePath("Unable to find user file '%s', please ensure that SPLUNK_HOME is defined correctly (currently: %s).  Aborting backup." % (PASS_FILE, comm.splunk_home))

  shutil.copy(PASS_FILE, PASS_FILE_BAK)

  try:
    targetFiles = ["savedsearches.conf", "eventtypes.conf"]
    exporter = bundle_paths.BundlesExporter()
    site = bundle_paths.BundlesImportExportSite(bakDir)
    exporter.do_export(targetFiles, site)
  except bundle_paths.BundleException as e:
    raise FilePath("Unable to export: %s.  Aborting backup." % e)


def exEvents(args, fromCLI):
    """
    Export events from the index.
    """
    paramsReq = ("dir", "index")
    paramsOpt = ("host", "source", "sourcetype", "terms")
    
    comm.validateArgs(paramsReq, paramsOpt, args)
    comm.requireSplunkdDown()
    
    args["dir"] = os.path.normpath(args["dir"])
    
    #
    # No errors found, continue.
    #

    index     = args.pop("index")
    dest_path = args.pop("dir")

    i = 3
    query = []

    for metadataType in ("source", "sourcetype", "host"):
        if metadataType in args:
            query.append(metadataType + "::" + args[metadataType])

    # should this handle multi-word terms? question for sorkin. TODO
    if "terms" in args:
        for term in args["terms"].split(" "):
            query.append(term)

    scanAndExport(index, dest_path, query)


def scanAndExport(index, dest_path, query):
    dirs = []

    dre = re.compile("db_\d+_\d+_(\d+)")
    hre = re.compile("hot_v\d+_(\d+)")

    for line in [x for x in os.popen("btool indexes list %s" % index).readlines() if (x.count("Path") > 0)]:
        sl = line.split('=')

        if len(sl) != 2:
            continue

        dbd = bundle_paths.expandvars(sl[1].strip())

        try:
            dl = os.listdir(dbd)
        except:
            continue

        
        for d in dl:
            idx = 2**32
            
            mo = dre.match(d)
            ho = hre.match(d)
            if mo:
                idx = int(mo.group(1))
            elif ho:
                idx = int(ho.group(1))
            elif d != "db-hot":
                continue

            fn = os.path.join(dbd, d)

            if os.path.isdir(fn):
                dirs.append((idx, fn))

    dirs.sort()

    q = " ".join(map((lambda x: "\"" + x + "\""), query))
    for (idx, d) in dirs:
        comm.runAndLog( ["exporttool", d, dest_path, q] )
