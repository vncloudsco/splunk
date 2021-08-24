'''
Migrates the Google Maps app from 4.1 -> 4.2
See: http://splunkbase.splunk.com/apps/All/4.x/Add-On/app:Google+Maps
'''
from __future__ import print_function

from builtins import object
import logging
import os
import re
import shutil
import time
from splunk.clilib import bundle_paths

logger = logging.getLogger()


def _move_module_images(app_path, dryRun=False):
    logger.info('Migrating module images...')
    path = os.path.join(app_path, 'appserver', 'modules', 'GoogleMaps', 'img')
    if not os.path.isdir(path):
        logger.warn('Module images not found; possibly migrated already')
        return

    dest = os.path.join(app_path, 'appserver', 'static', 'img')

    if not dryRun:
        return shutil.move(path, dest)


def _update_css_image_paths(app_path, dryRun=False):
    logger.info('Migrating CSS image path references...')
    filepath = os.path.join(app_path, 'appserver', 'modules', 'GoogleMaps', 'GoogleMaps.css')

    if not os.access(filepath, os.W_OK):
        logger.error('Could not obtain write access to GoogleMaps.css; %s' % filepath)
        return

    new_file = []
    rex1 = re.compile(r'url\(img/')
    rex2 = re.compile(r'src="img/')

    in_file = open(filepath, 'r')
    try:
        for line in in_file:
            line = rex1.sub('url(/static/app/maps/img/', line)
            line = rex2.sub('src="/static/app/maps/img/', line)
            new_file.append(line)
    finally:
        if in_file:
            in_file.close()

    if not dryRun:
        shutil.copyfile(filepath, filepath + '.' + str(int(time.time())))

        out_file = open(filepath, 'w')
        try:
            out_file.writelines(new_file)
        finally:
            if out_file:
                out_file.close()


def migrate_maps_41x_420(dryRun=False):
    
    bundle_object = bundle_paths.get_bundle('maps')
    if not bundle_object:
        return

    logger.info('Google Maps app found in: %s' % bundle_object.location())

    _move_module_images(bundle_object.location(), dryRun)
    _update_css_image_paths(bundle_object.location(), dryRun)

    logger.info('Done migrating Google Maps app')


if __name__ == '__main__':

    class lg(object):
        def info(self, m):
            print(m)
        warn = info
        error = info
    logger = lg()

    migrate_maps_41x_420()

