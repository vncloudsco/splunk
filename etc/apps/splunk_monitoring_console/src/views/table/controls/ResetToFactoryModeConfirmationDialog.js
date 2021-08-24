define([
    'jquery',
    'underscore',
    'module',
    'views/shared/Modal'
], function(
    $,
    _,
    module,
    Modal
) {
    var DMC_ALERT_PATTERN = /^DMC Alert/;
    var DMC_FORWARDER_PATTERN = /^DMC Forwarder/;
    var DMC_STANDALONE_PATTERN = /^DMC Asset - Build Standalone Asset Table$/;

    var CONFIRM_BUTTON = '<a class="btn btn-primary modal-btn-primary modal-btn-primary-confirm-reset">'+_('Reset').t()+'</a>';
    var REFRESH_BUTTON = '<a class="btn btn-primary modal-btn-primary modal-btn-primary-refresh-page" data-dismiss="modal">' + _('Refresh').t() + '</a>';

    var CONTINUE_BUTTON = '<a class="btn modal-btn-continue" data-dismiss="modal">' + _('Continue').t() + '</a>';

    return Modal.extend({
        moduleId: module.id,
        initialize: function(options) {
            options || (options = {});
            // make sure the modal doesn't accidentally close, because we want to force user click the refresh button to
            // reload the whole page after reset process is done. SPL-102221
            _.extend(options, {
                keyboard: false,
                backdrop: 'static'
            });
            Modal.prototype.initialize.call(this, options);
        },
        events: $.extend({}, Modal.prototype.events, {
            'click .modal-btn-primary-confirm-reset': '_resetToFactoryMode',
            'click .modal-btn-primary-refresh-page': function() {
                location.reload();
            }
        }),
        _resetToFactoryMode: function(e) {
            e.preventDefault();

            this.$(Modal.BODY_SELECTOR).html(this._progressBarTemplate);
            this.$(Modal.FOOTER_SELECTOR).empty();
            this.$('button.close').remove();

            var dfds = [];

            // delete all dmc_* search groups (Note that the distsearches collection may contain non-dmc groups.)
            var _dmc_groups = this.collection.peers.distsearches.filter(function(model) {
                return model.isDmcGroup();
            });
            dfds.push.apply(dfds, _.invoke(_dmc_groups, 'destroy'));

            // delete assets.csv and dmc_forwarder_assets.csv
            dfds.push.apply(_.invoke(this.collection.lookups.toArray(), 'destroy'));

            // reset app.conf is_configured = false
            this.model.appLocal.entry.content.set('configured', false);
            dfds.push(this.model.appLocal.save());

            // disable all dmc alerts and forwarder scheduled searches
            // enable [DMC Asset - Build Standalone Asset Table]
            dfds.push.apply(dfds, this.collection.savedSearches.each(function(savedSearch) {
                if (DMC_ALERT_PATTERN.test(savedSearch.entry.get('name')) || DMC_FORWARDER_PATTERN.test(savedSearch.entry.get('name'))) {
                    savedSearch.entry.content.set('disabled', true);
                }
                else if (DMC_STANDALONE_PATTERN.test(savedSearch.entry.get('name'))) {
                    savedSearch.entry.content.set('disabled', false);
                }
                return savedSearch.save();
            }));

            // delete splunk_monitoring_console_assets.conf
            var dmc_instances_with_overrides = this.collection.peers.assets.filter(function(model) {
                // since we cannot delete [settings] stanza in the conf file, we need to clear it.
                if (model.entry.get('name').toLowerCase() == 'settings') {
                    model.entry.content.set({
                        configuredPeers: '',
                        blackList: '',
                        disabled: true
                    });
                    dfds.push(model.save());
                    return false;
                }
                else {
                    return true;
                }
            });
            dfds.push(dfds, _.invoke(dmc_instances_with_overrides, 'destroy'));

            dfds.push(this.collection.thresholdConfigs.resetToDefault());

            // pretend no change was made, so that the "Apply Changes" button won't become green.
            _.defer(function() {
                this.model.state.set('changesMade', false);
            }.bind(this));

            $.when.apply($, dfds).done(function() {
                this.$(Modal.BODY_SELECTOR).find('.progress-bar').removeClass('progress-striped active').text(_('done').t());
                this.$(Modal.FOOTER_SELECTOR).append(REFRESH_BUTTON);
            }.bind(this)).fail(function() {
                this.$(Modal.BODY_SELECTOR).find('.progress-bar').removeClass('progress-striped active').text(_('error!').t());
                this.$(Modal.FOOTER_SELECTOR).append(CONTINUE_BUTTON);
            }.bind(this));
        },
        render: function() {
            this.$el.html(Modal.TEMPLATE);
            this.$(Modal.HEADER_TITLE_SELECTOR).html(_('Reset to Default Settings').t());
            this.$(Modal.BODY_SELECTOR).html(this._explanationDocTemplate);
            this.$(Modal.FOOTER_SELECTOR).append(CONFIRM_BUTTON);
            this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);

            return this;
        },
        _explanationDocTemplate: '<div class="alert alert-warning modal-txt-reset-warning-message"><i class="icon-alert" />' + _('Warning: This operation deletes and resets data and cannot be undone.').t() + '</div>' +
            '<div><p>' + _('This operation will do the following:').t() + '</p>' +
            '<ul>' +
                '<li>' + _('Delete all distributed groups created by Monitoring Console.').t() + '</li>' +
                '<li>' + _('Delete all lookup files created by Monitoring Console.').t() + '</li>' +
                '<li>' + _('Reset Monitoring Console to standalone mode.').t() + '</li>' +
                '<li>' + _('Disable all alerts in Monitoring Console.').t() + '</li>' +
                '<li>' + _('Disable forwarder monitoring.').t() + '</li>' +
                '<li>' + _('Reset all instances monitored by Monitoring Console to unconfigured state.').t() +
                '<li>' + _('Reset all thresholds to their default configuration.').t() +
            '</ul></div>' +
        '<div><p>' + _('Are you sure you want to reset to default settings?').t() + '</p>',
        _progressBarTemplate: '<div class="progress"><div class="progress-bar progress-striped active" style="width: 100%">' + _('resetting to default settings').t() + '</div></div>'
    });
});
