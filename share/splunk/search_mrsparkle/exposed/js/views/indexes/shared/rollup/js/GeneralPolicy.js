define(
[
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'views/indexes/shared/rollup/js/AddSummary',
    'views/indexes/shared/rollup/js/Configuration',
    'views/indexes/shared/rollup/GeneralPolicy.pcss'
],
function(
    $,
    _,
    module,
    BaseView,
    AddSummary,
    Configuration,
    css
){
    return BaseView.extend( /** @lends views.GeneralPolicy.prototype */ {
        moduleId: module.id,
        className: 'general-policy',
        /**
         * @constructor
         * @memberOf views
         * @name GeneralPolicy
         * @extends {views.BaseView}
         * @description View for displaying general policy components
         *
         * @param {Object} options
         * @param {Object} options.model The model supplied to this class
         * @param {Object} options.collection The collection supplied to this class
         */
        initialize: function(options) {
            BaseView.prototype.initialize.call(this, options);
            this.children.addSummary = new AddSummary({
                model: {
                    rollup: this.model.rollup
                },
                collection: {
                    indexes: this.collection.indexes
                }
            });
            this.children.configuration = new Configuration({
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
                'aria-label': _('General policy').t()
            });
        },
        render: function() {
            if (!this.el.innerHTML) {
                var template = _.template(this.template, {
                    _: _
                });
                this.$el.html(template);
            }
            this.children.addSummary.render().appendTo(this.$(".add-summary-placeholder"));
            this.children.configuration.render().appendTo(this.$(".rollup-configuration-placeholder"));
            return this;
        },
        template: '\
            <div class="add-summary-placeholder"></div>\
            <div class="rollup-configuration-placeholder"></div>\
        '
    });
});
