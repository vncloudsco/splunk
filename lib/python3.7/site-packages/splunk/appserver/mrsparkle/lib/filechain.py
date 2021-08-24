from __future__ import absolute_import
import cssmin
import hashlib
import logging
import os.path
import shutil
import subprocess
import threading
import traceback
import sys

import splunk.appserver.mrsparkle.lib.i18n as i18n
import splunk.appserver.mrsparkle.lib.startup as startup
import splunk.appserver.mrsparkle.lib.util as util
import splunk.util

import splunk.appserver.mrsparkle.lib.apps as apps
import splunk.appserver.mrsparkle.lib.module as libmodule

import cherrypy

logger = logging.getLogger('splunk.appserver.lib.filechain')

MODULE_STATIC_CACHE_PATH = util.make_absolute(os.path.join('var', 'run', 'splunk', 'appserver', 'modules', 'static'))

MRSPARKLE = util.make_absolute(os.path.join('share', 'splunk', 'search_mrsparkle'))

PATH_TO_JSMIN = util.make_absolute(os.path.join('bin', 'jsmin'))

# define the filename prefixes for the cached versions of the concatenated
# static resources
MODULE_JS_FILE_PREFIX = 'modules.min.js'
MODULE_CSS_FILE_PREFIX = 'modules-'


'''
This is the logic to minify and chain various sets of CSS and JavaScript.  The discrete chunks are the modules
JS (anything found in getInstalledModules() in moduleMapper), common JS (anything in exposed/js and exposed JS/contrib)
and the modules CSS (again, from getInstalledModules())

These routines should be called either at startup or at build time, unless i18n can be sped up enough to
make it practical to call these on the fly.
'''

_chain_modules_js_lock = threading.Lock()
def chain_modules_js(files):
    # we could create a lock for each hash instead of a global lock here
    # but the savings of potentially generating/checking different module groups concurrently
    # probably isn't worth managing a dictionary of locks
    with _chain_modules_js_lock:
        logger.debug('Chaining and minifying modules JS')
        try:
            locale = i18n.current_lang(True)

            modules = libmodule.moduleMapper.getInstalledModules()

            hash = generate_file_list_hash(files)
            cache_filename = util.make_absolute(os.path.join(i18n.CACHE_PATH, '%s-%s-%s.cache' % (MODULE_JS_FILE_PREFIX, hash, locale)))
        
            if os.path.exists(cache_filename) and os.path.getsize(cache_filename) != 0:
                cache_mtime = os.path.getmtime(cache_filename)

                # check if root directory was modified (app installed, etc., where indiv. timestamps may be well in the past)
                if cache_mtime < os.path.getmtime(os.path.join(MRSPARKLE, 'modules')) or cache_mtime < os.path.getmtime(util.make_absolute(os.path.join('etc', 'apps'))):
                    os.unlink(cache_filename)
                else:
                    # check individual files, so if they've been touched we'll poison the cache
                    for input_filename in files:
                        parts = os.path.normpath(input_filename.strip('/')).replace(os.path.sep, '/').split('/')
                        if len(parts) == 2:
                            input_path = os.path.join(MRSPARKLE, *parts)
                        else:
                            module_path = apps.local_apps.getModulePath(parts[1])
                            if module_path == False:
                                logger.debug("module_path returned False")
                                break
                            input_path = os.path.join(module_path, *parts[2:])
                        if cache_mtime < os.path.getmtime(input_path):
                            os.unlink(cache_filename)
                            break
            
                if os.path.exists(cache_filename) and os.path.getsize(cache_filename) != 0:
                    return cache_filename
        
            output_fh = open(cache_filename, 'wb')
        
            # many duplicate JS translation blocks
            blocks = []
            js = ''
            moduleName = None
            err = ''
            wrap_try_catch = splunk.util.normalizeBoolean(cherrypy.config.get('trap_module_exceptions', True))
            for input_filename in files:
                parts = os.path.normpath(input_filename.strip('/')).replace(os.path.sep, '/').split('/')
                if len(parts) == 2:
                    input_path = os.path.join(MRSPARKLE, *parts)
                    # since we don't have the module name from something like /modules/AbstractModule.js, try
                    # to figure it out from the module list
                    for key in modules:
                        if modules[key]['js'].endswith(os.path.join(*parts)):
                            moduleName = key
                            break
                else:
                    module_path = apps.local_apps.getModulePath(parts[1])
                    if module_path == False:
                        logger.debug("module_path returned False")
                        break
                    input_path = os.path.join(module_path, *parts[2:])

                    for key in modules:
                        if modules[key]['js'].endswith(os.path.join(*parts)):
                            moduleName = key
                            break
                
                # SPL-59142. in an event of unknown moduleName, the error 
                # message should point out which file caused the execption.
                if moduleName is not None:
                    # great we know what module and app it is
                    err = 'The module \'%s\' in the \'%s\' app ' % (moduleName, modules[moduleName]['appName'])
                else:
                    # we donno, let us atlest mention the filename that leads to execption.
                    err = 'File \'%s\' ' % input_filename
                err += 'has thrown an unexpected error and may not function properly. Contact the app author or disable the app to remove this message. '
                
                block = i18n.generate_wrapped_js(input_path, locale)
                if block:
                    if block not in blocks:
                        blocks.append(block)
                    if wrap_try_catch:
                        js += 'try{\n'
                    js += block + '\n'
                input_temp_fh = open(input_path, 'r')
                js += input_temp_fh.read() + ';\n'
                input_temp_fh.close()
                if block and wrap_try_catch:
                    js += '}catch(e){var err=" %s ";if(window.console){window.console.log(e);}$(function(){Splunk.Messenger.System.getInstance().send("error","%s",err);});}\n' % (err, err)

            minifier = util.Popen([PATH_TO_JSMIN], stdin = subprocess.PIPE, stderr = subprocess.STDOUT, stdout = subprocess.PIPE, close_fds = True)
            (data, _) = minifier.communicate(js.encode())
            if sys.version_info >= (3, 0):
                data = data.decode()

            if minifier.returncode != 0:
                logger.error('While minifying modules JavaScript, jsmin (pid %d) returned code %d' % (minifier.pid, minifier.returncode))
                logger.error('Disabling minification of JavaScript and CSS')
                cherrypy.config['minify_js'] = False
                cherrypy.config['minify_css'] = False
            else:
                output_fh.write(splunk.util.toUTF8(data))
                output_fh.close()

                return cache_filename
        except IOError:
            logger.error('While minifying modules JavaScript, the following exception was thrown: %s Stack:  %s' % (traceback.format_exc(), traceback.format_stack()))
            logger.error('Disabling minification of JavaScript and CSS')
            cherrypy.config['minify_js'] = False
            cherrypy.config['minify_css'] = False
            try:
                if os.path.exists(cache_filename):
                    os.unlink(cache_filename)
            except:
                pass
        finally:
            try:
                input_temp_fh.close()
            except:
                pass
            try:
                output_fh.close()
            except:
                pass
            

