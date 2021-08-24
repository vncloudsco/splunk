define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    './Title.pcssm'
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
            this.model.serverInfo.on('change reset', function() {
                this.render();
            }, this);
        },

        render: function() {
            var html = this.compiledTemplate({
                css: css
            });

            this.$el.html(html);
            return this;
        },
        template: '<span data-title-role="about" tabindex="0" aria-label="About Page">About</span>'
    });
});
