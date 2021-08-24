/**
 * @author claral
 * @date 4/20/16
 *
 */
define([
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'util/savedsearches/FederatedUtils'
    ],
    function (
        $,
        _,
        module,
        BaseView,
        federated_utils
    ) {

        return BaseView.extend({
            moduleId: module.id,

            events: {
                'click .new-federated-search-button': function(e) {
                    e.preventDefault();
                    this.onNewFederatedSearchButton();
                },
                'click .new-report-button': function(e) {
                    e.preventDefault();
                    this.onNewReportButton();
                },
                'click .new-alert-button': function(e) {
                    e.preventDefault();
                    this.onNewAlertButton();
                }
            },

            onNewFederatedSearchButton: function() {
                this.model.controller.trigger("newFederatedSearch");
            },

            onNewReportButton: function() {
                this.model.controller.trigger("newReport");
            },

            onNewAlertButton: function() {
                this.model.controller.trigger("newAlert");
            },

            render: function () {
                var html = this.compiledTemplate({
                    showAlertButton: this.model.user.canScheduleSearch() && this.model.user.canUseAlerts(),
                    showFederatedSearchButton: federated_utils.canCreateFederatedSearches(this.model.user, this.model.serverInfo)
                });

                this.$el.html(html);

                return this;
            },

            template:
                '<% if (showFederatedSearchButton) { %>\
                    <a href="#" class="btn new-federated-search-button"><%- _("New Federated Search").t() %></a>\
                <% } %>\
                <a href="#" class="btn new-report-button"><%- _("New Report").t() %></a>\
                <% if (showAlertButton) { %>\
                    <a href="#" class="btn new-alert-button"><%- _("New Alert").t() %></a>\
                <% } %>'
        });
    });