_chain_common_js_lock = threading.Lock()
def chain_common_js():
    '''
    Add translations to the common JS in share/splunk/search_mrsparkle/exposed/js, EXCLUDING anything in contrib/,
    which does not need translations
    '''
    with _chain_common_js_lock:
        logger.debug('Chaining and minifying common JS')
        try:
            locale = cherrypy.request.lang # defaults to en_US, handy for precaching in root.py 
            js_root = os.path.join(MRSPARKLE, 'exposed', 'js')
            cache_filename = util.make_absolute(os.path.join(i18n.CACHE_PATH, '%s-%s-%s.cache' % ('common.min.js', hashlib.sha1(b'common.min.js').hexdigest(), locale)))
            js_filenames = startup.generateJSManifest(True)
        
            if os.path.exists(cache_filename) and os.path.getsize(cache_filename) != 0:
                cache_mtime = os.path.getmtime(cache_filename)

                # if any .js files were touched, one of js_root or js_root/contrib will have the bumped timestamp
                if cache_mtime < os.path.getmtime(js_root) or cache_mtime < os.path.getmtime(js_root + os.sep + 'contrib'):
                    os.unlink(cache_filename)
                elif cache_mtime < os.path.getmtime(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'startup.py')):
                    os.unlink(cache_filename)
                else:
                    return cache_filename
        
            output_fh = open(cache_filename, 'wb')
        
            # many duplicate JS translation snippets
            blocks = []
            js = ''
            for js_filename in js_filenames:
                if js_filename == 'i18n.js':
                    path = i18n.dispatch_i18n_js(os.path.join(js_root, 'i18n.js'))
                    input_temp_fh = open(path, 'rb')
                    out = input_temp_fh.read()
                    if sys.version_info >= (3, 0): out = out.decode()
                    js += out + '\n'
                    input_temp_fh.close()
                else:
                    path = os.path.join(js_root, js_filename)
                    if os.sep + 'contrib' + os.sep not in path:
                        block = i18n.generate_wrapped_js(path, locale)
                        if block and block not in blocks:
                            blocks.append(block)
                            js += block + '\n'
                    input_temp_fh = open(path, 'r')
                    js += input_temp_fh.read() + ';\n'
                    input_temp_fh.close()
            
            minifier = util.Popen([PATH_TO_JSMIN], stdin = subprocess.PIPE, stderr = subprocess.STDOUT, stdout = subprocess.PIPE, close_fds = True)
            (data, _) = minifier.communicate(js.encode())
            if sys.version_info >= (3, 0):
                data = data.decode()
            
            if minifier.returncode != 0:
                logger.error('While minifying common JavaScript, jsmin (pid %d) returned code %d' % (minifier.pid, minifier.returncode))
                logger.error('Disabling minification of JavaScript and CSS')
                cherrypy.config['minify_js'] = False
                cherrypy.config['minify_css'] = False
            else:
                output_fh.write(splunk.util.toUTF8(data))
                output_fh.close()
        
                return cache_filename
        except IOError:
            logger.error('While minifying common JavaScript, the following exception was thrown: %s Stack:  %s' % (traceback.format_exc(), traceback.format_stack()))
            logger.error('Disabling minification of JavaScript and CSS')
            cherrypy.config['minify_js'] = False
            cherrypy.config['minify_css'] = False
            try:
                if os.path.exists(cache_filename):
                    os.unlink(cache_filename)
            except:
                pass
        finally:
            try:
                input_temp_fh.close()
            except:
                pass
            try:
                output_fh.close()
            except:
                pass

