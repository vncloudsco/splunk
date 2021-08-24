define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    './HealthTitle.pcssm'
],
function(
    $,
    _,
    module,
    BaseView,
    css
){
    return BaseView.extend({
        moduleId: module.id,
        css: css,
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
        },

        render: function() {
            var html = this.compiledTemplate({
                css: css
            });

            this.$el.html(html);
            return this;
        },
        template: '\
        <span class="<%- css.healthTitle %>" data-title-role="health-title">\
            <%- _("Health Status of Splunkd").t() %>\
        </span>\
        '
    });
});
