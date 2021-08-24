define(
    [
        'underscore',
        'module',
        'models/datasets/commands/InitialData',
        'views/Base',
        'views/shared/controls/ControlGroup',
        'contrib/text!./IndexesAndSourcetypesSVG.html',
        'contrib/text!./DatasetSVG.html',
        'contrib/text!./SearchSVG.html'
    ],
    function(
        _,
        module,
        InitialDataCommand,
        BaseView,
        ControlGroup,
        IndexesAndSourcetypesSVG,
        DatasetSVG,
        SearchSVG
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'method-picker',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
            },

            events: {
                'click .methodIndexes a': function (e) {
                    e.preventDefault();
                    this.model.command.set('selectedMethod', InitialDataCommand.METHODS.INDEXES_AND_SOURCETYPES);
                },

                'click .methodDataset a': function(e) {
                    e.preventDefault();
                    this.model.command.set('selectedMethod', InitialDataCommand.METHODS.DATASET);
                },

                'click .methodSearch a': function(e) {
                    e.preventDefault();
                    this.model.command.set('selectedMethod', InitialDataCommand.METHODS.SEARCH);
                }
            },

            updateTabs: function() {
                var current = this.model.command.get('selectedMethod');
                var methods = InitialDataCommand.METHODS;
                this.$('.nav-tabs li').removeClass('active');
                this.$('.methodIndexes')[current === methods.INDEXES_AND_SOURCETYPES ? 'addClass': 'removeClass']('active');
                this.$('.methodDataset')[current === methods.DATASET ? 'addClass': 'removeClass']('active');
                this.$('.methodSearch')[current === methods.SEARCH ? 'addClass': 'removeClass']('active');
            },

            startListening: function(options) {
                this.listenTo(this.model.command, 'change:selectedMethod', this.updateTabs);
            },

            render: function() {
                if (!this.$el.html()) {
                    this.$el.html(this.compiledTemplate({
                        _: _,
                        IndexesAndSourcetypesSVG: IndexesAndSourcetypesSVG,
                        DatasetSVG: DatasetSVG,
                        SearchSVG: SearchSVG
                    }));
                }
                this.updateTabs();

                return this;
            },

            template: '\
                <ul class="nav nav-tabs">\
                    <li class="methodIndexes"><a href="#"><%= IndexesAndSourcetypesSVG %><div><%- _(\'Indexes & Source Types\').t() %></div></a></li>\
                    <li class="methodDataset"><a href="#"><%= DatasetSVG %><div><%- _(\'Existing Datasets\').t() %></div></a></li>\
                    <li class="methodSearch"><a href="#"><%= SearchSVG %><div><%- _(\'Search (Advanced)\').t() %></div></a></li>\
                </ul>\
            '
        });
    }
);
