define(
[
    'jquery',
    'underscore',
    'module',
    'views/Base',
    '../BaseToken.pcss'
],
function(
    $,
    _,
    module,
    BaseView,
    TokenIcon,
    css
){
    /**
     * @constructor
     * @memberOf views
     * @name BaseToken
     * @extends {views.BaseView}
     * @description Generic view for creating tokens
     *
     * @param {Object} options
     * @param {String} options.model The model supplied to this component
     */
    return BaseView.extend( /** @lends views.BaseToken.prototype */ {
        moduleId: module.id,
        initialize: function(options) {
            if (options.inline) {
                this.className = 'inline';
            }
            BaseView.prototype.initialize.call(this, arguments);
            options = options || {};
            _(options).defaults(this.defaultOptions);
        },
        render: function() {
            if (!this.el.innerHTML) {
                var icons = this.model.content.get('icons');
                var iconsExist = icons && icons.length;
                var template = _.template(this.template, {
                    _: _,
                    text: this.model.content.get('text'),
                    iconsClass: iconsExist ? 'icons' : 'no-icons'
                });
                this.$el.html(template);
                if (icons) {
                    for (var i = 0; i < icons.length; i++) {
                        this.$('.tokens').append(icons[i].render().el);
                    }
                }
            }
            return this;
        },
        template: '\
                <span class="token-container <%- iconsClass %>">\
                    <span class="text"><%- _(text).t() %></span>\
                    <span class="tokens"></span>\
                </span>\
        '
    });
});
