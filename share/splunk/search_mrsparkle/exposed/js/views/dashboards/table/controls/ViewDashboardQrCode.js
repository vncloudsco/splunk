define([
        'underscore',
        'jquery',
        'splunk.util',
        'module',
        'views/shared/Modal',
        './ViewDashboardQrCode.pcssm'
    ],

    function(
        _,
        $,
        splunkUtil,
        module,
        Modal,
        css
    )
    {
        return Modal.extend({
            moduleId: module.id,
            className: 'modal viewDashboardQrCode',

            initialize: function () {
                Modal.prototype.initialize.apply(this, arguments);
                this.model.qrUrl = splunkUtil.make_full_url('/splunkd/__raw/services/qr/code_for_dashboard/dashboard_qr.');
                var that = this;

                this.model.qrCodeFileTypes = [];
                var fileTypesUrl = splunkUtil.make_full_url('/splunkd/__raw/services/qr/file_types');

                this.model.fileTypesDeferred = $.ajax(fileTypesUrl).then(function(res) {
                    that.model.qrCodeFileTypes = res;
                });

                this.model.isDashboardMobileCompatible = true;
                var compatibleUrl = splunkUtil.make_full_url('/splunkd/__raw/services/qr/is_dashboard_mobile_compatible',
                    {dashboard_id: this.model.dashboardId});

                this.model.compatibleDeferred = $.ajax(compatibleUrl).then(function(res) {
                    that.model.isDashboardMobileCompatible = res.valid;
                }).fail(function() {
                    that.model.isDashboardMobileCompatible = false;
                });

                $.when(this.model.compatibleDeferred, this.model.fileTypesDeferred).done(function() {
                    that.render();
                });
            },
            render: function () {
                this.$el.html(Modal.TEMPLATE);
                this.$(Modal.HEADER_TITLE_SELECTOR).html(_("Get Dashboard QR Code").t());
                this.$(Modal.FOOTER_SELECTOR).css('padding', '0');

                if (!this.model.isDashboardMobileCompatible) {
                    this.$(Modal.BODY_SELECTOR).append('<div class="alert alert-error"><i class="icon-alert"></i>' +
                        _("This dashboard is not compatible with Splunk Mobile at this time").t() + '</div>');
                    return this;
                }

                var qrTargetUrl = encodeURIComponent('https://spl.mobi:8000' + this.model.dashboardId);
                this.$(Modal.BODY_SELECTOR).append('<div class="' + css.qrBox + '" ><div class="' + css.qrImageBox + '" ><img class="' + css.qrImage + '" src="' +
                    this.model.qrUrl + 'png?dashboard_id=' + qrTargetUrl + '" \></div><div class="' + css.downloadButtonsBox + '" ></div></div>');

                var that = this;
                this.model.qrCodeFileTypes.forEach(function(fileType) {
                    that.$('.' + css.downloadButtonsBox).first().append('<a href="' + that.model.qrUrl + fileType.extension + '?dashboard_id='
                        + qrTargetUrl + '" class="btn ' + css.downloadButton + '" download><strong>' + _("Export as " + fileType.name).t() + '</strong></a>');
                });

                return this;
            }
        });

    });
