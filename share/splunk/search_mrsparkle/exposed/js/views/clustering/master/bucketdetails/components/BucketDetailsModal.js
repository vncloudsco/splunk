define([
        'jquery',
        'backbone',
        'underscore',
        'module',
        'views/shared/Modal',
        'util/splunkd_utils',
        'splunk.util'
    ],
    function(
        $,
        backbone,
        _,
        module,
        Modal,
        splunkdUtils,
        splunkUtils
    ) {
        return Modal.extend({
            moduleId: module.id,
            className: Modal.CLASS_NAME,

            initialize: function(options) {
                Modal.prototype.initialize.apply(this, arguments);

                this.bucketId = this.options.bucketId;
                var data = {
                    output_mode: 'json'
                };

                $.ajax({
                    url: splunkdUtils.fullpath('cluster/master/buckets/' + this.bucketId),
                    type: 'GET',
                    contentType: 'application/json',
                    data: data
                }).done(function(response) {
                    var responseContent = response.entry[0].content;

                    var peers = !responseContent.peers ? [] :
                      _.map(responseContent.peers, function(peer) {
                            return {
                              instanceName: peer.server_name ? peer.server_name : _("N/A").t(),
                              bucketFlags: peer.bucket_flags ? peer.bucket_flags : _("N/A").t(),
                              bucketSizeVote: peer.bucket_size_vote ? peer.bucket_size_vote : _("N/A").t(),
                              status: peer.status ? peer.status : _("N/A").t(),
                              searchState: peer.search_state ? peer.search_state : _("N/A").t()
                            };
                      });

                    var bucketDetails = {
                      bucketSize: responseContent.bucket_size ? responseContent.bucket_size : _("Unreported. Bucket might be hot.").t(),
                      forceRoll: responseContent.force_roll ? responseContent.force_roll : _("N/A").t(),
                      frozen: responseContent.frozen ? responseContent.frozen === 1 : _("N/A").t(),
                      index: responseContent.index ? responseContent.index : _("N/A").t(),
                      originSite: responseContent.origin_site ? responseContent.origin_site : _("N/A").t(),
                      standalone: responseContent.standalone ? responseContent.standalone === 1 : _("N/A").t(),
                      peers: peers,
                      repCountBySite: responseContent.rep_count_by_site ? responseContent.rep_count_by_site : [],
                      searchCountBySite: responseContent.search_count_by_site ? responseContent.search_count_by_site : []
                    };

                    this.$(Modal.BODY_SELECTOR).append(_.template(this.detailsTemplate, bucketDetails));
                }.bind(this));
            },

            render: function() {
                this.$el.html(Modal.TEMPLATE);
                this.$(Modal.HEADER_TITLE_SELECTOR).html(_('Bucket:  ').t() + this.bucketId);
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CLOSE);

                return this;
            },

            detailsTemplate: '\
                <div>\
                    <h4> <%= _("Bucket Details").t() %> </h4>\
                    <div> <%= _("Bucket Size: ").t() %> <%= bucketSize %> </div>\
                    <div> <%= _("Force Roll: ").t() %> <%= forceRoll %> </div>\
                    <div> <%= _("Frozen: ").t() %> <%= frozen %> </div>\
                    <div> <%= _("Index: ").t() %> <%= index %> </div>\
                    <div> <%= _("Origin Site: ").t() %> <%= originSite %> </div>\
                    <div> <%= _("Standalone: ").t() %> <%= standalone %> </div>\
                    <h4> <%= _("Peers").t() %> </h4>\
                    <% _.each(peers, function(peer) { %> \
                            <div>\
                                <div> <%= _("Instance Name: ").t() %> <%= peer.instanceName %> </div>\
                                <div> <%= _("Bucket Flags: ").t() %> <%= peer.bucketFlags %> </div>\
                                <div> <%= _("Bucket Size Vote: ").t() %> <%= peer.bucketSizeVote %> </div>\
                                <div> <%= _("Status: ").t() %> <%= peer.status %> </div>\
                                <div> <%= _("Search State: ").t() %> <%= peer.searchState %> </div>\
                                <br/>\
                            </div>\
                    <% }) %>\
                    <h4> <%= _("Replication Count by Site").t() %> </h4>\
                    <% _.each(repCountBySite, function(value, key) { %> \
                        <div> <%= key + ": " + value %> </div>\
                    <% }) %>\
                    <h4> <%= _("Search Count by Site").t() %> </h4>\
                    <% _.each(searchCountBySite, function(value, key) { %> \
                        <div> <%= key + ": " + value %> </div>\
                    <% }) %>\
                </div>\
            '
        });
    });
