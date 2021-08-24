define([
    'underscore',
    'jquery',
    'backbone',
    'models/search/Report',
    'models/MeltingPot',
    'util/readonly',
    'controllers/dashboard/helpers/vizTypeNames',
    'splunkjs/mvc/utils'
], function(_, $, Backbone, Report, MeltingPot, ReadOnly, vizTypeNames, Utils) {

    var DashboardElementReportContent = MeltingPot.extend({
        initialize: function() {
            MeltingPot.prototype.initialize.apply(this, arguments);
            this.transientProps = new Backbone.Model();
        },
        set: function(key, val, options) {
            if (key == null) {
                return this;
            }
            if (typeof key === 'object') {
                options = val;
            }

            if (options && options['transient'] && this.transientProps) {
                this.transientProps.set.apply(this.transientProps, arguments);
                return this;
            } else {
                return MeltingPot.prototype.set.apply(this, arguments);
            }
        },
        toJSON: function(options) {
            var result;
            if (options && options.omitNonSavedSearchesDefaults) {
                result = MeltingPot.mergeModels(_(this._delegates).without(DashboardElementReport.NON_SAVEDSEARCHES_DEFAULTS), options);
            } else {
                result = MeltingPot.prototype.toJSON.apply(this, arguments);
            }
            return options && options.onlyDisplayProperties ? DashboardElementReport.getDisplayProperties(result) : result;
        },
        save: function() {
            this.trigger('save');
            return $.Deferred().resolve();
        }
    });

    var VIZ_TYPE_REPORT_PROPERTIES = [
        'display.general.type',
        'display.events.type',
        'display.visualizations.type',
        'display.visualizations.custom.type',
        'display.visualizations.charting.chart',
        'display.visualizations.mapping.type'
    ];

    var DashboardElementReport = Report.extend({
        initialize: function(options) {
            Report.prototype.initialize.call(this);
            if (options && options.delegate) {
                this.entry.content.addDelegate(options.delegate);
            }
            this.entry.content.addDelegate(this.entry.content.transientProps);
            this.typeModel = new Backbone.Model();
            this.entry.content.addDelegate(this.typeModel);
            this.editStateDelegate = new Backbone.Model();
            this.entry.content.addDelegate(this.editStateDelegate);
            this.entry.content.addDelegate(DashboardElementReport.NON_SAVEDSEARCHES_DEFAULTS);
            this.viewModeSink = new Backbone.Model();
            this.setEditable(options.editable);
            this.listenTo(this.entry.content, DashboardElementReport.getTypeChangeEvents().join(' '), this.updateTypeModel);
            this.listenTo(this.entry.content, 'save', this.save);
            this.updateTypeModel();
        },
        setEditable: function(editable) {
            this.entry.content.removeDelegate(this.viewModeSink);
            this.viewModeSink.clear();
            if (!editable) {
                this.entry.content.addDelegate(this.viewModeSink, {index: 0});
            }
            this.editStateDelegate.set('dashboard.element.edit', !!editable);
        },
        setDefaults: function(model) {
            this.entry.content.addDelegate(model.entry.content);
        },
        updateTypeModel: function() {
            this.typeModel.set('dashboard.element.viz.type', DashboardElementReport.getVizType(this));
        },
        fetch: function() {
            throw new Error('Cannot fetch DashboardElementReport');
        },
        initializeAssociated: function() {
            Report.prototype.initializeAssociated.apply(this, arguments);
            this.entry.content = new DashboardElementReportContent({delegates: []});
            this.entry.acl = new MeltingPot({ delegates: [] });
        },
        setReportDelegate: function(report) {
            this.entry.set('name', report.entry.get('name'));
            this.entry.acl.removeDelegates();
            this.entry.acl.addDelegate(report.entry.acl);
        },
        clearReportDelegate: function() {
            this.entry.unset('name');
            this.entry.acl.removeDelegates();
        },
        isNew: function() {
            return this.entry.get('name') == null || this.entry.get('name') == '_new';
        },
        save: function() {
            this.trigger('save');
            return $.Deferred().resolve();
        }
    }, {
        VIZ_TYPES: ['table', 'chart', 'event', 'single', 'list', 'map', 'html', 'viz'],
        NON_SAVEDSEARCHES_DEFAULTS: ReadOnly.readOnlyModel(new Backbone.Model({
            'display.prefs.statistics.count': '10',
            'display.prefs.events.count': '10',
            'display.visualizations.chartHeight': '250',
            'display.visualizations.singlevalueHeight': '115',
            'display.visualizations.singlevalue.linkView': 'search',
            'display.events.showPager': '1',
            'display.events.histogram': '0',
            'display.events.fields': '["host", "source", "sourcetype"]',
            'display.events.table.sortDirection': 'asc',
            'display.visualizations.resizable': true,
            'display.visualizations.custom.resizable': true,
            'display.visualizations.singlevalue.resizable': true,
            'dashboard.element.refresh.display': 'progressbar'
        })),
        getTypeChangeEvents: function() {
            return _(VIZ_TYPE_REPORT_PROPERTIES).map(function(prop) { return 'change:' + prop; });
        },
        getVizType: function(report) {
            return DashboardElementReport.getVizTypeFromReportContent(report.entry.content.toJSON());
        },
        getVizTypeFromReportContent: function(content) {
            var type = null;
            switch (content['display.general.type']) {
                case 'visualizations':
                    switch (content['display.visualizations.type']) {
                        case 'charting':
                            type = vizTypeNames.CHART;
                            break;
                        case 'singlevalue':
                            type = vizTypeNames.SINGLE_VALUE;
                            break;
                        case 'mapping':
                            type = vizTypeNames.MAP;
                            break;
                        case 'custom':
                            type = vizTypeNames.CUSTOM_VIZ;
                            break;
                    }
                    break;
                case 'events':
                    type = vizTypeNames.EVENT;
                    break;
                case 'statistics':
                    type = vizTypeNames.TABLE;
                    break;
            }
            return type;
        },
        getVizTypeReportProperties: function() {
            return VIZ_TYPE_REPORT_PROPERTIES;
        },
        getDisplayPropertyPrefixes: function(reportContent) {
            var generalType = reportContent['display.general.type'];
            var prefixes;
            switch (generalType) {
                case 'visualizations':
                    switch (reportContent['display.visualizations.type']) {
                        case 'charting':
                            prefixes = ['display.visualizations.trellis', 'display.visualizations.charting'];
                            break;
                        case 'singlevalue':
                            prefixes = ['display.visualizations.trellis', 'display.visualizations.singlevalue'];
                            break;
                        case 'mapping':
                            prefixes = ['display.visualizations.trellis', 'display.visualizations.mapping'];
                            break;
                        case 'custom':
                            prefixes = ['display.visualizations.trellis', 'display.visualizations.custom'];
                            break;
                    }
                    break;
                case 'events':
                    prefixes = ['display.events'];
                    break;
                case 'statistics':
                    prefixes = ['display.statistics'];
                    break;
            }
            return prefixes;
        },
        getDisplayProperties: function(reportContent, noPrefix) {
            var properties = {};
            var prefixes = DashboardElementReport.getDisplayPropertyPrefixes(reportContent);
            if (prefixes) {
                _.each(reportContent, function(v, k) {
                    _.each(prefixes, function (prefix) {
                        if (_.isString(k) && k.indexOf(prefix) === 0) {
                            if (noPrefix === true) {
                                properties[k.slice(prefix.length + 1)] = v;
                            }
                            else {
                                properties[k] = v;
                            }
                        }
                    });
                }, this);
            }
            return properties;
        }
    });

    return DashboardElementReport;
});
