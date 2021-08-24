define(
    [
        'underscore',
        'jquery',
        'module',
        'views/shared/Modal'
    ],
    function(
        _,
        $,
        module,
        Modal
        ) {
        return Modal.extend({
            moduleId: module.id,

            initialize: function() {
                Modal.prototype.initialize.apply(this, arguments);
            },

            render: function() {
                var headerDOM = this.options.headerText ? '<h3>' + this.options.headerText + '</h3>' : '';

                this.$el.html(Modal.TEMPLATE);

                this.$(Modal.HEADER_SELECTOR).html(headerDOM);
                this.$(Modal.BODY_SELECTOR).html(this.options.message);
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_OK);

                return this;
            }
        });
    }
);
