define(
[
    'jquery',
    'underscore',
    'module',
    'models/Base',
    'util/indexes/Aggregations',
    'views/Base',
    'views/shared/token/BaseToken',
    'views/indexes/shared/rollup/js/DimensionFilterRadioList',
    'views/indexes/shared/rollup/js/Multiselect',
    'views/indexes/shared/rollup/Configuration.pcss'
],
function(
    $,
    _,
    module,
    BaseModel,
    Aggregations,
    BaseView,
    BaseToken,
    DimensionFilterRadioList,
    Multiselect,
    css
){
    return BaseView.extend( /** @lends views.Configuration.prototype */ {
        className: 'rollup-configuration',
        moduleId: module.id,
        /**
         * @constructor
         * @memberOf views
         * @name Configuration
         * @extends {views.BaseView}
         * @description Configuration for excluded/included fields
         *
         * @param {Object} options
         * @param {Object} options.model The model supplied to this class
         */
        initialize: function(options) {
            BaseView.prototype.initialize.call(this, options);

            var generalPolicyTab = this.model.rollup.get('tabs')[0];
            var defaultAggregation = generalPolicyTab.aggregation;
            var aggregationLabel = Aggregations.aggregationLabelMap[defaultAggregation];
            var aggregationTokenModel = new BaseModel({
                text: aggregationLabel || 'Unknown Aggregation',
                icons: []
            });
            this.children.aggregationToken = new BaseToken({
                model: {
                    content: aggregationTokenModel
                },
                inline: true
            });

            this.children.dimensionFilterRadioList = new DimensionFilterRadioList({
                model: {
                    rollup: this.model.rollup
                }
            });
            this.children.excluded = new Multiselect({
                ariaLabel: _('Dimensions multiselect').t(),
                model: {
                    content: this.model.content,
                    rollup: this.model.rollup
                }
            });
            this.setAriaAttributes();
        },
        setAriaAttributes: function() {
            this.$el.attr({
                role: 'group',
                'aria-label': _('General policy configuration').t()
            });
        },
        render: function() {
            if (!this.el.innerHTML) {
                var template = _.template(this.template, {
                    _: _
                });
                this.$el.html(template);
            }
            this.$('.list-type-placeholder').append(this.children.dimensionFilterRadioList.render().el);
            this.$('.list-items-placeholder').append(this.children.excluded.render().el);
            this.$('.aggregation-value').append(this.children.aggregationToken.render().el);
            return this;
        },
        template: '\
            <div class="aggregration-header"><%- _("Aggregation:").t() %></div>\
            <span class="rollup-help-text"><%- _("The aggregation method to apply to each summarized metric data point. Applies to all metrics in this policy that do not have an exception rule.").t() %></span>\
            <div class="aggregation-value"></div>\
            <div class="list-type-placeholder"></div>\
            <span class="rollup-help-text"><%- _("Lists dimensions indexed over the last 24 hours.").t() %></span>\
            <div class="config-item list-items-placeholder"></div>\
        '
    });
});
