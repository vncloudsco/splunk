define(
    [
        'underscore',
        'jquery',
        'module',
        'views/Base',
        'views/shared/FlashMessages',
        'views/dataset/header/Master',
        'views/shared/timerangepicker/Master',
        'views/shared/jobstatus/Master',
        'views/dataset/tablecontainer/Master',
        'util/splunkd_utils',
        './Master.pcss'
    ],
    function(
        _,
        $,
        module,
        BaseView,
        FlashMessages,
        HeaderView,
        TimeRangePicker,
        JobStatus,
        TableContainerView,
        splunkdUtils,
        css
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'explorer-page',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.errorTypes = [splunkdUtils.FATAL, splunkdUtils.ERROR];

                this.children.flashMessages = new FlashMessages({
                    className: 'dataset-flash-messages',
                    model: {
                        dataset: this.model.dataset
                    },
                    whitelist: this.errorTypes
                });

                this.children.header = new HeaderView({
                    model: {
                        application: this.model.application,
                        appLocal: this.model.appLocal,
                        dataset: this.model.dataset,
                        searchJob: this.model.searchJob,
                        serverInfo: this.model.serverInfo,
                        timeRange: this.model.timeRange,
                        user: this.model.user
                    },
                    collection: {
                        apps: this.collection.apps,
                        roles: this.collection.roles
                    }
                });

                this.children.timeRangePicker = new TimeRangePicker({
                    model: {
                        application: this.model.application,
                        state: this.model.dataset.entry.content,
                        timeRange: this.model.timeRange,
                        user: this.model.user
                    },
                    collection: this.collection.times,
                    className: 'controls',
                    timerangeClassName: 'btn btn-primary pull-left',
                    dialogOptions: {
                        showPresetsRealTime: false,
                        showCustomRealTime: false,
                        enableCustomAdvancedRealTime: false
                    }
                });

                this.children.tableContainer = new TableContainerView({
                    model: {
                        application: this.model.application,
                        appLocal: this.model.appLocal,
                        config: this.model.config,
                        dataset: this.model.dataset,
                        result: this.model.result,
                        resultJsonRows: this.model.resultJsonRows,
                        searchJob: this.model.searchJob,
                        serverInfo: this.model.serverInfo,
                        state: this.model.state,
                        timeRange: this.model.timeRange,
                        user: this.model.user,
                        ast: this.model.ast
                    },
                    flashMessagesHelper: this.children.flashMessages.flashMsgHelper
                });

                // We have to do this because some shared components (cough time range picker cough) activate in
                // initialize, and we don't want router changes to trigger events before actual activation kicks in.
                _.each(this.children, function(child) {
                    child.deactivate({ deep: true });
                });
            },

            activate: function(options) {
                if (this.active) {
                    return BaseView.prototype.activate.apply(this, arguments);
                }

                var clonedOptions = _.extend({}, (options || {}));
                delete clonedOptions.deep;

                if (!this.children.jobStatus) {
                    this.initializeJobStatus();
                }

                this.children.jobStatus.options.showControlsAndJobInfo = this.model.searchJob.id;
                if (this.$el.html() && !this.children.jobStatus.$el.html()) {
                    this.children.jobStatus.activate({ deep: true }).render().appendTo(this.$('.job-status-container'));
                } else {
                    this.children.jobStatus.activate({ deep: true });
                }

                this.triggerError();
                this.manageStateOfChildren();

                return BaseView.prototype.activate.call(this, clonedOptions);
            },

            deactivate: function(options) {
                if (!this.active) {
                    return BaseView.prototype.deactivate.apply(this, arguments);
                }

                BaseView.prototype.deactivate.apply(this, arguments);

                this.children.jobStatus.remove();
                delete this.children.jobStatus;

                this.isError = false;

                return this;
            },

            initializeJobStatus: function() {
                this.children.jobStatus = new JobStatus({
                    model: {
                        application: this.model.application,
                        appLocal: this.model.appLocal,
                        state: this.model.dataset.entry.content,
                        searchJob: this.model.searchJob,
                        // deliberately leaving report out so PDF export isn't possible
                        serverInfo: this.model.serverInfo,
                        user: this.model.user
                    },
                    enableReload: true,
                    enableSearchMode: false,
                    allowDelete: false,
                    hidePrintButton: true,
                    allowRawEventsExport: false,
                    // While it's true that lookup files will return an empty array for fields,
                    // exporting with no fields list will actually do the right thing for lookup files.
                    fields: _.pluck(this.model.dataset.getFields(), 'name')
                });
                this.children.jobStatus.deactivate({ deep: true });
            },

            manageStateOfChildren: function() {
                if (this.isError) {
                    this.children.flashMessages.activate({ deep: true }).$el.css('display', '');
                    this.children.header.deactivate({ deep: true }).$el.hide();
                    this.children.timeRangePicker.deactivate({ deep: true }).$el.hide();
                    this.children.tableContainer.deactivate({ deep: true }).$el.hide();
                } else {
                    this.children.flashMessages.deactivate({ deep: true }).$el.hide();
                    this.children.header.activate({ deep: true }).$el.css('display', '');
                    this.children.timeRangePicker.activate({ deep: true }).$el.css('display', '');
                    this.children.tableContainer.activate({ deep: true }).$el.css('display', '');
                }
            },

            triggerError: function() {
                var didTriggerError = false;

                this.isError = splunkdUtils.messagesContainsOneOfTypes(this.model.dataset.error.get('messages'), this.errorTypes);

                if (this.model.dataset.isNew() && !this.isError) {
                    var noDatasetIdError = splunkdUtils.createSplunkDMessage(
                        splunkdUtils.FATAL,
                        _('No dataset was specified.').t()
                    );
                    this.model.dataset.trigger('error', this.model.dataset, noDatasetIdError);
                    this.isError = true;
                    didTriggerError = true;
                }

                return didTriggerError;
            },

            render: function() {
                var html = this.$el.html();
                if (!html) {
                    this.children.flashMessages.render().appendTo(this.$el);
                    this.children.header.render().appendTo(this.$el);
                    this.children.timeRangePicker.render().appendTo(this.$el);

                    this.$el.append(this.template);
                    if (this.children.jobStatus) {
                        this.children.jobStatus.render().appendTo(this.$('.job-status-container'));
                    }

                    this.children.tableContainer.render().appendTo(this.$el);
                }
                return this;
            },

            template: '\
                <div class="job-status-container"></div>\
            '
        });
    }
);
