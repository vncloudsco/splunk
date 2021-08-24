'''
This is an example script for performing rolling upgrade in searchhead cluster
and should not be applied to a production instance without editing to suit
your environment and testing extensively.

Usage of this script:
python shc_upgrade_template.py -u uri_of_member -d directory_of_splunk_home -t timeout_before_shutdown -n new_splunk_package -r remote_ssh_user -s new_splunk_version_number --deployer yes/no --auth user:password

There are some preconditions to run this script:
    1. The upgrade is happening between post-NightLight (including NightLight) to a higher version.
    2. All the bits/binaries that are needed during the upgrading should have been put into place on the machines running Splunks.
    3. The user running this script should have set up the keyless ssh login onto the machines running Splunks.

Workflow of this script:
    1. check SHC status through REST "/services/shcluster/status"
    2. if SHC status is not healthy, exit the script. otherwise
    3. put SHC in upgrade state through REST "/services/shcluster/captain/control/default/upgrade-init"
    4. for each node in the SHC
        4.1 put the node in manual detention through REST "/services/shcluster/member/control/control/set_manual_detention"
        4.2 check the existing search jobs' status through REST "/services/shcluster/member/info"
        4.3 if there is no existing historical search jobs, or the timeout (configurable, and default to 180 seconds) expires, start the upgrade of the node
            4.3.1 stop the node by "splunk stop"
            4.3.2 back up the existing splunk installation (optional)
            4.3.3 untar the new splunk package
            4.3.4 start splunk by "splunk start"?
        4.4 turn off the manual detention through REST "/services/shcluster/member/control/control/set_manual_detention"
    5. finalize the upgrade through REST "/services/shcluster/captain/control/default/upgrade-finalize

'''

import logging as logger
import sys
import os
import requests
import time
import argparse
import subprocess
if sys.version_info >= (3, 0):
    import urllib.parse
    urlparse = urllib.parse.urlparse
else:
    from urlparse import urlparse
from distutils.version import StrictVersion
import distutils.util

def log_status_exit(shc_logger, status, message):
    shc_logger.error(message)
    if status == 401:
        shc_logger.error("Authentication failure: must pass valid credentials with request.")
    else:
        if status == 500:
            shc_logger.error("Internal server error.")
    sys.exit(message)

