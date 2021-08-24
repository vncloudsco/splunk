define([
        'jquery',
        'underscore',
        'backbone',
        'module',
        'collections/shared/FlashMessages',
        'views/shared/FlashMessagesLegacy',
        'views/shared/Modal',
        'views/shared/controls/ControlGroup',
        'util/splunkd_utils',
        'splunk.util',
        './DataRebalance.pcss'
    ],
    function(
        $,
        _,
        Backbone,
        module,
        FlashMessagesCollection,
        FlashMessagesLegacyView,
        Modal,
        ControlGroup,
        splunkdUtils,
        splunkUtils,
        css
    ) {
        return Modal.extend({
            moduleId: module.id,
            className: Modal.CLASS_NAME,

            events: {
                'click a.start-button': function(e) {
                    e.preventDefault();

                    this.flashMessages.reset();

                    this.model.clusterConfig.save({
                        rebalance_threshold: this.model.clusterConfig.entry.content.get('rebalance_threshold')
                    }, {
                        patch: true
                    })
                        .done(function() {
                            this.rebalanceAction('start')
                                .fail(function(response) {
                                    var errorText = response.responseJSON.messages[0].text;
                                    this.flashMessages.reset([{
                                        type: 'error',
                                        html: errorText
                                    }]);
                                }.bind(this));
                        }.bind(this))
                        .fail(function(response) {
                            var errorText = response.responseJSON.messages[0].text;
                            this.flashMessages.reset([{
                                type: 'error',
                                html: errorText
                            }]);
                        }.bind(this));
                },

                'click a.stop-button': function(e) {
                    e.preventDefault();
                    this.rebalanceAction('stop');
                    this.hideProgress();
                }
            },

            initialize: function(options) {
                Modal.prototype.initialize.call(this, options);

                var indexItems = this.collection.masterIndexes.map(function(model) {
                     return {
                         label: model.entry.get('name'),
                         value: model.entry.get('name')
                     };
                });

                indexItems.unshift({
                    label: _('All Indexes').t(),
                    value: null
                });

                this.rebalanceModel = new Backbone.Model();

                this.children.threshold = new ControlGroup({
                    controlType: 'Text',
                    className: 'data-rebalance-threshold control-group',
                    controlOptions: {
                        modelAttribute: 'rebalance_threshold',
                        model: this.model.clusterConfig.entry.content,
                        placeholder: _('Between 0.1 and 1').t()
                    },
                    tooltip: _('Threshold limit. If set to 0.9, data rebalancing continues ' +
                               'until the number of bucket copies on each peer is between ' +
                               '.90 and 1.10 of the average number of copies for all peers. ' +
                               'The threshold must be between 0.1 and 1.0.').t(),
                    label: _('Threshold').t()
                });

                this.children.maxRunTime = new ControlGroup({
                    controlType: 'Text',
                    className: 'data-rebalance-maxRunTime control-group',
                    controlOptions: {
                        modelAttribute: 'max_time_in_min',
                        model: this.rebalanceModel,
                        placeholder: _('optional').t()
                    },
                    tooltip: _('Maximum time, in minutes, to run data rebalancing.').t(),
                    label: _('Max Runtime').t()
                });

                this.children.index = new ControlGroup({
                    controlType: 'SyntheticSelect',
                    className: 'data-rebalance-index control-group',
                    controlOptions: {
                        modelAttribute: 'index',
                        model: this.rebalanceModel,
                        items: indexItems,
                        toggleClassName: 'btn',
                        popdownOptions: {
                            attachDialogTo: '.modal:visible',
                            scrollContainer: '.modal:visible .modal-body:visible'
                        }
                    },
                    tooltip: _('Run data rebalancing on all indexes or on a single specified index.').t(),
                    label: _('Index').t()
                });

                this.children.rebalanceType = new ControlGroup({
                    controlType: 'SyntheticCheckbox',
                    controlOptions: {
                        model: this.rebalanceModel,
                        modelAttribute: 'searchable',
                    },
                    tooltip: _('Select "searchable" to minimize search disruption during rebalance. ' +
                               'Data rebalance can take longer to complete in searchable mode.').t(),
                    label: _('Searchable').t()
                });

                this.flashMessages = new FlashMessagesCollection();
                this.children.flashMessagesLegacy = new FlashMessagesLegacyView({
                    collection: this.flashMessages
                });
            },

            render: function() {
                this.$el.html(Modal.TEMPLATE);

                this.$(Modal.HEADER_TITLE_SELECTOR).html(_('Data Rebalance').t());

                this.children.flashMessagesLegacy.render().appendTo(this.$(Modal.BODY_SELECTOR));
                this.children.threshold.render().appendTo(this.$(Modal.BODY_SELECTOR));
                this.children.maxRunTime.render().appendTo(this.$(Modal.BODY_SELECTOR));
                this.children.index.render().appendTo(this.$(Modal.BODY_SELECTOR));
                this.children.rebalanceType.render().appendTo(this.$(Modal.BODY_SELECTOR));

                this.$(Modal.BODY_SELECTOR).append(this.progressTemplate);
                this.$(Modal.BODY_SELECTOR).append(this.statusTemplate);

                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                this.$(Modal.FOOTER_SELECTOR).append(_.template(this.startButtonTemplate));
                this.$(Modal.FOOTER_SELECTOR).append(_.template(this.startingButtonTemplate));
                this.$(Modal.FOOTER_SELECTOR).append(_.template(this.stopButtonTemplate));

                this.hideProgress();
                this.pollStatus();

                return this;
            },

            pollStatus: function() {
                this.rebalanceAction('status')
                    .done(function(response) {
                        var status = parseInt(response.entry[0].content.status, 10);
                        var secondsRemaining = parseInt(response.entry[0].content.auto_stop_in_secs, 10) || null;
                        var minutesLastCompleted = parseInt(response.entry[0].content.last_completed, 10);
                        var daysLastCompleted = Math.floor(minutesLastCompleted / (60 * 24));
                        var hoursLastCompleted = Math.floor(minutesLastCompleted / 60) - (daysLastCompleted * 24);
                        var minutesRemainingLastCompleted = minutesLastCompleted - (daysLastCompleted * 24 * 60) - (hoursLastCompleted * 60);
                        var lastCompletedText = minutesLastCompleted === -1 ?
                          _('Data has never been rebalanced since cluster master restart').t() :
                          splunkUtils.sprintf(_('Data was last rebalanced %d days and %d hours and %d minutes ago').t(), daysLastCompleted, hoursLastCompleted, minutesRemainingLastCompleted);

                        if (status === -1) {
                            this.hideProgress();
                            this.$('.data-rebalance-status').text(lastCompletedText);
                            this.$('.start-button').show();
                            this.$('.starting-button').hide();
                            this.$('.stop-button').hide();
                        } else if (status === 0) {
                            this.showProgress(status, secondsRemaining);
                            this.$('.data-rebalance-status').text(_('Data rebalance is preparing to start').t());
                            this.$('.start-button').hide();
                            this.$('.starting-button').show();
                            this.$('.stop-button').hide();
                        } else if (status > 0) {
                            this.showProgress(status, secondsRemaining);
                            this.$('.start-button').hide();
                            this.$('.starting-button').hide();
                            this.$('.stop-button').show();
                        } else {
                            this.hideProgress();
                            this.$('.data-rebalance-status').text(_('Data rebalance has an invalid status').t());
                            this.$('.start-button').hide();
                            this.$('.starting-button').hide();
                            this.$('.stop-button').hide();
                        }

                        setTimeout(this.pollStatus.bind(this), 1000);
                    }.bind(this));
            },

            rebalanceAction: function(action) {
                var data = {
                    action: action,
                    output_mode: 'json'
                };

                if (action === 'start') {
                    if (this.rebalanceModel.has('max_time_in_min')) {
                        data.max_time_in_min = this.rebalanceModel.get('max_time_in_min');
                    }
                    if (this.rebalanceModel.has('index')) {
                        data.index = this.rebalanceModel.get('index');
                    }
                    if (this.rebalanceModel.has('searchable')) {
                        data.searchable = this.rebalanceModel.get('searchable');
                    }
                }

                return $.ajax({
                    url: splunkdUtils.fullpath('cluster/master/control/control/rebalance_buckets'),
                    type: 'POST',
                    contentType: "application/json",
                    data: data
                });
            },

            showProgress: function(percentComplete, secondsRemaining) {
                var hoursLeft = Math.floor(secondsRemaining / (60 * 60));
                var minutesLeft = Math.floor(secondsRemaining / 60) - (hoursLeft * 60);
                var secondsLeft = secondsRemaining - (hoursLeft * 60 * 60) - (minutesLeft * 60);
                var timeLeftText = splunkUtils.sprintf(_('Data rebalance will autostop in %d:%d:%d').t(), hoursLeft, minutesLeft, secondsLeft);

                this.children.threshold.disable();
                this.children.maxRunTime.disable();
                this.children.index.disable();
                this.children.rebalanceType.disable();

                this.$('.progress').show();
                this.$('.progress-bar').css('width', percentComplete * 4.1);
                this.$('.data-rebalance-status').text(secondsRemaining ? timeLeftText : '');
                this.$('.sr-only').text(percentComplete + "%");
            },

            hideProgress: function() {
                this.children.threshold.enable();
                this.children.maxRunTime.enable();
                this.children.index.enable();
                this.children.rebalanceType.enable();

                this.$('.progress').hide();
                this.$('.progress-bar').css('width', 0);
                this.$('.sr-only').text('0%');
            },

            startButtonTemplate: '<a href="#" class="btn btn-primary pull-right start-button"> <%= _("Start").t() %> </a>',

            startingButtonTemplate: '<a href="#" class="btn btn-primary pull-right starting-button disabled"> <%= _("Starting ...").t() %> </a>',

            stopButtonTemplate: '<a href="#" class="btn pull-right stop-button"> <%= _("Stop").t() %> </a>',

            statusTemplate: '\
                <div class="data-rebalance-text">\
                    <span class="data-rebalance-status"></span>\
                </div>',

            progressTemplate: '\
                <div class="progress" style="display: block;">\
                    <div class="progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" style="width:0%;">\
                        <span class="sr-only">0%</span>\
                    </div>\
                </div>'
        });
    });
