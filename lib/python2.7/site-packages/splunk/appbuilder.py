from __future__ import print_function
import os
import socket
import string
import sys
import tarfile
import time
import traceback

from future.moves.urllib import request as urllib_request

import splunk
import splunk.admin as admin
import splunk.clilib.bundle_paths as bundle_paths
import splunk.clilib.cli_common as comm
import splunk.util as util
from splunk.clilib.bundle_paths import make_splunkhome_path


APPS_PATH = bundle_paths.get_base_path()
PACKAGE_PATH = os.path.join(bundle_paths.get_system_bundle_path(), 'static', 'app-packages')
TEMPLATES_PATH = make_splunkhome_path(['share', 'splunk', 'app_templates'])

TEXT_EXTENSIONS = ['txt', 'html', 'htm', 'xhtml', 'css', 'py', 'pl', 'ps1', 'bat', 'sh', 'conf', 'js', 'xml', 'xsl', 'conf', 'meta']
TXT_PREFIX = '__'

'''
Needed to prevent collisions between mako and appbuilder templates
'''
class SafeTemplate(string.Template):
    delimiter = '$$'

'''
Returns Splunkd uri 
'''
def _getSplunkdUri():
    return comm.getMgmtUri().replace('127.0.0.1', socket.gethostname().lower())
    
'''
Returns Splunkweb uri 
'''
def _getSplunkWebUri():
    return comm.getWebUri().replace('127.0.0.1', socket.gethostname().lower())

''' 
Checks if the dir exists and creates it if doesn't
Returns dir path or None
'''
def _getPackageDir():
    if bundle_paths.maybe_makedirs(PACKAGE_PATH):
        return PACKAGE_PATH
    return None
    
'''
Returns local path of an app
'''
def _getAppPath(appName, check_exist=False):
    appPath = os.path.join(APPS_PATH, appName)
    if check_exist and not os.path.exists(appPath):
        return None
    return appPath

'''
We assume files that have one of TEXT_EXTENSIONS or whose name starts with TXT_PREFIX to be templates
Returns a tuple: (filename, isItText)
'''
def _isTextFile(fn):
    if fn.startswith(TXT_PREFIX):
        fn = fn[len(TXT_PREFIX):]
        return (fn, True)
    ext = os.path.splitext(fn)[1][1:]
    return (fn, True) if ext in TEXT_EXTENSIONS else (fn, False)


'''
This needs to handle this a bit better but to support adding static assets by upload this 
method will copy in file that have been donwloaded: todo: find a way to call this method 
with the cgi fs instaed of saveing to a temp dir since its not thread save
'''
def addUploadAssets(appName): 
    appPath = _getAppPath(appName, True)
    if not appPath:
        raise admin.ArgValidationException("App '%s' does not exist" % appName)

    tempPath = make_splunkhome_path(['var', 'run', 'splunk', 'apptemp'])
    # if does not exist then it means no assets exist for moving
    if not os.path.exists(tempPath):
        return

    dstPath = os.path.join(appPath, 'appserver', 'static')
    bundle_paths.maybe_makedirs(dstPath)
    comm.mergeDirs(tempPath, dstPath)

    # clean up
    bundle_paths.safe_remove(tempPath)

    
'''
Returns a list of available app templates
'''
def getTemplates():
    return [f.lower() for f in os.listdir(TEMPLATES_PATH) if os.path.isdir(os.path.join(TEMPLATES_PATH, f))]
        
        
'''
Creates skeleton app from a template
Returns url to the new app
'''
def createApp(appName, template, **kwargs):
    appPath = _getAppPath(appName)
    if os.path.exists(appPath):
        raise admin.AlreadyExistsException("App '%s' already exists. Nothing was created." % appName)
    
    if template not in getTemplates():
        raise admin.ArgValidationException("Template '%s' does not exist." % template)

    # Make sure we don't mess the app.conf file - add a backslash at the eol
    kwargs['description'] = kwargs['description'].replace('\n', '\\\n')        
        
    # Generate files for the app 			
    bundle_paths.maybe_makedirs(appPath)
    os.chdir(appPath)	
    
    templatePath = os.path.join(TEMPLATES_PATH, template)
    
    for root, dirs, files in os.walk(templatePath):
        # determine relative path  
        relPath = root[len(templatePath)+1:]

        # create subdirs
        for dir in dirs:
            bundle_paths.maybe_makedirs(os.path.join(relPath, dir))

        # Read template files and apply param values then save
        for fn in files:
            try:
                # use params to create custom file names
                inFilePath = os.path.join(root, fn)
                # filter by file type
                fn, isText = _isTextFile(fn)
                outFilePath = os.path.join(appPath, relPath, fn)
                if not isText:
                    comm.copyItem(inFilePath, outFilePath)
                    continue

                with open(inFilePath, 'r') as f_in:
                    content = f_in.read()
                    content = SafeTemplate(content).substitute(kwargs)
                    with open(outFilePath, 'w') as f_out:
                        f_out.write(content)
                        
            except:
                print(traceback.print_exc(file=sys.stderr))
                pass

    return '%s/app/%s' % (_getSplunkWebUri(), appName)
        