if __name__ == '__main__':
    # default settings
    USERNAME="admin"
    PASSWORD="changme"
    SSHUSER="root"

    # rest api used
    SHCLUSTER_STATUS_REST = "/services/shcluster/status?output_mode=json"
    UPGRADE_INIT_REST = "/services/shcluster/captain/control/default/upgrade-init?output_mode=json"
    UPGRADE_FINALIZE_REST = "/services/shcluster/captain/control/default/upgrade-finalize?output_mode=json"
    MANUAL_DETENTION_REST = "/services/shcluster/member/control/control/set_manual_detention?output_mode=json"
    MEMBER_INFO_REST = "/services/shcluster/member/info?output_mode=json"
    SHCLUSTER_CONFIG_REST = "/services/shcluster/config?output_mode=json"
    KVSTORE_STATUS_REST = "/services/kvstore/status?output_mode=json"
    TIMEOUT = 180
    TIMEOUT_INTERVAL = 5
    SHC_UPGRADE_BASE_VERSION = "7.1.0"

    #config the logger
    logger.basicConfig(filename='shc_upgrade.log', level=logger.INFO)

    example_text = '''example:

     python shc_upgrade_template.py -u https://example.com:8089 -d /home/user/splunk -t 180 -n /opt/newsplunk.tar.gz -r splunk -s 7.2.2 --auth admin:changed
    '''
    parser = argparse.ArgumentParser(description='SHC upgrade script', epilog=example_text,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-u', '--uri_of_member', required=True, action="store", type=str, help="Specify the mgmt_uri of any member in SHC")
    parser.add_argument('-d', '--directory_of_splunk_home', required=True, action="store", type=str, help="Specify the directory of splunk home")
    parser.add_argument('-n', '--new_splunk_package', required=True, action="store", type=str, help="Specify the full path for the new splunk package")
    parser.add_argument('-t', '--timeout_before_shutdown', action="store", type=int, help="Specify the timeout in seconds this script uses before shutting down splunk. If -1 is given, the script will wait for all non-realtime searches to be completed before shutting down splunk")
    parser.add_argument('-r', '--remote_ssh_user', action="store", type=str, help="Specify the user name used to access remote machines through ssh running SHC")
    parser.add_argument('-s', '--splunk_new_version', required=True, action="store", type=str, help="Specify the version of the new splunk package")
    parser.add_argument('-b', '--backup_directory', action="store", type=str, help="Specify the backup directory if user wants to back up existing splunk before the upgrade happens")
    parser.add_argument('--deployer', action="store", type=str, help="Specify if the deployer needs to be upgraded")
    parser.add_argument('-a', '--auth', action="store", type=str, help="Specify the username and password for the splunk account")

    argList = parser.parse_args()

    # check for username and password
    if argList.auth:
        newauth = argList.auth.split(':')
        if len(newauth) != 2:
            logger.error("Expected argument in 'username:password' format: %s", argList.auth)
            sys.exit("Expected argument in 'username:password' format")
        USERNAME = newauth[0]
        PASSWORD = newauth[1]

    #check ssh login name
    if argList.remote_ssh_user:
        SSHUSER = argList.remote_ssh_user

    # get shc status
    statusUri = argList.uri_of_member + SHCLUSTER_STATUS_REST
    logger.info('calling shc status at: %s', statusUri)
    rStatus = requests.get(
        statusUri, params = {'advanced' : 1},
        auth=(USERNAME, PASSWORD), verify=False)

    if rStatus.status_code != 200:
        message = "Error during getting SHC status"
        log_status_exit(logger, rStatus.status_code, message)

    rStatusJson = rStatus.json()
    # check shc status
    captainInfo = {}
    peerDictOrig = {}
    cluster_master_version = None
    try:
        captainInfo = rStatusJson['entry'][0]['content']['captain']
        if not captainInfo["dynamic_captain"]:
            raise ValueError("SHC does not have a dynamic captain"
                "please fix this before proceeding with rolling upgrade")

        if not captainInfo["stable_captain"]:
            raise ValueError("SHC does not have a stable captain "
                 "please fix this before proceeding with rolling upgrade")

        if not captainInfo["service_ready_flag"]:
            raise ValueError("SHC captain is not ready to provide service "
                 "please fix this before proceeding with rolling upgrade")

        if captainInfo["rolling_restart_flag"]:
            raise ValueError("SHC is in rolling restart "
                "please fix this before proceeding with rolling upgrade")

        if captainInfo["rolling_upgrade_flag"]:
            raise ValueError("SHC is already in rolling upgrade , the reason for the failure "
                 "may be an already existing rolling upgrade is going on, please wait for it to "
                 "finish or may be the script failed in between, so finalize the script "
                 "please fix this issue before proceeding with rolling upgrade")

        if captainInfo["max_failures_to_keep_majority"] <= 0:
            raise ValueError("max_failures_to_keep_majority should be larger than 0 ."
                 "Run show shcluster-status to know which search head does not have the status Up."
                 "Please fix this before proceeding with rolling upgrade")

        # version checking
        if StrictVersion(argList.splunk_new_version) <= StrictVersion(SHC_UPGRADE_BASE_VERSION):
            raise ValueError("the new splunk version number should be larger than %s" % (SHC_UPGRADE_BASE_VERSION))
        cluster_master = rStatusJson['entry'][0]['content']['cluster_master']
        if cluster_master:
            for master in cluster_master:
                version = cluster_master[master]['splunk_version']
                if cluster_master_version is not None:
                    if StrictVersion(version) < StrictVersion(cluster_master_version):
                        cluster_master_version = version
                else:
                    cluster_master_version = version
            if StrictVersion(cluster_master_version) < StrictVersion(argList.splunk_new_version):
                raise ValueError("cluster_master version %s is lower than the new SHC version %s" % (cluster_master_version, argList.splunk_new_version))

        # gather the nodes that are needed to be upgraded
        peerDictOrig = rStatusJson['entry'][0]['content']['peers']
        if len(peerDictOrig) == 0:
            raise ValueError("SHC has no members")
        delete_list = []
        for peer in peerDictOrig:
            if peerDictOrig[peer]['out_of_sync_node']:
                raise ValueError("SHC member %s out_of_sync_node is true" % peerDictOrig[peer]['mgmt_uri'])
            kvstore_status_uri = peerDictOrig[peer]['mgmt_uri'] + KVSTORE_STATUS_REST
            kvstore_status = requests.get(kvstore_status_uri, auth=(USERNAME, PASSWORD), verify=False)
            if kvstore_status.status_code != 200:
                raise ValueError("Can't get KVStore status for SHC member %s" %  peerDictOrig[peer]['mgmt_uri'])
            if kvstore_status.json()['entry'][0]['content']['current']['status'] != "ready":
                raise ValueError("KVStore on SHC member %s is not ready, please fix "
                    "this before proceeding with rolling upgrade" % peerDictOrig[peer]['mgmt_uri'])
            if "splunk_version" in peerDictOrig[peer]:
                if StrictVersion(peerDictOrig[peer]["splunk_version"]) >= StrictVersion(argList.splunk_new_version):
                    delete_list.append(peer)
            else:
                raise ValueError("SHC member %s version number is less than %s" % (peerDictOrig[peer]['mgmt_uri'], SHC_UPGRADE_BASE_VERSION))
        for peer in delete_list:
            peerDictOrig.pop(peer, None)

    except ValueError as err:
        logger.error(err.args)
        sys.exit(err.args)

    peerDictPreferedCaptain = {}
    for peer in peerDictOrig:
        if peerDictOrig[peer]["preferred_captain"]:
            peerDictPreferedCaptain[peer] = peerDictOrig[peer]

    logger.info('The complete member list in shc: %s', peerDictOrig)
    logger.info('The list of members who have preferred_captain set: %s', peerDictPreferedCaptain)

    # signal the start of upgrade
    logger.info("Starting upgrade of the search head cluster")
    initUri = argList.uri_of_member + UPGRADE_INIT_REST
    logger.info("initialize the start of upgrade: %s", initUri)
    rInit = requests.post(
        initUri,
        auth=(USERNAME, PASSWORD), verify=False)
    if rInit.status_code != 200:
        message = "Error during upgrade-init"
        logger.error(message)
        sys.exit(message)

    # default timeout is 180 seconds, user can override it with  "-t timeout_before_shutdown"
    if argList.timeout_before_shutdown:
        TIMEOUT = argList.timeout_before_shutdown
    first = True
    try:
        while len(peerDictOrig):
            # get one peer, avoid captain
            candidate = ""
            selected = False
            # try to pick a perfered captain
            for peer in peerDictPreferedCaptain:
                if peerDictPreferedCaptain[peer]["mgmt_uri"] == captainInfo["mgmt_uri"]:
                    continue
                candidate = peer
                selected = True
                break
            if not selected:
                for peer in peerDictOrig:
                    if peerDictOrig[peer]["mgmt_uri"] == captainInfo["mgmt_uri"]:
                        continue
                    candidate = peer
                    selected = True
                    break
            if not selected:
                errorMessage= ("Upgrade script can't pick a member to upgrade while there are still some upgrade candidates available.\n"
                               "This usually happens when the candidate is holding the captaincy, not transferring the captaincy to an upgraded member.\n"
                               "The root reason might be that the captain is already running a higher version of Splunk, or the SHC is in an unhealthy state.")
                raise ValueError(errorMessage)

            logger.info("selected member %s to upgrade", peerDictOrig[candidate]["label"])

            peer_mgmt_uri = peerDictOrig[candidate]['mgmt_uri']
            detentionUri = peer_mgmt_uri + MANUAL_DETENTION_REST
            logger.info("set %s to manual detention", peer_mgmt_uri)
            rDetention = requests.post(
                detentionUri,
                params={'manual_detention': 'on'}, auth=(USERNAME, PASSWORD), verify=False)

            if rDetention.status_code != 200:
                raise ValueError("Error during setting manual detention")

            infoUri = peer_mgmt_uri + MEMBER_INFO_REST
            timeOut = TIMEOUT
            while True:
                # query status of the node
                logger.info("get member information from %s", infoUri)
                rInfo = requests.get(
                    infoUri,
                    auth=(USERNAME, PASSWORD), verify=False)
                if rInfo.status_code != 200:
                    raise ValueError("Error during getting the member information")

                rInfoJson = rInfo.json()
                status = rInfoJson['entry'][0]['content']['status']
                active_historical_search_count = rInfoJson['entry'][0]['content']['active_historical_search_count']
                if status == 'ManualDetention' and active_historical_search_count == 0:
                    break
                time.sleep(TIMEOUT_INTERVAL)
                timeOut = timeOut - TIMEOUT_INTERVAL
                if TIMEOUT != -1 and timeOut < 0:
                    break

            #Check kvstore status
            start = time.time()
            kvstorestatusInfo = ''
            while kvstorestatusInfo !='ready' and time.time() - start < 240:
                kvstore_status = requests.get(kvstore_status_uri,
                    auth=(USERNAME, PASSWORD), verify=False)
                if kvstore_status.status_code != 200:
                    raise ValueError("Can't get KVStore status for SHC member %s" %
                    peerDictOrig[peer]['mgmt_uri'])
                else:
                    rKvstoreJson = kvstore_status.json()
                    kvstorestatusInfo = rKvstoreJson['entry'][0]['content']['current']['status']
                    if (kvstorestatusInfo != 'ready'):
                        time.sleep(60)

            if kvstorestatusInfo !='ready':
                raise ValueError("KVStore status is still not ready")

            uriResult = urlparse(peer_mgmt_uri)
            splunkcommand=argList.directory_of_splunk_home + "/bin/splunk stop"
            sshcommand = ["ssh", "-l", SSHUSER, uriResult.hostname, splunkcommand]
            logger.info("stop splunk %s", sshcommand)
            sshprocess = subprocess.Popen(sshcommand,
                                          shell=False,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
            sshresult, ssherror = sshprocess.communicate()
            if sshprocess.returncode:
                raise ValueError("Error during stopping splunk: %s" % ssherror)

            # check if we need to back up the existing installation
            if argList.backup_directory:
                backupcommand = "cp -rf " + argList.directory_of_splunk_home + " " + argList.backup_directory
                sshcommand = ["ssh", "-l", SSHUSER, uriResult.hostname, backupcommand]
                logger.info("back up splunk %s", sshcommand)
                sshprocess = subprocess.Popen(sshcommand,
                                              shell=False,
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
                sshresult, ssherror = sshprocess.communicate()
                if sshprocess.returncode:
                    raise ValueError("Error during backing up splunk: %s" % ssherror)

            installcommand = "tar -zxvf " + argList.new_splunk_package + " -C " + os.path.dirname(argList.directory_of_splunk_home)
            sshcommand = ["ssh", "-l", SSHUSER, uriResult.hostname, installcommand]
            logger.info("upgrade splunk %s", sshcommand)
            sshprocess = subprocess.Popen(sshcommand,
                                          shell=False,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
            sshresult, ssherror = sshprocess.communicate()
            if sshprocess.returncode:
                raise ValueError("Error during upgrading splunk: %s" % ssherror)

            splunkcommand = argList.directory_of_splunk_home + "/bin/splunk start --accept-license --answer-yes"
            sshcommand = ["ssh", "-l", SSHUSER, uriResult.hostname, splunkcommand]
            logger.info("start splunk %s", sshcommand)
            sshprocess = subprocess.Popen(sshcommand,
                                          shell=False,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
            sshresult, ssherror = sshprocess.communicate()
            if sshprocess.returncode:
                raise ValueError("Error during starting splunk: %s" % ssherror)

            # turn off manual detention
            logger.info("turn off manual detention for %s", peer_mgmt_uri)
            rDetention = requests.post(
                detentionUri,
                params={'manual_detention': 'off'}, auth=(USERNAME, PASSWORD), verify=False)
            if rDetention.status_code != 200:
                raise ValueError("Error during turning off manual detention")

            # post processing after the node is upgraded
            logger.info("waiting for the shc to be stable ...")
            time.sleep(60)
            peerDictOrig.pop(candidate, None)
            peerDictPreferedCaptain.pop(candidate, None)

            # update for possible new captain
            statusUri = argList.uri_of_member + SHCLUSTER_STATUS_REST
            logger.info('calling shc status at: %s', statusUri)
            rStatus = requests.get(
                statusUri, params={'advanced': 1},
                auth=(USERNAME, PASSWORD), verify=False)
            if rStatus.status_code != 200:
                raise ValueError("Error during getting SHC status")

            rStatusJson = rStatus.json()
            # update the captain
            captainInfo = rStatusJson['entry'][0]['content']['captain']

        # check if deployer needs to be upgraded
        if argList.deployer and distutils.util.strtobool(argList.deployer):
            configUri = captainInfo['mgmt_uri'] + SHCLUSTER_CONFIG_REST
            logger.info('getting deployer information at: %s', configUri)
            rStatus = requests.get(
                configUri, auth = (USERNAME, PASSWORD), verify = False)
            if rStatus.status_code != 200:
                raise ValueError("Error during getting deployer information")
            rStatusJson =  rStatus.json()
            deployerInfo = rStatusJson['entry'][0]['content']['conf_deploy_fetch_url']
            if deployerInfo:
                uriResult = urlparse(deployerInfo)
                splunkcommand = argList.directory_of_splunk_home + "/bin/splunk stop"
                sshcommand = ["ssh", "-l", SSHUSER, uriResult.hostname, splunkcommand]
                logger.info("stop splunk %s", sshcommand)
                sshprocess = subprocess.Popen(sshcommand,
                                              shell=False,
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
                sshresult, ssherror = sshprocess.communicate()
                if sshprocess.returncode:
                    raise ValueError("Error during stopping deployer: %s" % ssherror)

                installcommand = "tar -zxvf " + argList.new_splunk_package + " -C " + os.path.dirname(
                    argList.directory_of_splunk_home)
                sshcommand = ["ssh", "-l", SSHUSER, uriResult.hostname, installcommand]
                logger.info("upgrade splunk %s", sshcommand)
                sshprocess = subprocess.Popen(sshcommand,
                                              shell=False,
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
                sshresult, ssherror = sshprocess.communicate()
                if sshprocess.returncode:
                    raise ValueError("Error during upgrading deployer: %s" % ssherror)

                splunkcommand = argList.directory_of_splunk_home + "/bin/splunk start --accept-license --answer-yes"
                sshcommand = ["ssh", "-l", SSHUSER, uriResult.hostname, splunkcommand]
                logger.info("start splunk %s", sshcommand)
                sshprocess = subprocess.Popen(sshcommand,
                                              shell=False,
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
                sshresult, ssherror = sshprocess.communicate()
                if sshprocess.returncode:
                    raise ValueError("Error during starting deployer: %s" % ssherror)

    except ValueError as err:
        logger.error(err.args)
        sys.exit(err.args)
    finally:
        finalizeUri = argList.uri_of_member + UPGRADE_FINALIZE_REST
        logger.info('finalize the shc upgrade %s', finalizeUri)
        rFinalize = requests.post(
            finalizeUri,
            auth=(USERNAME, PASSWORD), verify=False)

    print('SHC is upgraded successfully')
    logger.info('SHC is upgraded successfully')
    sys.exit(0)
