/**
 * Created by cykao on 7/19/16.
 */
define([
    'underscore'
], function(
    _
) {
    var ROLE_LABELS = {
        'indexer': _('Indexer').t(),
        'license_master': _('License Master').t(),
        'search_head': _('Search Head').t(),
        'cluster_master': _('Cluster Master').t(),
        'deployment_server': _('Deployment Server').t(),
        'kv_store': _('KV Store').t(),
        'management_console': _('Monitoring Console').t(),
        'shc_deployer': _('SHC Deployer').t()
    };

    return {
        ROLE_LABELS: ROLE_LABELS
    };
});