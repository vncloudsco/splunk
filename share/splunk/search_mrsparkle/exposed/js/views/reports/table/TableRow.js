define(
    [
        'underscore',
        'module',
        'views/Base',
        'views/shared/reportcontrols/editmenu/Master',
        'views/shared/delegates/TableRowToggle',
        'uri/route',
        'util/splunkd_utils'
    ],
    function(
        _,
        module,
        BaseView,
        EditDropDown,
        TableRowToggleView,
        route,
        splunkd_utils
    )
    {
        return BaseView.extend({
            moduleId: module.id,
            tagName: 'tr',
            className: 'expand',
            /**
             * @param {Object} options {
             *     model: {
             *          report: <models.Report>,
             *          application: <models.Application>,
             *          state: <Backbone.Model>,
             *          appLocal: <models.services.AppLocal>,
             *          user: <models.service.admin.user>
             *     },
             *     collection: {
             *          roles: <collections.services.authorization.Roles>,
             *          apps: <collections.services.AppLocals>,
             *          alertActions: <collections.shared.ModAlertActions> (Optional: for edit schedule dialog)
             *     },
             *     index: <index_of_the_row>,
             *     alternateApp: <alternate_app_to_open>
             * }
             */
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                this.$el.addClass((this.options.index % 2) ? 'even' : 'odd');
                var appLocals = this.collection.apps,
                    updatedCollection = _.omit(this.collection, 'apps');
                updatedCollection.appLocals = appLocals;
                this.editdropdown = new EditDropDown({
                    model: {
                        application: this.model.application,
                        report: this.model.report,
                        user: this.model.user,
                        appLocal: this.model.appLocal,
                        serverInfo: this.model.serverInfo
                    },
                    collection: updatedCollection,
                    button: false,
                    showOpenActions: false
                });
                this.activate();
            },
            startListening: function() {
                this.listenTo(this.model.report, 'updateCollection', function() {
                    this.model.state.trigger('change:search');
                });
                this.listenTo(this.model.report.entry.content, 'change:next_scheduled_time', this.updateScheduleTime);
                this.listenTo(this.model.report.entry.acl, 'change:sharing', this.updateSharing);
            },
            updateSharing: function () {
                var sharing = this.model.report.entry.acl.get('sharing');
                var sharingLabel = splunkd_utils.getSharingLabel(sharing);
                this.$('td.sharing').text(sharingLabel);
            },
	        /**
             * Update the Schedule Time column when the report schedule changes.
             * Display None when the report is not scheduled.
             */
            updateScheduleTime: function () {
                this.$('td.scheduled_time').text(this.model.report.entry.content.get('next_scheduled_time') || _('None').t());
            },
            render: function() {
                var openInView = this.model.report.openInView(this.model.user),
                    reportName   = this.model.report.entry.get('name'),
                    appName = this.model.report.entry.acl.get('app'),
                    reportApp = _.find(this.collection.apps.models, function(app) {return app.entry.get('name') === appName;}),
                    app = reportApp && reportApp.entry.content.get("visible") ? appName : this.options.alternateApp,
                    openInApp = this.model.application.get("app");
                if (openInApp === "system") {
                    openInApp = app;
                }
                var viewRouteData = route.getViewRouteData(openInView, this.collection.apps);
                var reportLink = route.report(
                    this.model.application.get("root"),
                    this.model.application.get("locale"),
                    openInApp,
                    { data: { s: this.model.report.id }}
                );
                var openLink = viewRouteData.route(
                    this.model.application.get("root"),
                    this.model.application.get("locale"),
                    openInApp,
                    { data: { s: this.model.report.id }}
                );
                this.$el.html(this.compiledTemplate({
                    reportName: reportName,
                    openInText: viewRouteData.openLabel,
                    reportLink: reportLink,
                    link: openLink,
                    app: this.model.report.entry.acl.get('app'),
                    scheduled_time: this.model.report.entry.content.get('next_scheduled_time') || _('None').t(),
                    owner: this.model.report.entry.acl.get('owner'),
                    index: this.options.index,
                    canUseApps: this.model.user.canUseApps()
                }));
                this.updateSharing();
                this.editdropdown.render().appendTo(this.$('.actions-edit'));
                return this;
            },
            template: '\
                <td class="expands">\
                    <a href="#" aria-label="<%-_("Expand Table Row").t()%>"><i class="icon-triangle-right-small"></i></a>\
                </td>\
                <td class="title">\
                    <a href="<%= reportLink %>" title="<%- reportName %>"><%- reportName %></a>\
                </td>\
                <td class="actions actions-edit">\
                    <a class="openInLink" href="<%= link %>"><%- openInText %></a>\
                </td>\
                <td class="scheduled_time"><%- scheduled_time %></td>\
                <td class="owner"><%- owner %></td>\
                <% if(canUseApps) { %>\
                    <td class="app"><%- app %></td>\
                <% } %>\
                <td class="sharing">Global</td>\
            '
        });
    }
);
