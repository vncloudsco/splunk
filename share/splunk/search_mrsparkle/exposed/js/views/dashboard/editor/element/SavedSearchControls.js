define([
    'module',
    'jquery',
    'underscore',
    'views/dashboard/editor/element/ElementControls',
    'views/shared/reportcontrols/details/Master',
    'views/dashboard/editor/element/DialogHelper',
    'controllers/dashboard/helpers/EditingHelper',
    'controllers/dashboard/helpers/ModelHelper',
    'uri/route'
], function(module,
            $,
            _,
            ElementControls,
            ReportDetailsView,
            DialogHelper,
            EditingHelper,
            ModelHelper,
            route) {

    var SavedSearchControls = ElementControls.extend({
        moduleId: module.id,
        events: _.extend(ElementControls.prototype.events, {
            'click a.viewPanelReport': 'onViewPanelReport',
            // NOTE: the following four selectors are defined in separate view components. So these selectors need to be
            // updated when their definition change, it is unlikely to change though since they are shared view components.
            'click a.edit-schedule, a.edit-acceleration, a.edit-permissions, a.edit-embed': function(e) {
                // need to close the popdown when any modal shows up.
                e.preventDefault();
                this.children.popdown.hide();
            },
            'click a.cloneSearchReport': function(e) {
                e.preventDefault();
                // convert into a inline search
                DialogHelper.confirmConvertToInline({
                    isPivot: this.model.savedReport.isPivotReport()
                }).then(function() {
                    EditingHelper.saveAsInlineSearch(this.searchManager, this.model.elementReport, this.model.report, {
                        app: this.model.application.get('app')
                    });
                    this.model.controller.trigger('edit:save-report-as-inline', {
                        elementId: this.settings.get('id'),
                        searchManagerId: this.searchManager.id
                    });
                }.bind(this));
                this.children.popdown.hide();
            },
            'click a.selectNewReport': function(e) {
                e.preventDefault();
                var reportLimit = 100;
                var reports = ModelHelper.getCachedModel('reports', {
                    app: this.model.application.get('app'),
                    owner: this.model.application.get('owner'),
                    search: 'is_visible=1 AND disabled=0',
                    count: reportLimit
                });
                var dialog = DialogHelper.openSelectReportDialog({
                    model: this.model,
                    reportLimit: reportLimit,
                    collection: _.extend({}, this.collection, {
                        reports: reports
                    })
                }).on('updateReportID', function(reportId, panelTitle) {
                    var elementId = this.settings.get('id');
                    EditingHelper.updateReportId(this.searchManager, elementId, this.model.savedReport, reportId, panelTitle, {
                        app: this.model.application.get('app')
                    }).then(function() {
                        this.model.controller.trigger('edit:update-report-id', {
                            searchManagerId: this.searchManager.id,
                            elementId: elementId
                        });
                        dialog.hide();
                    }.bind(this));
                }.bind(this));
                this.children.popdown.hide();
            },
            'click a.useReportFormatting': function(e) {
                e.preventDefault();
                DialogHelper.confirmUseReportSetting().then(function() {
                    var elementId = this.settings.get('id');
                    EditingHelper.useReportSettingsForElement(this.model.elementReport, this.model.savedReport);
                    this.model.controller.trigger('edit:use-report-formatting', {elementId: elementId});
                }.bind(this));
                this.children.popdown.hide();
            }
        }),

        getIconClass: function() {
            return this.model.savedReport.isPivotReport() ? "icon-report-pivot" : "icon-report-search";
        },

        getTemplateArgs: function() {
            return {
                reportName: this.model.savedReport.entry.get('name')
            };
        },

        tooltip: function(options) {
            this.$('a.viewPanelReport').tooltip(options);
        },

        render: function() {
            ElementControls.prototype.render.apply(this, arguments);

            this.tooltip({
                title: _('View report').t()
            });

            return this;
        },

        template: '\
            <a class="viewPanelReport dropdown-toggle btn-pill" href="#">\
                    <span class="<%- iconClass %>">\
            </a>\
            <div class="dropdown-menu" />\
        ',

        onViewPanelReport: function(e) {
            e.preventDefault();
            e.stopPropagation();

            this.tooltip('hide');

            var template = this.reportDetailsTemplate,
                root = this.model.application.get('root'),
                locale = this.model.application.get('locale'),
                app = this.model.application.get('app'),
                openInView = this.model.savedReport.openInView(this.model.user);

            var viewRouteData = route.getViewRouteData(openInView);
            var viewReportLink = route.report(root, locale, app, {data: {s: this.model.savedReport.get('id')}});
            var editReportLink = viewRouteData.route(root, locale, app, {data: {s: this.model.savedReport.get('id')}});
            this.$('.dropdown-menu').html(_.template(template, {
                viewReportLink: viewReportLink,
                editReportLink: editReportLink,
                editReportLabel: viewRouteData.openLabel,
                _: _
            }));

            if (this.children.reportDetails) {
                this.children.reportDetails.remove();
            }

            this.children.reportDetails = new ReportDetailsView({
                model: {
                    report: this.model.savedReport,
                    application: this.model.application,
                    appLocal: this.model.appLocal,
                    user: this.model.user,
                    serverInfo: this.model.serverInfo
                },
                collection: {
                    roles: this.collection.roles,
                    alertActions: this.collection.alertActions
                }
            });

            this.$('.reportDetails').prepend($("<li/>").addClass('reportDetailsView').append(this.children.reportDetails.render().el));
            var desc = this.model.savedReport.entry.content.get('description');
            if (desc) {
                this.$('.reportDetails').prepend($("<li/>").addClass('report-description').text(desc));
            }
            this.$('.reportDetails').prepend($("<li/>").addClass('report-name').text(this.model.savedReport.entry.get('name')));
            this.$('.dropdown-menu').addClass('show-details');
            $(window).trigger('resize');
        },
        reportDetailsTemplate: '\
            <div class="arrow"></div>\
            <ul class="reportDetails">\
                <li><a target="_blank" href="<%- viewReportLink %>" class="viewSearchReport"><%- _("View").t() %></a></li>\
                <li><a target="_blank" href="<%- editReportLink %>" class="openSearchReport"><%- editReportLabel %></a></li>\
                <li><a href="#" class="cloneSearchReport"><%- _("Clone to Inline").t() %></a></li>\
            </ul>\
            <ul class="reportActions">\
                <li><a class="selectNewReport"><%- _("Select New Report").t() %></a></li>\
                <li><a class="useReportFormatting"><%- _("Use Report\'s Formatting for this Content").t() %></a></li>\
            </ul>\
        '
    });

    return SavedSearchControls;
});
