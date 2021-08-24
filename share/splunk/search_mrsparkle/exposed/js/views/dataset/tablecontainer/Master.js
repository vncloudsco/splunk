define(
    [
        'underscore',
        'jquery',
        'module',
        'mixins/dataset',
        'views/Base',
        'views/dataset/tablecontainer/results/Master',
        'views/dataset/tablecontainer/datasummary/Master',
        './Master.pcss'
    ],
    function(
        _,
        $,
        module,
        datasetMixin,
        BaseView,
        ResultsView,
        DataSummaryView,
        css
    ) {
        return BaseView.extend({
            moduleId: module.id,

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.children.resultsView = new ResultsView({
                    model: {
                        application: this.model.application,
                        ast: this.model.ast,
                        config: this.model.config,
                        dataset: this.model.dataset,
                        resultJsonRows: this.model.resultJsonRows,
                        searchJob: this.model.searchJob,
                        state: this.model.state
                    }
                });

                this.children.dataSummaryView = new DataSummaryView({
                    model: {
                        application: this.model.application,
                        ast: this.model.ast,
                        config: this.model.config,
                        dataset: this.model.dataset,
                        searchJob: this.model.searchJob,
                        state: this.model.state,
                        timeRange: this.model.timeRange
                    }
                });
            },

            startListening: function() {
                this.listenTo(this.model.dataset.entry.content, 'change:dataset.display.mode', this.manageStateOfChildren);
            },

            activate: function(options) {
                var clonedOptions = _.extend({}, (options || {}));
                delete clonedOptions.deep;

                if (this.active) {
                    return BaseView.prototype.activate.call(this, clonedOptions);
                }

                this.manageStateOfChildren();

                return BaseView.prototype.activate.call(this, clonedOptions);
            },

            manageStateOfChildren: function() {
                if (this.model.dataset.entry.content.get('dataset.display.mode') === datasetMixin.MODES.TABLE) {
                    this.children.resultsView.activate({ deep: true }).$el.css('display', '');
                    this.children.dataSummaryView.deactivate({ deep: true }).$el.hide();
                } else {
                    this.children.resultsView.deactivate({ deep: true }).$el.hide();
                    this.children.dataSummaryView.activate({ deep: true }).$el.css('display', '');
                }
            },

            render: function() {
                if (!this.$el.html()) {
                    this.$el.html(this.compiledTemplate({
                        _: _,
                        containsStar: this.model.dataset.getFlattenedFieldsObj().containsStar
                    }));

                    this.children.resultsView.render().appendTo(this.$el);
                    this.children.dataSummaryView.render().appendTo(this.$el);

                    this.manageStateOfChildren();
                }

                return this;
            },

            template: '\
                <% if (containsStar) { %>\
                    <div class="alert-warning">\
                        <i class="icon-alert"></i>\
                        <%= _("There may be more fields for this dataset than are displayed here. Open this dataset in Search to explore it further.").t() %>\
                    </div>\
                <% } %>\
            '
        });
    }
);
