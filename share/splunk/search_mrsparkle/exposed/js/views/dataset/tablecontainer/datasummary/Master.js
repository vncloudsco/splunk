define(
    [
        'underscore',
        'jquery',
        'module',
        'models/datasets/DataSummarySearchJob',
        'models/datasets/DataSummaryResultJsonRows',
        'models/datasets/DataSummarySummary',
        'models/services/search/jobs/Timeline',
        'models/shared/fetchdata/ResultsFetchData',
        'views/Base',
        'views/shared/FlashMessages',
        'views/shared/summarytable/Master',
        'views/dataset/tablecontainer/datasummary/StatusBar',
        'util/splunkd_utils'
    ],
    function(
        _,
        $,
        module,
        DataSummarySearchJobModel,
        DataSummaryResultJsonRowsModel,
        DataSummarySummaryModel,
        TimelineModel,
        ResultsFetchDataModel,
        BaseView,
        FlashMessages,
        DataSummaryTable,
        DataSummaryStatusBar,
        splunkdUtils
    ) {
        return BaseView.extend({
            moduleId: module.id,

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.model.dataSummaryJob = new DataSummarySearchJobModel({}, {
                    delay: DataSummarySearchJobModel.DEFAULT_POLLING_INTERVAL,
                    processKeepAlive: true,
                    keepAliveInterval: DataSummarySearchJobModel.DEFAULT_LONG_POLLING_INTERVAL
                });
                this.model.dataSummarySummary = new DataSummarySummaryModel();
                this.model.dataSummaryTimeline = new TimelineModel();
                this.model.dataSummaryResultJsonRows = new DataSummaryResultJsonRowsModel();

                this.errorTypes = [splunkdUtils.FATAL, splunkdUtils.ERROR];

                this.children.flashMessages = new FlashMessages({
                    model: {
                        ast: this.model.ast
                    },
                    whitelist: this.errorTypes
                });

                this.children.dataSummaryStatusBar = new DataSummaryStatusBar({
                    model: {
                        application: this.model.application,
                        dataSummaryJob: this.model.dataSummaryJob
                    }
                });

                this.children.dataSummaryTable = new DataSummaryTable({
                    model: {
                        ast: this.model.ast,
                        config: this.model.config,
                        dataset: this.model.dataset,
                        dataSummaryJob: this.model.dataSummaryJob,
                        resultJsonRows: this.model.dataSummaryResultJsonRows,
                        state: this.model.state,
                        summary: this.model.dataSummarySummary,
                        timeline: this.model.dataSummaryTimeline
                    },
                    useDock: true,
                    editingMode: false
                });
            },

            activate: function(options) {
                var clonedOptions = _.extend({}, (options || {}));
                delete clonedOptions.deep;

                if (this.active) {
                    return BaseView.prototype.activate.call(this, clonedOptions);
                }

                this.startDataSummaryJob();
                this.manageStateOfChildren();

                return BaseView.prototype.activate.call(this, clonedOptions);
            },

            deactivate: function(options) {
                var clonedOptions = _.extend({}, (options || {}));
                delete clonedOptions.deep;

                if (!this.active) {
                    return BaseView.prototype.deactivate.call(this, clonedOptions);
                }

                BaseView.prototype.deactivate.call(this, clonedOptions);

                this.model.dataSummaryJob.off(null, null, this);
                this.clearModels();

                return this;
            },

            startListening: function() {
                this.listenTo(this.model.dataSummaryResultJsonRows, 'change', this.manageStateOfChildren);
                this.listenTo(this.model.dataSummaryJob, 'restart', this.startDataSummaryJob);
            },

            startDataSummaryJob: function() {
                var search;

                $.when(this.clearModels()).then(function() {
                    search = this.model.dataSummaryJob.appendStatsToSearch(this.model.dataset.getFromSearch(), {
                        columns: this.model.dataset.getTypedFields()
                    });

                    this.model.dataSummaryJob.save({}, {
                        data: {
                            search: search,
                            earliest_time: this.model.searchJob.getWindowedEarliestTimeOrAllTime(),
                            latest_time: this.model.searchJob.getWindowedLatestTimeOrAllTime(),
                            adhoc_search_level: 'verbose',
                            preview: true,
                            status_buckets: 300,
                            app: this.model.application.get('app'),
                            ui_dispatch_app: this.model.application.get('app'),
                            owner: this.model.application.get('owner'),
                            auto_cancel: DataSummarySearchJobModel.DEFAULT_AUTO_CANCEL,
                            provenance: 'UI:Dataset'
                        },

                        success: function(model, response) {
                            if (!this.model.dataSummaryJob.isPreparing()) {
                                this.registerDataSummaryJobFriends();
                            } else {
                                this.listenToOnce(this.model.dataSummaryJob, 'prepared', function() {
                                    this.registerDataSummaryJobFriends();
                                }.bind(this));
                            }

                            this.model.dataSummaryJob.startPolling();
                        }.bind(this)
                    });
                }.bind(this));
            },

            registerDataSummaryJobFriends: function(options) {
                this.model.dataSummaryJob.registerJobProgressLinksChild(DataSummarySearchJobModel.SUMMARY, this.model.dataSummarySummary, this.fetchDataSummarySummary, this);
                this.model.dataSummaryJob.registerJobProgressLinksChild(DataSummarySearchJobModel.TIMELINE, this.model.dataSummaryTimeline, this.fetchDataSummaryTimeline, this);
                this.model.dataSummaryJob.registerJobProgressLinksChild(DataSummarySearchJobModel.RESULTS_PREVIEW, this.model.dataSummaryResultJsonRows, this.fetchDataSummaryResultJSONRows, this);
            },

            fetchDataSummarySummary: function() {
                this.model.dataSummarySummary.safeFetch({
                    data: {
                        min_freq: 0,
                        top_count: 100 // Get top 100 values for Data Summary top results list
                    }
                });
            },

            fetchDataSummaryTimeline: function() {
                this.model.dataSummaryTimeline.safeFetch();
            },

            fetchDataSummaryResultJSONRows: function(options) {
                options = options || {};

                if (this.model.dataSummaryJob.entry.content.get('isPreviewEnabled') || this.model.dataSummaryJob.isDone()) {
                    var fetchDataModel = new ResultsFetchDataModel();

                    var data = $.extend(
                        fetchDataModel.toJSON(),
                        {
                            time_format: '%s.%Q'
                        }
                    );

                    $.extend(true, data, options);

                    this.model.dataSummaryResultJsonRows.safeFetch({
                        data: data
                    });
                }
            },

            clearModels: function() {
                var deferred = $.Deferred();

                if (!this.model.dataSummaryJob.isNew()) {
                    this.model.dataSummaryJob.fetchAbort();

                    $.when(this.model.dataSummaryJob.destroy()).always(function() {
                        this.model.dataSummaryJob.clear();
                        deferred.resolve();
                    }.bind(this));
                } else {
                    deferred.resolve();
                }

                this.model.dataSummarySummary.fetchAbort();
                this.model.dataSummarySummary.clear();
                this.model.dataSummaryTimeline.fetchAbort();
                this.model.dataSummaryTimeline.clear();
                this.model.dataSummaryResultJsonRows.fetchAbort();
                this.model.dataSummaryResultJsonRows.clear();

                return deferred;
            },

            manageStateOfChildren: function() {
                var isError = splunkdUtils.messagesContainsOneOfTypes(this.model.ast.error.get('messages'), this.errorTypes);

                if (isError) {
                    this.children.flashMessages.activate({ deep: true }).$el.show();
                    this.children.dataSummaryStatusBar.deactivate({ deep: true }).$el.hide();
                    this.children.dataSummaryTable.deactivate({ deep: true }).$el.hide();
                } else {
                    this.children.flashMessages.deactivate({ deep: true }).$el.hide();
                    this.children.dataSummaryStatusBar.activate({ deep: true }).$el.css('display', '');
                    this.children.dataSummaryTable.activate({ deep: true }).$el.css('display', '');
                }
            },

            render: function() {
                this.children.flashMessages.render().appendTo(this.$el);
                this.children.dataSummaryStatusBar.render().appendTo(this.$el);
                this.children.dataSummaryTable.render().appendTo(this.$el);

                this.manageStateOfChildren();

                return this;
            }
        });
    }
);
