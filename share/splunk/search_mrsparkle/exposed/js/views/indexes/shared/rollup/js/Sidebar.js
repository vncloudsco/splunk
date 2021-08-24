define([
    'jquery',
    'underscore',
    'module',
    'util/indexes/Aggregations',
    'views/Base',
    'views/indexes/shared/rollup/js/TabBar',
    'views/shared/Tooltip',
    'views/indexes/shared/rollup/Sidebar.pcss'
],

function(
    $,
    _,
    module,
    Aggregations,
    BaseView,
    TabBar,
    Tooltip,
    css
) {
    return BaseView.extend({
        moduleId: module.id,
        className: 'rollup-sidebar',
        /**
         * @constructor
         * @memberOf views
         * @name Sidebar
         * @extends {views.BaseView}
         * @description View containing all components for metric rollup configuration
         *
         * @param {Object} options
         * @param {Object} options.model The model supplied to this class
         * @param {Object} options.collection The collection supplied to this class
         */
        initialize: function(options) {
            BaseView.prototype.initialize.call(this, options);
            this.children.tabBar = new TabBar({
                model: {
                    content: this.model.content,
                    rollup: this.model.rollup
                }
            });
            this.children.exceptionTooltip = new Tooltip({
                content: _('You can create exception rules only for metrics indexed in the last 24 hours.').t()
            });

            this.startListening();
        },

        startListening: function() {
            this.listenTo(this.model.content, 'change:tabIndex', this.handleTabChange);
            this.listenTo(this.model.rollup, 'change:tabs', this.render);
        },

        handleTabChange: function() {
            var tabIndex = this.model.content.get('tabIndex');
            // have to modify programatically since splunk-ui component
            // doesn't update on programatic select
            var tabs = this.model.rollup.get('tabs');
            for (var i = 0; i < tabs.length; i++) {
                var enabled = i === tabIndex;
                $($('.rollup-tab')[i]).attr('aria-selected', enabled);
                $($('.rollup-tab')[i]).attr('tabIndex', enabled ? -1 : undefined);
            }
        },

        updateAddExceptionButton: function(){
            var totalMetricsLength = this.collection.metrics.length;
            var currentMetricsLength = this.model.rollup.get('tabs').length - 1;
            var enabled = currentMetricsLength < totalMetricsLength;
            if (enabled) {
                this.$('.add-exception-rule-link').removeClass('add-exception-disabled');
                this.$('.add-exception-rule-link').attr('href', '#');
            } else {
                this.$('.add-exception-rule-link').addClass('add-exception-disabled');
                this.$('.add-exception-rule-link').removeAttr('href');
            }
        },

        events: {
            'click .add-exception-rule-link': function(e) {
                e.preventDefault();
                var modelCopy = $.extend(true, {}, this.model);
                var tabs = modelCopy.rollup.get('tabs');
                tabs.push({
                    label: _('Exception Rule').t(),
                    tabBarLabel: _('Select Metric').t(),
                    exceptionMetric: '',
                    aggregation: '',
                    exceptionItems: $.extend(true, [], this.collection.metrics.getItems()),
                    aggregationItems: Aggregations.ALL_AGGREGATIONS,
                    validMetric: true,
                    validAgg: true,
                    validAggValue: true
                });
                this.model.rollup.set({
                    tabs: tabs
                });
                this.model.content.set({
                    tabIndex: tabs.length - 1
                });

                // scroll to the bottom of the scrollbar
                var tabBarSelector = this.$('.rollup-tab-bar');
                tabBarSelector.scrollTop(tabBarSelector.prop("scrollHeight"));

                this.updateAddExceptionButton();
            }
        },

        render: function() {
            if (!this.el.innerHTML) {
                var template = _.template(this.template, {
                    _: _
                });
                this.$el.html(template);
                this.children.tabBar.render().appendTo(this.$(".roll-up-tab-bar-placeholder"));
                this.children.exceptionTooltip.render().appendTo(this.$(".add-exception-toolip-placeholder"));
            }
            this.updateAddExceptionButton();
            return this;
        },

        template: '\
            <div class="roll-up-tab-bar-placeholder"></div>\
            <div class="roll-up-tab-bar-separator"></div>\
            <div class="exception-rule-wrapper">\
                <a role="button" aria-label="Add exception rule" href="#" class="add-exception-rule-link">\
                    <%- _("+ Add Exception Rule").t() %>\
                </a>\
                <span class="add-exception-toolip-placeholder"></span>\
            </div>\
        '
    });
});
