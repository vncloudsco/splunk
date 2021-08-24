define(
    [
        'module',
        'jquery',
        'underscore',
        'views/Base',
        'uri/route'
    ],
    function(
        module,
        $,
        _,
        BaseView,
        route
    ) {
        return BaseView.extend({
            moduleId: module.id,
            tagName: 'ul',
            className: 'explore_actions',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
            },

            render: function() {
                var datasetName = this.model.dataset.getFromName(),
                    fromType = this.model.dataset.getFromType(),
                    fromQuery = this.model.dataset.getFromSearch(),
                    selectedFieldsString = this.model.dataset.getSelectedFieldsString(),
                    hasTimeField = this.model.dataset.hasField('_time'),

                    appName = this.model.dataset.entry.acl.get('app'),
                    datasetApp = _.find(this.collection.apps.models, function (app) {
                        return app.entry.get('name') === appName;
                    }),
                    app = datasetApp && datasetApp.entry.content.get("visible") ? appName : this.options.alternateApp,
                    openInApp = this.model.application.get("app"),
                    searchLinkData = {
                        q: fromQuery
                    },
                    pivotLinkData = {
                        data: {
                            dataset: datasetName,
                            type: fromType
                        }
                    },
                    extendSearchLink,
                    extendPivotLink;

                if (this.model.searchJob && !this.model.searchJob.isNew()) {
                    if (hasTimeField) {
                        pivotLinkData.data.windowedEarliest = this.model.searchJob.getWindowedEarliestTimeOrAllTime();
                        pivotLinkData.data.windowedLatest = this.model.searchJob.getWindowedLatestTimeOrAllTime();
                    }
                    pivotLinkData.data.earliest = this.model.searchJob.getDispatchEarliestTime();
                    pivotLinkData.data.latest = this.model.searchJob.getDispatchLatestTime();

                    searchLinkData.sid = this.model.searchJob.id;
                    searchLinkData.earliest = this.model.searchJob.getDispatchEarliestTime();
                    searchLinkData.latest = this.model.searchJob.getDispatchLatestTime();
                    searchLinkData.q = this.model.searchJob.getSearch();
                }

                extendPivotLink = route.pivot(
                    this.model.application.get('root'),
                    this.model.application.get('locale'),
                    this.model.application.get('app'),
                    pivotLinkData);

                if (openInApp === "system") {
                    openInApp = app;
                }

                if (selectedFieldsString) {
                    searchLinkData['display.events.fields'] = selectedFieldsString;
                }

                extendSearchLink = route.search(
                    this.model.application.get('root'),
                    this.model.application.get('locale'),
                    openInApp,
                    {
                        data: searchLinkData
                    });

                this.$el.html(this.compiledTemplate({
                    canSearch: this.model.dataset.canSearch(),
                    searchLink: extendSearchLink,
                    canPivot: this.model.dataset.canPivot(),
                    pivotLink: extendPivotLink
                }));

                return this;
            },

            template: '\
                <% if (canPivot) { %>\
                    <li><a class="explore_link" href="<%= pivotLink %>"><%- _("Visualize with Pivot").t() %></a></li>\
                <% } %>\
                <% if (canSearch) { %>\
                    <li><a class="explore_link" href="<%= searchLink %>"><%- _("Investigate in Search").t() %></a></li>\
                <% } %>\
            '
        });
    }
);