'''
Installs an app from the location which could be a url or local path string
Returns (Bundle, status) tuple of installed app
'''
def installApp(location, force=False, sslpol=None):
    installer = bundle_paths.BundleInstaller()
    location = location.strip()
        
    try:
        if location.startswith('http'):
            req = urllib_request.Request(url=location)
            return installer.install_from_url(req, force, sslpol)
        else:
            return installer.install_from_tar(location, force)
    except splunk.ResourceNotFound as e:
        raise admin.ArgValidationException(e.msg)
    except splunk.RESTException as e:
        if e.statusCode == 409:
            raise admin.AlreadyExistsException(e.msg)
        raise admin.InternalException(e.msg)
    except Exception as e:
        raise admin.InternalException(e)

'''
Merges local and default parts of an app into default 
Returns the path to the merged app.
'''
def mergeApp(appName):
    appPath = _getAppPath(appName, True)
    if not appPath:
        return None
    tmpPath = os.path.join(PACKAGE_PATH, 'DELETEME_' + appName)
    
    # this should copy app dir to tmp dir
    bundle_paths.maybe_makedirs(tmpPath)
    comm.mergeDirs(appPath, tmpPath)

    localPath = os.path.join(tmpPath, 'local')
    defaultPath = os.path.join(tmpPath, 'default')
    
    # check if the app is allowed to be merged

    if os.path.exists(localPath) and os.path.exists(defaultPath):
        # merge local and default dirs in tmp, result in local
        b = bundle_paths.Bundle('dummy', 'bundle')
        comm.mergeDirs(defaultPath, localPath, False, b._merger)

        # remove default
        bundle_paths.safe_remove(defaultPath)

        # move local to default
        comm.moveItem(localPath, defaultPath)
    
    return tmpPath
    
'''
Packages the appName app to a tar.gz/spl archive, returning the url and local path of the package
By default merges contents of local and default directories with higher precedence of local.
'''
def packageApp(appName, needsMerging=True):
    appPath = mergeApp(appName) if needsMerging else _getAppPath(appName, True)
    if not appPath:
        raise admin.ArgValidationException('The app "%s" cannot be found.' % appName)
        
    packageDir = _getPackageDir()
    tarFile = "%s.tar.gz" % appName
    tarPath = os.path.join(packageDir, tarFile)
    z = tarfile.open(tarPath, 'w:gz')
    
    # walk through files in directory and package them up
    for dirpath, dirnames, files in os.walk(appPath):
        for file in files:
            file = os.path.join(dirpath, file)
            archiveName = os.path.join(appName, file[len(os.path.commonprefix( (appPath, file) ))+1:])
            # skip hidden unix files 
            if os.sep + '.' in archiveName:
                continue
            # skip old default dirs
            if archiveName.startswith(os.path.join(appName, 'default.old.')):
                continue
            # set execution permission flag on extension-less files in bin directory
            if not os.path.isdir(file) and archiveName.startswith(os.path.join(appName, 'bin')):
                info = tarfile.TarInfo(name=archiveName.replace('\\', '/'))
                fobj = open(file, 'rb')
                info.size = os.fstat(fobj.fileno()).st_size
                info.mtime = os.path.getmtime(file)
                info.mode = 0o755
                z.addfile(info, fileobj=fobj)
                fobj.close()
            else:
                z.add(file, archiveName, False)

    z.close()
    
    # cleanup tmp dir
    if needsMerging:
        bundle_paths.safe_remove(appPath)
    
    splTarPath = tarPath.replace('tar.gz', 'spl')
    if os.path.exists(splTarPath):
        bundle_paths.safe_remove(splTarPath)
    os.rename(tarPath, splTarPath)
    
    url = '%s/static/app-packages/%s' % (_getSplunkdUri(), os.path.basename(splTarPath))
    return (url, splTarPath)    
