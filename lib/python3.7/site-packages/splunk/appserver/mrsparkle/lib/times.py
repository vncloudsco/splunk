from __future__ import absolute_import
from splunk.util import cmp

import logging
import lxml.etree as et
import sys
from functools import cmp_to_key

import splunk.bundle
import splunk.util as util
from splunk.appserver.mrsparkle.lib import cached

logger = logging.getLogger('splunk.appserver.mrsparkle.lib.times')


def getTimeRanges(namespace=None):
    '''
    Returns a list of splunk search time identifiers that are defined
    in the time.conf files, ordered ascending by the 'order' key in each
    time stanza.

    Sample time.conf stanza:

        [last_7d]
        label = Last 7 Days
        earliest_time = -7d
        latest_time = false
        order = 30

        [previous2_m]
        label = Last Month
        earliest_time = -2m@m
        latest_time = -1m@m
        order = 40

    Sample return structure:

        [
            {
                'key' = 'last_7d',
                'label' = 'Last 7 Days',
                'earliest_time' = '-7d',
                'latest_time' = False,
                'order' = '30'
            },

            {
                'key' = 'previous2_m',
                'label' = 'Last Month',
                'earliest_time' = '-2m@m',
                'latest_time' = '-1m@m',
                'order' = '40'
            }
        ]

    '''

    stanzas = cached.getEntities('admin/conf-times', namespace=namespace,
                search='disabled=0', count=-1)

    # the final flat ordered array we will output.
    orderedStanzas = []

    # two dicts that we use only to check for configuration error cases.
    # if you use sub_menu = foo  in a stanza in times.conf (to place that stanza within the sub_menu with label=foo)
    # you MUST have a stanza with label=foo,  and is_sub_menu=True.
    # if you dont have this, right we just log an error at runtime.
    subMenusDefinedByChildren = {}
    subMenusPresent = {}

    for s in stanzas:
        if s == 'default':
            continue

        item = {
            'key': s,
            'label': stanzas[s].get('label', 'no label'),
            'order': int(stanzas[s].get('order', 99999))
        }

        # stanzas that are just sub_menu containers.
        # we only care so we can check for misconfigurations.
        if ('is_sub_menu' in stanzas[s] and util.normalizeBoolean(stanzas[s]['is_sub_menu'])):
            # were still outputting a flat list at the end of the day.
            # the caller will use this flag to build the hierarchy appropriately.
            item['is_sub_menu'] = True
            subMenusPresent[stanzas[s]['label']] = True

        # items that are meant to be INSIDE a submenu. If omitted it the item will go into the main menu.
        if (stanzas[s].get('sub_menu')) :
            item['sub_menu'] = stanzas[s]['sub_menu']
            subMenusDefinedByChildren[stanzas[s]['sub_menu']] = True

        # header_label is optional. If omitted it will use the 'header' as the label.
        if (stanzas[s].get('header_label')) :
            item['header_label'] = stanzas[s]['header_label']

        # only add time bounds if evaluates to something true
        for p in ('earliest_time', 'latest_time'):
            # loosening the checking to allow literal '0' values, rather than interpreting them as null.
            if ( util.normalizeBoolean(stanzas[s].get(p)) or (stanzas[s].get(p) == "0")):
                item[p] = stanzas[s][p]
            else:
                item[p] = False

        orderedStanzas.append(item)

    if (subMenusPresent.keys() != subMenusDefinedByChildren.keys()) :
        logger.error("Configuration error in times.conf.  For each sub_menu key (%s) there must be an existing stanza (%s) and vice versa." % (list(subMenusDefinedByChildren),  list(subMenusPresent)))
    
    # even though the sub_menu = <sub_menu_name> items will be 
    # sorted in alongside the main-level items, and other sub-menu items, 
    # the client code will pull out all sub_menu items and attach them to the 
    # is_sub_menu items. 
    # The thinking is that some clients (ResultsHeader.html) just want a flat list of timeranges and iterating over a tree structure would suck. 
    # other clients that need the tree (TimeRangePicker.html) will have to build it themselves using sub_menu and is_sub_menu
    
    return sorted(orderedStanzas, key=cmp_to_key(compareTimeRanges))

def compareTimeRanges(x, y):
    """
    Compare heuristic based on IM chat SPL-18830:
    Sort by order (lowest->highest)
    Sort by label (alpha)
    Sort by stanza (alpha)
    Returns -1, 0, 1
    """
    if "order" in x and "order" in y:
        return cmp(x["order"], y["order"])
    if "order" in x:
        return 1
    if "order" in y:
        return -1
    if "label" in x and "label" in y:
        return cmp(x["label"], y["label"])
    if "label" in x:
        return cmp(x["label"], y["name"])
    if "label" in y:
        return cmp(x["name"], y["label"])
    return cmp(x["name"], y["name"])


def getServerZoneinfo(sessionKey=None):
    '''
    Returns the Olsen database entries for the current server timezone.
    This table identifies the various DST boundaries for a single
    timezone.

    Sample output:

    ### SERIALIZED TIMEZONE FORMAT 1.0;Y-25200 YW 50 44 54;Y-28800 NW 50 53 54;
    Y-25200 YW 50 57 54;Y-25200 YG 50 50 54;@-1633269600 0;@-1615129200 1;
    @-1601820000 0;@-1583679600 1;@-880207200 2;@-769395600 3;@-765385200 1;
    @-687967200 0;@-662655600 1;@-620834400 0;@-608137200 1;@-589384800 0;

    ...

    @1983430800 1;@1994320800 0;@2014880400 1;@2025770400 0;@2046330000 1;
    @2057220000 0;@2077779600 1;@2088669600 0;@2109229200 1;@2120119200 0;
    @2140678800 1;$
    '''

    serverStatus, serverResp = splunk.rest.simpleRequest('/search/timeparser/tz', sessionKey=sessionKey)
    if sys.version_info >= (3, 0): serverResp = serverResp.decode()
    return serverResp


def splunktime2Iso(times, now=None):
    '''
    Returns splunk-parsed unix timestamps.  Accepts splunk relative time
    identifiers.
    '''

    getargs = {}
    getargs['time'] = times
    if now:
        getargs['now'] = now

    serverStatus, serverResp = splunk.rest.simpleRequest('/search/timeparser', getargs=getargs)

    root = et.fromstring(serverResp)

    if root.find('messages/msg'):
        raise splunk.SplunkdException(root.findtext('messages/msg'))

    output = {}
    for node in root.findall('dict/key'):
        output[node.get('name')] = node.text

    return output
