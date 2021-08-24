define(
    [
        'underscore',
        'module',
        'mixins/dataset',
        'views/Base',
        'views/dataset/header/Title',
        'views/shared/controls/SyntheticRadioControl',
        'views/dataset/header/TaskBar'
    ],
    function(
        _,
        module,
        datasetMixin,
        BaseView,
        Title,
        SyntheticRadioControl,
        TaskBar
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'section-header',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.children.title = new Title({
                    model: {
                        dataset: this.model.dataset
                    }
                });

                if (this.model.dataset.getType() !== 'inputlookup-table') {
                    this.children.datasetModeTabs = new SyntheticRadioControl({
                        model: this.model.dataset.entry.content,
                        modelAttribute: 'dataset.display.mode',
                        items: [
                            { label: _('View Results').t(), value: datasetMixin.MODES.TABLE },
                            { label: _('Summarize Fields').t(), value: datasetMixin.MODES.DATA_SUMMARY }
                        ],
                        additionalClassNames: 'btn-group-tabs btn-group-summary'
                    });
                }

                this.children.taskBar = new TaskBar({
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
            },

            render: function() {
                this.children.title.render().appendTo(this.$el);
                this.children.datasetModeTabs && this.children.datasetModeTabs.render().appendTo(this.$el);
                this.children.taskBar.render().appendTo(this.$el);

                return this;
            }
        });
    }
);
