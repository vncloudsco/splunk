define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'contrib/text!./Section.html',
    './Section.pcssm'
],
function(
    $,
    _,
    module,
    BaseView,
    systemMenuSectionTemplate,
    css
){
    return BaseView.extend({
        moduleId: module.id,
        template: systemMenuSectionTemplate,
        className: css.view,
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
            var itemsArray = this.model.get('items');
            itemsArray.sort(function(a,b){
                return parseInt(a.get('order'), 10) - parseInt(b.get('order'), 10);
            });
        },
        render: function() {
            var html = this.compiledTemplate({model: this.model, css: css});
            this.$el.html(html);

            return this;
        }
    });
});
