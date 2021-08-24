define(
    [
        'module',
        'jquery',
        'underscore',
        'controllers/dashboard/helpers/ReportModelHelper',
        'models/dashboard/DashboardElementReport',
        'views/dashboard/Base',
        'views/dashboard/editor/element/InlineSearchControls',
        'views/dashboard/editor/element/SavedSearchControls',
        'views/dashboard/editor/element/MiscControlsAdapter',
        'splunkjs/mvc',
        'splunkjs/mvc/savedsearchmanager',
        'uri/route',
        'splunkjs/mvc/tokenutils',
        'views/shared/vizcontrols/Master',
        'util/dashboard_utils',
        './ElementEditor.pcssm'
    ],
    function(module,
             $,
             _,
             ReportModelHelper,
             DashboardElementReport,
             BaseDashboardView,
             InlineSearchControls,
             SavedSearchControls,
             MiscControls,
             mvc,
             SavedSearchManager,
             route,
             TokenUtils,
             VizControls,
             DashboardUtils,
             css
    ) {
        return BaseDashboardView.extend({
            moduleId: module.id,
            viewOptions: {
                register: false
            },
            className: 'dashboard-element-editor ' + css.flexContainer,
            initialize: function() {
                BaseDashboardView.prototype.initialize.apply(this, arguments);

                this.bindToComponentSetting('managerid', this.renderElementControl, this);
                this.bindToComponentSetting('evtmanagerid', this.renderElementControl, this);

                this.children.vizControls = new VizControls({
                    model: {
                        report: this.model.report,
                        application: this.model.application,
                        user: this.model.user
                    },
                    vizTypes: ['events', 'statistics', 'visualizations'],
                    saveOnApply: true, //do not save on apply
                    vizpicker: this.reportContainsTokenInVizType() ? {
                        warningMsg: _("Warning: Changes here can overwrite related token settings and behavior in your source code.").t()
                    } : undefined,
                    format: this.reportContainsTokenInFormat() ? {
                        warningMsg: _("Warning: Changes here can overwrite related token settings and behavior in your source code.").t()
                    } : undefined,
                    dashboard: true
                });

                this.listenTo(this.model.report.entry.content, DashboardElementReport.getTypeChangeEvents().join(' '), this.updateDrilldown);
            },
            reportContainsTokenInVizType: function() {
                var reportModelContent = this.model.elementReport.toJSON({tokens: true});
                var tokenReleatedKey = _.find(DashboardElementReport.getVizTypeReportProperties(), function(key) {
                    return reportModelContent[key] && TokenUtils.hasToken(reportModelContent[key]);
                });
                return tokenReleatedKey != null;
            },
            reportContainsTokenInFormat: function() {
                var reportModelContent = this.model.elementReport.toJSON({tokens: true});
                var pairWithToken = _.chain(reportModelContent).pairs().find(function(pair) {
                    var isDisplayProp = pair[0].indexOf("display") === 0;
                    var isNotVizTypeProp = _(DashboardElementReport.getVizTypeReportProperties()).indexOf(pair[0]) < 0;
                    var propValueHasToken = TokenUtils.hasToken(pair[1]);
                    return isDisplayProp && isNotVizTypeProp && propValueHasToken;
                }).value();
                return pairWithToken != null;
            },
            renderElementControl: function() {
                if (this.children.elementControls) {
                    this.children.elementControls.remove();
                }

                if (this.children.miscControls) {
                    this.children.miscControls.remove();
                }

                var searchManager = DashboardUtils.getPrimarySearchManager(this.settings.get('managerid'), mvc.Components);
                var eventManager = mvc.Components.get(this.settings.get('evtmanagerid'));

                var ElementControls = searchManager instanceof SavedSearchManager ? SavedSearchControls : InlineSearchControls;

                this.children.elementControls = new ElementControls({
                    model: this.model,
                    collection: this.collection,
                    searchManager: searchManager,
                    eventManager: eventManager,
                    settings: this.settings
                });
                this.children.elementControls.render().$el.prependTo(this.$el);

                this.children.miscControls = new MiscControls({
                    model: this.model,
                    collection: this.collection,
                    searchManager: searchManager,
                    eventManager: eventManager,
                    settings: this.settings
                });
                this.children.miscControls.render().$el.appendTo(this.$el);
            },
            updateDrilldown: function() {
                this.model.report.entry.content.set(ReportModelHelper.transferDrilldown(
                    this.model.report.entry.content.previousAttributes(),
                    this.model.report.entry.content.toJSON()
                ));
            },
            render: function() {
                this.renderElementControl();
                this.children.vizControls.render().$el.appendTo(this.$el);
                return this;
            }
        });
    });
