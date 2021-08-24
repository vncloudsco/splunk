
import os, tarfile, sys
import subprocess
import logging

logger = logging.getLogger('installit')

def main():
    if len(sys.argv) != 2:
        print("Usage: %s <bundle file to install>" % sys.argv[0])
        print("       Bundle should exist in etc/bundles folder of SPLUNK_HOME.")
        print("       If the bundle has setup.py, untar the bunlde in var/run and invoke setup.py")
        sys.exit(1)

    fullBundleFileName  = sys.argv[1]
    (bundlesPath, bundleFileName) = os.path.split(fullBundleFileName)
    # everything before the last '.', so foo-1234 will be extracted from foo-1324.bundle
    bundleName = bundleFileName.rsplit('.', 1)[0]

    bundleFile  = tarfile.open(fullBundleFileName, 'r')
    try:
        tarinfo = bundleFile.getmember('setup.py')
    except KeyError as err:
        logger.debug('Nothing to be installed for bundle: %s' % fullBundleFileName)
        sys.exit(0)
    
    splunkHome = os.environ["SPLUNK_HOME"] 
    if splunkHome == "":
        logger.error('SPLUNK_HOME is not set. Exiting.')
        sys.exit(1)

    destDir = os.path.join(splunkHome, 'var', 'run', 'installable-bundles', bundleName)
    try:
        logger.debug('Created installation directory: %s', destDir)
        os.makedirs(destDir)
    except OSError as err:
        # errno=17 is 'File exists'. Ignore, it an rewrite over an existing bundle.
        if err.errno != 17:
            logger.error('Error when trying to create directory: %s. Exiting', destDir)
            sys.exit(1)
     
    bundleFile.extractall(destDir)
    setupPy = os.path.join(destDir, 'setup.py')
    python = os.path.join(splunkHome, 'bin', 'python')
    
    logger.info('Setting up %s using script %s' %(bundleName, setupPy)) 
    splunkStart = subprocess.Popen(['python', setupPy], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    consoleOut = open(os.path.join(destDir, 'setup.py.out'), 'w')
    
    for line in splunkStart.stdout:
        logger.debug(line)
        consoleOut.write(line)
        
    consoleOut.close()
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%a, %d %b %Y %H:%M:%S')

    main()
