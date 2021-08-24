define(
    [
        'module',
        'jquery',
        'underscore',
        'views/Base',
        'views/dashboard/editor/addcontent/preview/BasePreview',
        'views/dashboard/editor/addcontent/preview/content/ReportContent',
        'controllers/dashboard/helpers/ReportModelHelper'
    ],
    function(module,
             $,
             _,
             BaseView,
             BasePreview,
             ReportContent,
             ReportModelHelper
    ) {
        return BasePreview.extend({
            moduleId: module.id,
            className: 'report-preview content-preview',
            initialize: function(options) {
                BasePreview.prototype.initialize.apply(this, arguments);
                this.model = _.extend({}, this.model);
                this.collection = _.extend({}, this.collection);
            },
            _getPayload: function() {
                return {
                    type: 'new:element-report',
                    payload: {
                        "type": "panel",
                        "settings": {},
                        "children": [
                            {
                                "type": this._getType(),
                                "settings": {},
                                "children": [
                                    {
                                        "type": "saved-search",
                                        "settings": {
                                            "cache": "scheduled",
                                            "ref": this.model.report.entry.get('name')
                                        },
                                        "children": []
                                    }
                                ],
                                "reportContent": _.extend(
                                    { "dashboard.element.title": this.model.report.entry.get('name') },
                                    this.getCustomVizNameAttribute(),
                                    ReportModelHelper.getDisabledDrilldownAttribute(this.model.report.entry.content.toJSON({tokens: true}))
                                )
                            }
                        ]
                    }
                };
            },
            _getType: function() {
                return this.model.report.entry.content.get('dashboard.element.viz.type');
            },
            _isCustomViz: function() {
                return this._getType() === 'viz';
            },
            getCustomVizNameAttribute: function() {
                // this is only useful for custom viz, it will do nothing for other viz types.
                var attr = 'display.visualizations.custom.type';
                var pair = {};

                if (this._isCustomViz()) {
                    pair[attr] = this.model.report.entry.content.get(attr, { token: true });
                }

                return pair;
            },
            _getTitle: function() {
                return _("Preview").t();
            },
            _getPreview: function() {
                return new ReportContent({
                    model: this.model,
                    collection: this.collection
                });
            }
        });
    });
