/**
 * Created by ykou on 2/25/15.
 */
define([
    'jquery',
    'underscore',
    'module',
    'backbone',
    'splunkjs/mvc/searchmanager',
    'views/shared/Modal',
    'views/shared/controls/ControlGroup',
    'contrib/text!splunk_monitoring_console/views/settings/forwarder_setup/enterprise/RebuildAssetsDialog.html'
], function(
    $,
    _,
    module,
    Backbone,
    SearchManager,
    Modal,
    ControlGroup,
    Template
) {
    var MESSAGES = {
        PROGRESS: _('in progress').t(),
        CANCEL: _('cancelled').t(),
        DONE: _('done').t(),
        ERROR: _('error').t(),
        FAILED: _('failed').t(),
        START: _('start').t()
    };

    var SPARKLINE_SPAN = {
        '-15m@m': '1m',
        '-30m@m': '1m',
        '-1h@m': '2m',
        '-4h@m': '8m',
        '-8h@m': '16m',
        '-12h@m': '24m',
        '-1d@m': '48m'
    };

    var CONTINUE_BUTTON = '<a href="#" class="btn btn-primary modal-btn-primary confirm-rebuild-button">'+_('Start Rebuild').t()+'</a>';

    return Modal.extend({
        moduleId: module.id,
        initialize: function() {
            //this.options.onHiddenRemove = true;  // set to true because we always want to destroy the search manager inside
            Modal.prototype.initialize.apply(this, arguments);

            // use this to track the state of this dialog.
            // we need this because user my open this window multiple times,
            // we want to reset this window when the search is done AND user re-opens this window.
            this._rebuildIsDone = false;

            this._timeRangeModel = new Backbone.Model({
                earliest: '-1d@m',
                latest: 'now'
            });

            this.compiledProgressBar = _.template(this._progressBarTemplate);
        },
        events: $.extend({}, Modal.prototype.events, {
            'click .confirm-rebuild-button': function(e) {
                e.preventDefault();
                this._runRebuildSearch();
            },
            'click .do-it-again-button': function(e) {
                e.preventDefault();
                this.render();
            }
        }),
        _runRebuildSearch: function() {
            if (!this._rebuildForwarderAssetsSearch) {
                this._rebuildForwarderAssetsSearch = new SearchManager({
                    'earliest_time': this._timeRangeModel.get('earliest'),
                    'latest_time': this._timeRangeModel.get('latest'),
                    'search': this._getSearchString()
                });
                this._rebuildForwarderAssetsSearch.on({
                    'search:cancelled': function() {
                        this._updateSearchStatus(MESSAGES.CANCEL);
                    },
                    'search:done': function() {
                        this._updateSearchStatus(MESSAGES.DONE);
                    },
                    'search:error': function() {
                        this._updateSearchStatus(MESSAGES.ERROR);
                    },
                    'search:failed': function() {
                        this._updateSearchStatus(MESSAGES.FAILED);
                    },
                    'search:progress': function() {
                        this._updateSearchStatus(MESSAGES.PROGRESS);
                    },
                    'search:start': function() {
                        this._updateSearchStatus(MESSAGES.START);
                    }
                }, this);
            } else {
                this._rebuildForwarderAssetsSearch.startSearch();
            }
        },
        _updateSearchStatus: function(message) {
            var $progressBar = this.$(Modal.BODY_SELECTOR).find('.progress-bar');
            if ($progressBar.length <= 0) {  // no progress bar
                this.$(Modal.BODY_SELECTOR).html(this.compiledProgressBar({
                    message: message
                }));
            }
            else {
                $progressBar.html(message);
            }
            this.$(Modal.FOOTER_SELECTOR).empty();
            if (_.contains([MESSAGES.CANCEL, MESSAGES.DONE, MESSAGES.ERROR, MESSAGES.FAILED], message)) {
                $progressBar.removeClass('progress-striped active');
                this.$(Modal.FOOTER_SELECTOR).html(Modal.BUTTON_DONE);
                this.$(Modal.FOOTER_SELECTOR).find('.btn-primary').focus();
                this._rebuildIsDone = true;
            }
        },
        show: function() {
            if (this._rebuildIsDone) {
                this.render();
            }
            Modal.prototype.show.apply(this, arguments);
        },
        _getSearchString: function() {
            var span = SPARKLINE_SPAN[this._timeRangeModel.get('earliest')];
            if (!span) { throw Error('cannot find right span for `dmc_re_build_forwarder_assets(1)`'); }
            return '`dmc_re_build_forwarder_assets(' + span + ')`';
        },
        render: function() {
            this.$el.html(Modal.TEMPLATE);
            this.$(Modal.HEADER_TITLE_SELECTOR).html(_("Rebuild Forwarder Assets").t());
            this.$(Modal.BODY_SELECTOR).html(this.compiledTemplate());

            this.children.timeRangePicker = new ControlGroup({
                label: _('Time Range:').t(),
                controlType: 'SyntheticSelect',
                controlOptions: {
                    model: this._timeRangeModel,
                    modelAttribute: 'earliest',
                    items: [    // please make sure SPARKLINE_SPAN synchronized with this.
                        {label: _('Last 15 minutes').t(), value: '-15m@m'},
                        {label: _('Last 30 minutes').t(), value: '-30m@m'},
                        {label: _('Last 1 hour').t(), value: '-1h@m'},
                        {label: _('Last 4 hours').t(), value: '-4h@m'},
                        {label: _('Last 8 hours').t(), value: '-8h@m'},
                        {label: _('Last 12 hours').t(), value: '-12h@m'},
                        {label: _('Last 24 hours').t(), value: '-1d@m'}
                    ],
                    menuWidth: 'narrow',
                    toggleClassName: 'btn',
                    popdownOptions: {detachDialog: true}
                },
                help: _('Splunk Enterprise uses logs in this time range to discover forwarders.').t()
            });
            this.$(".form-rebuild-time-range-picker").append(this.children.timeRangePicker.render().$el);

            this.$(Modal.FOOTER_SELECTOR).append(CONTINUE_BUTTON);
            this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);

            return this;
        },
        template: Template,
        _progressBarTemplate: '<div class="progress"><div class="progress-bar progress-striped active" style="width: 100%"><%= message %></div></div>'
   });
});
