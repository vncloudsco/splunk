define(
    [
        'underscore',
        'models/SplunkDBase',
        'splunk.util'
    ],
    function(_, SplunkDBaseModel, splunkUtil) {
        return SplunkDBaseModel.extend({
            urlRoot: "cluster/master/peers/",
            url: "cluster/master/peers",
            initialize: function() {
                this.peerStatuses = {
                    Up: _('Up').t(),
                    Pending: _('Pending').t(),
                    Detention: _('Detention').t(),
                    Restarting: _('Restarting').t(),
                    ShuttingDown: _('Shutting down').t(),
                    ReassigningPrimaries: _('Reassigning primaries').t(),
                    Decommissioning: _('Decommissioning').t(),
                    GracefulShutdown: _('Graceful shutdown').t(),
                    Down: _('Down').t()
                };
                SplunkDBaseModel.prototype.initialize.apply(this, arguments);
            },
            isSearchable: function() {
                return splunkUtil.normalizeBoolean(this.entry.content.get('is_searchable'));
            },
            getTranslatedStatus: function() {
                var status = this.entry.content.get('status');
                return this.peerStatuses[status] || status;
            }
        },
        {
            // strings that match apply_bundle_status.status returned from the backend
            VALIDATED: 'ValidationDone',
            RELOADING: 'ReloadInProgress',
            CHECKING_RESTART: 'DryRunInProgress',
            NONE: 'None',
            // strings that match the peer.status from the backend.
            PEER_STATUS_UP: 'Up',
            PEER_STATUS_PENDING: 'Pending',
            PEER_STATUS_DETENTION: 'Detention',
            PEER_STATUS_RESTARTING: 'Restarting',
            PEER_STATUS_SHUTTING_DOWN: 'Shutting down',
            PEER_STATUS_REASSIGNING_PRIMARIES: 'Reassigning primaries',
            PEER_STATUS_DECOMMISSIONING: 'Decommissioning',
            PEER_STATUS_GRACEFUL_SHUTDOWN: 'Graceful shutdown',
            PEER_STATUS_DOWN: 'Down'
        });
    }
);