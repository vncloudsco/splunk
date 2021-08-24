define (
    [
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'views/shared/Modal'
    ],
    function(
        $,
        _,
        module,
        BaseView,
        ModalView
    ){
        return BaseView.extend({
            moduleId: module.id,
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

            },
            events: {
                'click .modal-btn-primary': function() {
                    this.trigger('closeModal');
                }
            },
            focus: function() {
                this.$('.modal-btn-primary').focus();
            },
            render: function() {
                this.$el.html(ModalView.TEMPLATE);
                this.$(ModalView.HEADER_TITLE_SELECTOR).html(_("Rebuild Failed").t());
                this.$(ModalView.BODY_SELECTOR).html(_("There was an error rebuilding the data model.  Please close this dialog and try again.").t());
                this.$(ModalView.FOOTER_SELECTOR).append(ModalView.BUTTON_CLOSE);
                return this;
            }
        });
    });