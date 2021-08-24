define([
        'jquery',
        'underscore',
        'module',
        'models/Base',
        'models/search/SearchHistory',
        'models/services/search/jobs/Result',
        'views/Base',
        'views/search/searchhistory/historycontent/Master',
        'splunk.util',
        './Master.pcss'
    ],
    function (
        $,
        _,
        module,
        BaseModel,
        SearchHistoryModel,
        ResultsModel,
        BaseView,
        HistoryContentView,
        splunkutil,
        css
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'search-history',
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                this.model.searchHistoryResults = new ResultsModel();
                this.model.tableData = new BaseModel();
                this.model.searchHistoryJob = new SearchHistoryModel({},
                    {
                        delay: SearchHistoryModel.DEFAULT_POLLING_INTERVAL,
                        processKeepAlive: true,
                        keepAliveInterval: SearchHistoryModel.DEFAULT_LONG_POLLING_INTERVAL
                    });
                this.children.historyContent = new HistoryContentView({
                    model: {
                        application: this.model.application,
                        tableData: this.model.tableData,
                        searchBar: this.model.searchBar,
                        searchHistoryJob: this.model.searchHistoryJob,
                        searchHistoryResults: this.model.searchHistoryResults,
                        uiPrefs: this.model.uiPrefs
                    }
                });
            },
            events: {
                'click a.show-history': function(e) {
                    e.preventDefault();
                    var $title = this.$('.show-history > h3');
                    if (this.$('.show-history > i').hasClass('icon-chevron-down')) {
                        this.children.historyContent.$el.hide();
                        this.children.historyContent.deactivate({deep: true});
                        this.$('.show-history > i').removeClass('icon-chevron-down').addClass('icon-chevron-right');
                    } else {
                        this.children.historyContent.$el.show();
                        this.children.historyContent.activate({deep: true});
                        this.$('.show-history > i').removeClass('icon-chevron-right').addClass('icon-chevron-down');
                    }
                }
            },
            activate: function() {
                if (this.active) {
                    return BaseView.prototype.activate.apply(this, arguments);
                }

                if (this.isExpanded()) {
                    this.children.historyContent.activate({deep: true});
                }
                return BaseView.prototype.activate.apply(this, arguments);
            },
            isExpanded: function() {
               return this.$('.show-history > i').hasClass('icon-chevron-down');
            },
            render: function() {
                this.$el.html(this.compiledTemplate({
                    _: _
                }));
                var $title = this.$('.show-history > h3');
                this.children.historyContent.render().appendTo(this.$el).$el.hide();
                return this;
            },
            template: '\
                <div class="search-history-label">\
                    <a class="show-history" href="#">\
                        <i class="icon-chevron-right"></i> <h2 class="h3"><%= _("Search History").t() %></h2>\
                    </a>\
                </div>\
            '
        });
    });