def chain_modules_css(files):
    logger.debug('Chaining and minifying modules CSS')
    try:
        if not os.path.exists(os.path.join(MODULE_STATIC_CACHE_PATH, 'css')):
            os.makedirs(os.path.join(MODULE_STATIC_CACHE_PATH, 'css'))
    
        hash = generate_file_list_hash(files)
    
        cache_filename = util.make_absolute(os.path.join(MODULE_STATIC_CACHE_PATH, 'css', MODULE_CSS_FILE_PREFIX + hash + '.min.css'))
    
        if os.path.exists(cache_filename) and os.path.getsize(cache_filename) != 0:
            cache_mtime = os.path.getmtime(cache_filename)
            for input_filename in files:
                if input_filename.startswith('/modules/'):
                    parts = os.path.normpath(input_filename.strip('/')).replace(os.path.sep, '/').split('/')
                    if len(parts) == 2:
                        input_path = os.path.join(MRSPARKLE, *parts)
                    else:
                        module_path = apps.local_apps.getModulePath(parts[1])
                        if module_path == False:
                            logger.debug("module_path returned False")
                            break
                        input_path = os.path.join(module_path, *parts[2:])
                    if cache_mtime < os.path.getmtime(input_path):
                        os.unlink(cache_filename)
                        break
        else:
            # cache_filename opened 'wb' below, no need to unlink() here if it's 0 bytes
            pass
    
        if os.path.exists(cache_filename) and os.path.getsize(cache_filename) != 0:
            return cache_filename
    
        output_fh = open(cache_filename, 'wb')
    
        for input_filename in files:
            if input_filename.startswith('/modules/'):
                parts = os.path.normpath(input_filename.strip('/')).replace(os.path.sep, '/').split('/')
                if len(parts) == 2:
                    input_path = os.path.join(MRSPARKLE, *parts)
                else:
                    module_path = apps.local_apps.getModulePath(parts[1])
                    if module_path == False:
                        logger.debug("module_path returned False")
                        break
                    input_path = os.path.join(module_path, *parts[2:])

                input_temp_fh = open(input_path, 'rb')
                out = input_temp_fh.read()
                if sys.version_info >= (3, 0): out = out.decode()
                output_fh.write(splunk.util.toUTF8(cssmin.cssmin(out)))
                input_temp_fh.close()
    
        return cache_filename
    except IOError:
        logger.error('While minifying modules CSS, the following exception was thrown: %s Stack:  %s' % (traceback.format_exc(), traceback.format_stack()))
        logger.error('Disabling minification of JavaScript and CSS')
        cherrypy.config['minify_js'] = False
        cherrypy.config['minify_css'] = False
        try:
            if os.path.exists(cache_filename):
                os.unlink(cache_filename)
        except:
            pass
    finally:
        try:
            input_temp_fh.close()
        except:
            pass
        try:
            output_fh.close()
        except:
            pass

def generate_file_list_hash(l):
    joined = ''.join(l)
    if sys.version_info >= (3, 0):
        joined = joined.encode('utf-8')
    return hashlib.sha1(joined).hexdigest()


def clear_cache():
    '''
    Deletes all cached minified JS and CSS resources
    '''

    # declare tuples of (directory_path, cache_file_prefix) to delete
    cache_paths = [
        (util.make_absolute(i18n.CACHE_PATH), MODULE_JS_FILE_PREFIX),
        (util.make_absolute(os.path.join(MODULE_STATIC_CACHE_PATH, 'css')), MODULE_CSS_FILE_PREFIX)
    ]

    logger.info('clearing filechain cache')
    for cache_pair in cache_paths:
        
        try:
            files = os.listdir(cache_pair[0])
        except Exception as e:
            logger.warn('unable to list cache directory "%s": %s' % (cache_pair[0], e))
            break

        for file in files:
            if file.startswith(cache_pair[1]):
                logger.debug('deleting cached resource: %s' % file)
                try:
                    os.unlink(os.path.join(cache_pair[0], file))
                except Exception as e:
                    logger.warning('failed to delete cached resource: %s' % e)
