define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'contrib/text!views/monitoringconsole/splunk_health_check/ProgressBar.html',
    'views/monitoringconsole/splunk_health_check/ProgressBar.pcss',
    'splunk.util'
], function(
    $,
    _,
    module,
    BaseView,
    Template,
    css,
    splunkUtils
) {
    return BaseView.extend({
        moduleId: module.id,
        template: Template,
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);

            this.listenTo(this.model, 'change:checked change:total', this.render);
        },
        render: function() {
            var current = this.model.get('checked');
            var total = this.model.get('total');
            var ratio = total ? current / total * 100 : 0;
            var percent = ratio < 100 ? ratio : 100;
            this.$el.attr('aria-live', 'assertive');
            this.$el.attr('role', 'status');
            this.$el.html(this.compiledTemplate({
                percent: percent,
                splunkUtils: splunkUtils
            }));
            return this;
        }
    });
});