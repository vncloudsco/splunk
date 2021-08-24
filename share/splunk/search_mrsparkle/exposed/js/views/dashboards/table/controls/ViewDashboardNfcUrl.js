define([
        'underscore',
        'jquery',
        'module',
        'views/shared/Modal',
        'views/shared/controls/ControlGroup'
    ],

    function(
        _,
        $,
        module,
        Modal,
        ControlGroup
    )
    {
        return Modal.extend({
            moduleId: module.id,
            className: 'modal view-dashboard-qr-code',

            initialize: function () {
                Modal.prototype.initialize.apply(this, arguments);
                var idParts = this.model.dashboardId.split('/');
                this.model.nfcUrl = 'https://spl.mobi/s1/' +
                    idParts[idParts.length-5] + '/' +
                    idParts[idParts.length-4] + '/' +
                    idParts[idParts.length-1];
            },
            render: function () {
                this.$el.html(Modal.TEMPLATE);
                this.$(Modal.HEADER_TITLE_SELECTOR).html(_("Get Dashboard NFC URL").t());
                this.$(Modal.BODY_SELECTOR).append('<p>' + this.model.nfcUrl + '</p>');
                return this;
            }
        });
    });
