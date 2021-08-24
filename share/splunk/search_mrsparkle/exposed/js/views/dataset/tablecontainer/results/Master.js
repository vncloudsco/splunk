define(
    [
        'underscore',
        'jquery',
        'module',
        'models/search/Job',
        'views/Base',
        'views/shared/FlashMessages',
        'views/dataset/tablecontainer/results/DatasetControls',
        'views/shared/JobDispatchState',
        'views/shared/datasettable/Master',
        'util/splunkd_utils'
    ],
    function(
        _,
        $,
        module,
        SearchJobModel,
        BaseView,
        FlashMessages,
        DatasetControls,
        JobDispatchState,
        TableView,
        splunkdUtils
    ) {
        return BaseView.extend({
            moduleId: module.id,

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.errorTypes = [splunkdUtils.FATAL, splunkdUtils.ERROR];

                this.children.flashMessages = new FlashMessages({
                    model: {
                        ast: this.model.ast
                    },
                    whitelist: this.errorTypes
                });

                this.children.datasetControls = new DatasetControls({
                    model: {
                        dataset: this.model.dataset,
                        searchJob: this.model.searchJob,
                        state: this.model.state
                    }
                });

                this.children.table = new TableView({
                    model: {
                        config: this.model.config,
                        dataset: this.model.dataset,
                        resultJsonRows: this.model.resultJsonRows,
                        state: this.model.state
                    },
                    editingMode: false,
                    useDock: true
                });
            },

            startListening: function() {
                this.listenTo(this.model.resultJsonRows, 'change', this.manageStateOfChildren);
            },

            activate: function(options) {
                var clonedOptions = _.extend({}, (options || {}));
                delete clonedOptions.deep;

                if (this.active) {
                    return BaseView.prototype.activate.call(this, clonedOptions);
                }

                return BaseView.prototype.activate.call(this, clonedOptions);
            },

            deactivate: function(options) {
                var clonedOptions = _.extend({}, (options || {}));
                delete clonedOptions.deep;

                if (!this.active) {
                    return BaseView.prototype.deactivate.call(this, clonedOptions);
                }

                BaseView.prototype.deactivate.call(this, clonedOptions);

                return this;
            },

            manageStateOfChildren: function() {
                var isError = splunkdUtils.messagesContainsOneOfTypes(this.model.ast.error.get('messages'), this.errorTypes),
                    jobDispatchStateMsgs = {};

                if (isError) {
                    this.children.flashMessages.activate({ deep: true }).$el.show();
                    this.children.datasetControls.deactivate({ deep: true }).$el.hide();
                    this.children.table.deactivate({ deep: true }).$el.hide();
                    this.children.jobDispatchState && this.children.jobDispatchState.deactivate({ deep: true }).$el.hide();
                } else {
                    this.children.flashMessages.deactivate({ deep: true }).$el.hide();
                    this.children.datasetControls.activate({ deep: true }).$el.css('display', '');
                    this.children.table.activate({ deep: true }).$el.css('display', '');

                    // Job Dispatch State must be removed and reinitialized every time on activate
                    if (this.children.jobDispatchState) {
                        this.children.jobDispatchState.deactivate({ deep: true }).remove();
                        delete this.children.jobDispatchState;
                    }

                    jobDispatchStateMsgs[SearchJobModel.DONE] = {
                        msg: this.getDoneJobMessage.bind(this)
                    };

                    if (!this.model.resultJsonRows.hasRows()) {
                        this.children.jobDispatchState = new JobDispatchState({
                            model: {
                                application: this.model.application,
                                searchJob: this.model.searchJob
                            },
                            mode: this.model.ast.isTransforming() ? 'results' : '',
                            jobDispatchStateMsgs: jobDispatchStateMsgs
                        });
                        // If the view has already been rendered, then render and append. Otherwise, allow render() to do it.
                        if (this.$el.html()) {
                            this.children.jobDispatchState.activate({ deep: true }).render().appendTo(this.$el);
                        }
                    }
                }
            },

            getDoneJobMessage: function() {
                var transformingCondition = this.model.ast.isTransforming() ?
                        (this.model.searchJob.entry.content.get('eventCount') > 0) :
                        this.model.searchJob.isUneventfulReportSearch();

                if (this.model.searchJob.isOverAllTime() || transformingCondition) {
                    return _('No results found.').t();
                } else {
                    return _('No results found. Try expanding the time range.').t();
                }
            },

            render: function() {
                this.children.flashMessages.render().appendTo(this.$el);
                this.children.datasetControls.render().appendTo(this.$el);
                this.children.table.render().appendTo(this.$el);
                if (this.children.jobDispatchState) {
                    this.children.jobDispatchState.activate({ deep: true }).render().appendTo(this.$el);
                }

                this.manageStateOfChildren();

                return this;
            }
        });
    }
);
