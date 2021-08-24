define(
    [
        'underscore',
        'jquery',
        'module',
        'views/Base',
        'views/shared/controls/SyntheticSelectControl',
        'views/shared/SearchResultsPaginator',
        'views/shared/delegates/Dock'
    ],
    function(
        _,
        $,
        module,
        BaseView,
        SyntheticSelectControl,
        SearchResultsPaginator,
        Dock
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'table-caption',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.children.count = new SyntheticSelectControl({
                    model: this.model.dataset.entry.content,
                    modelAttribute: 'dataset.display.count',
                    items: [
                        { value: '10', label: _('10 per page').t() },
                        { value: '20', label: _('20 per page').t() },
                        { value: '50', label: _('50 per page').t() }
                    ],
                    className: 'btn-group pull-left count-control',
                    menuWidth: 'narrow',
                    toggleClassName: 'btn-pill'
                });
            },

            initializePaginator: function() {
                this.children.searchResultsPaginator = new SearchResultsPaginator({
                    model: {
                        state: this.model.dataset.entry.content,
                        searchJob: this.model.searchJob
                    },
                    countKey: 'dataset.display.count',
                    offsetKey: 'dataset.display.offset',
                    mode: this.model.searchJob.isReportSearch() ? 'results_preview' : 'events'
                });

                // TODO: remove when views don't call activate in init
                this.children.searchResultsPaginator.deactivate({ deep:true });
            },

            startListening: function() {
                this.listenTo(this.model.searchJob, 'prepared', function() {
                    if (!this.children.searchResultsPaginator) {
                        this.initializePaginator();

                        if (this.$el.html() && !this.children.searchResultsPaginator.$el.html()) {
                            this.children.searchResultsPaginator.activate({deep: true}).render().appendTo(this.$('.table-caption-inner'));
                        }
                    }
                });
            },

            activate: function(options) {
                if (this.active) {
                    return BaseView.prototype.activate.apply(this, arguments);
                }

                if (!this.children.searchResultsPaginator && !this.model.searchJob.isPreparing()) {
                    this.initializePaginator();
                }

                if (this.children.searchResultsPaginator && this.$el.html() && !this.children.searchResultsPaginator.$el.html()) {
                    this.children.searchResultsPaginator.activate({ deep: true }).render().appendTo(this.$('.table-caption-inner'));
                }

                return BaseView.prototype.activate.apply(this, arguments);
            },

            deactivate: function(options) {
                if (!this.active) {
                    return BaseView.prototype.deactivate.apply(this, arguments);
                }

                if (this.children.searchResultsPaginator) {
                    this.children.searchResultsPaginator.remove();
                    delete this.children.searchResultsPaginator;
                }

                BaseView.prototype.deactivate.apply(this, arguments);

                return this;
            },

            render: function() {
                this.$el.html(this.template);

                var $tableCaptionInner = this.$('.table-caption-inner');

                this.children.count.render().appendTo($tableCaptionInner);
                if (this.children.searchResultsPaginator) {
                    this.children.searchResultsPaginator.render().appendTo($tableCaptionInner);
                }

                this.children.dock = new Dock({
                    el: this.el,
                    affix: '.table-caption-inner'
                });

                return this;
            },

            template: '\
                <div class="table-caption-inner"></div>\
            '
        });
    }
);
