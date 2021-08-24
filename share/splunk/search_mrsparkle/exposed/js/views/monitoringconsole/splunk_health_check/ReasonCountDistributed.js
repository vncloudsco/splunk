/**
 * Created by claral on 6/21/16.
 */
define(
[
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'views/monitoringconsole/splunk_health_check/utils',
    'contrib/text!views/monitoringconsole/splunk_health_check/ReasonCountDistributed.html',
    'views/monitoringconsole/splunk_health_check/ReasonCountDistributed.pcss',
    'views/monitoringconsole/splunk_health_check/pcss/icon-style.pcss',
    'splunk.util'
], function(
    $,
    _,
    module,
    BaseView,
    utils,
    Template,
    css,
    iconStyleCSS,
    splunkUtils
) {
    return BaseView.extend({
        moduleId: module.id,
        template: Template,
        render: function() {
            var isDone = this.model.task.isDone();
            var reasonSummary = [];
            var totalCount = 0;
            if (isDone) {
    			var reasonSummaryUnsorted = _.map(this.model.task.getReasonSummary(), function(count, severity_level) {
                    return {
                        level: severity_level,
                        count: count
                    };
                });
                // most severe level first
                reasonSummary = _.sortBy(reasonSummaryUnsorted, function(summary) {
                    return - summary.level;
                });
                totalCount = this.model.task.getResult().raw.rows.length;
            }
            this.$el.html(this.compiledTemplate({
            	reasonSummary: reasonSummary,
                totalCount: totalCount,
				isDone: isDone,
				utils: utils,
                splunkUtils: splunkUtils
            }));

            this.$('.health-tooltip-link').tooltip();

            return this;
        }
    });
});
