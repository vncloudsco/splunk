define([
        'jquery',
        'underscore',
        'module',
        'models/search/SearchHistory',
        'views/Base',
        'views/shared/TableHead',
        'views/search/searchhistory/historycontent/TableRow',
        'views/shared/delegates/TableRowToggle',
        'views/shared/SearchResultsPaginator',
        'views/shared/FindInput',
        'views/shared/controls/SyntheticSelectControl'
    ],
    function (
        $,
        _,
        module,
        SearchHistoryModel,
        BaseView,
        TableHead,
        TableRow,
        TableRowToggleDelegate,
        SearchResultsPaginator,
        FilterInputView,
        SyntheticSelectControlView
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'history-content content-section',
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                this.model.tableData.set("count", this.model.uiPrefs.entry.content.get("display.page.search.searchHistoryCount"));
                this.model.tableData.set("earliest_time", this.model.uiPrefs.entry.content.get("display.page.search.searchHistoryTimeFilter"));
                this.children.input = new FilterInputView({
                    model: this.model.tableData,
                    key: "search"
                });
                this.children.tableRowToggle = new TableRowToggleDelegate({
                    el: this.el,
                    collapseOthers: true,
                    disabledClass: 'disabled'
                });
                this.children.collectionPaginator = new SearchResultsPaginator({
                    model: {
                        state: this.model.tableData,
                        searchJob: this.model.searchHistoryJob,
                        results: this.model.searchHistoryResults
                    },
                    maxPerPage: this.model.tableData.get("count"),
                    mode: 'results'
                });

                this.children.timeDropdown = new SyntheticSelectControlView({
                    controlType: 'SyntheticSelect',
                    model: this.model.tableData,
                    modelAttribute: 'earliest_time',
                    descriptionPosition: 'top',
                    items: [
                        {
                            value: "0",
                            label: _("No Time Filter").t()
                        },
                        {
                            value: "@d",
                            label: _("Today").t(),
                            description: _("Ran:").t()
                        },
                        {
                            value: "-7d@d",
                            label: _("Last 7 Days").t(),
                            description: _("Ran in:").t()
                        },
                        {
                            value: "-30d@d",
                            label: _("Last 30 Days").t(),
                            description: _("Ran in:").t()
                        }
                    ],
                    className: 'time-selected',
                    toggleClassName: 'btn',
                    popdownOptions: {
                        attachDialogTo: 'body'
                    }
                });

                this.children.countDropdown = new SyntheticSelectControlView({
                    controlType: 'SyntheticSelect',
                    model: this.model.tableData,
                    modelAttribute: 'count',
                        items: [
                            { value: '10',  label: _('10 Per Page').t()  },
                            { value: '20',  label: _('20 Per Page').t()  },
                            { value: '50',  label: _('50 Per Page').t()  }
                        ],
                    menuWidth: "narrow",
                    className: 'btn-group count-selected',
                    toggleClassName: 'btn-pill'
                });

                this.children.head = new TableHead({
                    model: this.model.tableData,
                    columns: [
                        {
                            html: '<i class="icon-info"></i>',
                            className: 'col-info'
                        },
                        {
                            label: _("Search").t(),
                            className: 'search-header',
                            sortKey: 'search'
                        },
                        {
                            label: _("Actions").t(),
                            className: 'actions-header'
                        },
                        {
                            label: _("Last Run").t(),
                            className: 'time-ran-header',
                            sortKey: '_time'
                        }
                    ]
                });
            },
            startListening: function() {
                this.listenTo(this.model.searchHistoryJob, 'done', this.fetchSearchHistoryResults);
                this.listenTo(this.model.searchHistoryResults, 'sync', this.handleSearchHistoryResults);
                this.listenTo(this.model.searchHistoryResults, 'error', function() { this.$el.css('minHeight', ''); });
                this.listenTo(this.model.tableData, 'change:search change:offset change:sortKey change:sortDirection', _.debounce(this.fetchSearchHistoryResults));
                this.listenTo(this.model.tableData, 'change:earliest_time', _.debounce(this.startSearchHistoryJob));
                this.listenTo(this.model.tableData, 'change:count', this.modifySearchHistoryCount);
            },
            showLoading: function(show) {
                var $waiting = this.$('tr.waiting'),
                    $noResults = this.$('tr.noresults');
                if (show) {
                    $waiting.show();
                    $noResults.hide();
                    this.clearTable();
                } else {
                    $waiting.hide();
                }
            },
            modifySearchHistoryCount: function() {
                this.fetchSearchHistoryResults();
                this.model.uiPrefs.entry.content.set({
                    'display.page.search.searchHistoryCount': this.model.tableData.get("count")
                });
                this.model.uiPrefs.save();
            },
            clearSearchHistory: function() {
                this.model.searchHistoryJob.clear();
                this.model.searchHistoryResults.fetchAbort();
                this.model.searchHistoryResults.clear();
            },
            clearTable: function() {
                this.$el.css('minHeight', this.$el.height());
                this.$('.search-content tr:not(.waiting):not(.noresults)').remove();
            },
            startSearchHistoryJob: function() {
                this.showLoading(true);
                this.model.uiPrefs.entry.content.set({
                    'display.page.search.searchHistoryTimeFilter': this.model.tableData.get("earliest_time")
                });
                this.model.uiPrefs.save();
                // Don't trigger a change event to get new results.
                this.model.tableData.set({offset: 0}, {silent: true});
                if (!this.model.searchHistoryJob.isNew()) {
                    this.clearSearchHistory();
                }
                $.when(this.model.searchHistoryJob.startJob(this.model.application,
                    {data: {
                        earliest_time: this.model.tableData.get("earliest_time"),
                        provenance: 'UI:Search'
                    }})).then(function() {
                    this.model.searchHistoryJob.startPolling();
                }.bind(this));
            },
            handleSearchHistoryResults: function() {
                this.showLoading(false);
                this.render();
            },
            fetchSearchHistoryResults: function() {
                var id = this.model.searchHistoryJob.entry.links.get(SearchHistoryModel.RESULTS);
                if (!_.isUndefined(id)) {
                    this.showLoading(true);
                    this.model.searchHistoryResults.set({id: id});
                    this.model.searchHistoryResults.safeFetch({
                        data: {
                            offset: this.model.tableData.get("offset"),
                            count: this.model.tableData.get("count"),
                            search: this.buildSearch()
                        }
                    });
                }
            },
            buildSearch: function() {
                var search = "| search " + (this.model.tableData.get("search") || "");
                if (this.model.tableData.get("sortKey") && this.model.tableData.get("sortDirection")) {
                    search += ' | sort ';
                    search += this.model.tableData.get("sortDirection") === 'desc' ?
                        '-' :
                        '';
                    search += this.model.tableData.get("sortKey");
                }
                return search;
            },
            activate: function() {
                if (this.active) {
                    return BaseView.prototype.activate.apply(this, arguments);
                }
                this.$('.search-content tr:not(.waiting):not(.noresults)').remove();
                this.startSearchHistoryJob();
                this.showLoading(true);
                return BaseView.prototype.activate.apply(this, arguments);
            },
            deactivate: function() {
                if (!this.active) {
                    return BaseView.prototype.deactivate.apply(this, arguments);
                }
                this.clearSearchHistory();
                return BaseView.prototype.deactivate.apply(this, arguments);
            },
            render: function() {
                var $noResults = this.$('tr.noresults');
                if (!this.$el.html()) {
                    this.$el.html(this.compiledTemplate());
                    this.children.timeDropdown.render().appendTo(this.$('.history-filters'));
                    this.children.input.render().prependTo(this.$('.history-filters'));
                    this.children.countDropdown.render().appendTo(this.$('.history-filters'));
                    this.children.head.render().prependTo(this.$('.table'));
                    this.children.collectionPaginator.render().prependTo(this.$el);
                }
                var $tableBody = this.$('tbody');
                this.clearTable();
                if (!this.model.searchHistoryResults.results.length) {
                    $noResults.show();
                } else {
                    $noResults.hide();
                    _.each(this.model.searchHistoryResults.results.models, function(search, index) {
                        var row = new TableRow({
                                model: {
                                    application: this.model.application,
                                    fetchData: search,
                                    searchBar: this.model.searchBar,
                                    tableData: this.model.tableData
                                },
                                isAccordion: false,
                                striped: index % 2
                            }),
                            accordionRow = new TableRow({
                                model: {
                                    application: this.model.application,
                                    fetchData: search,
                                    searchBar: this.model.searchBar,
                                    tableData: this.model.tableData
                                },
                                isAccordion: true,
                                striped: index % 2
                            });

                        row.render().$el.appendTo($tableBody);
                        row.disableNonTruncated();
                        accordionRow.render().$el.appendTo($tableBody);
                    }.bind(this));
                }
                this.$el.css('minHeight', '');
                return this;
            },
            template: '\
                <div class="history-filters">\
                </div>\
                <table class="table table-chrome table-listing table-striped table-hover table-row-expanding">\
                    <tbody class="history-group search-content">\
                        <tr class="waiting"><td colspan="4"><%- _("Waiting for results...").t() %></td></tr>\
                        <tr class="noresults" style="display:none"><td colspan="4"><%- _("No results found.").t() %></td></tr>\
                    </tbody>\
                </table>\
            '
        });
    });
