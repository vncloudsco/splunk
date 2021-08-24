/**
 * Created by ykou on 1/22/15.
 */
define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'splunk_monitoring_console/views/overview/distributed_mode/components/ProgressBar',
    'contrib/text!splunk_monitoring_console/views/overview/distributed_mode/components/LicenseUsageSection.html'
], function(
    $,
    _,
    module,
    BaseView,
    ProgressBarView,
    Template
) {
    /**
     * Resource Usage section.
     * This is basically a wrapper for the CPU and Memory viz bar.
     *
     * @param {SearchManager}   searchManager           - search manager
     * @param {Array of Strings} searchResultFieldName  - two strings: first is for the percentage,
     *                                                              second is for the afterLabel
     * @param {string}          TOOLTIP (optional)
     */
    return BaseView.extend({
        moduleId: module.id,
        className: 'dmc-single-values-section',
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);

            this.children.usage = new ProgressBarView({
                searchManager: this.options.searchManager,
                searchResultFieldName: this.options.searchResultFieldName,
                BEFORE_LABEL: _('Today').t(),
                drilldownHref: 'license_usage_today',
                TOOLTIP: this.options.DMC_DOC
            });
        },
        render: function() {
            this.$el.html(this.compiledTemplate());
            this.$('.dmc-license-usage').append(this.children.usage.render().$el);
            return this;
        },
        template: Template
    });
});