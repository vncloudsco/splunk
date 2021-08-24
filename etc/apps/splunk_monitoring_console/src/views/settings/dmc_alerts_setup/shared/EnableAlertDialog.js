/**
 * @author atruong
 * @date 4/24/15
 *
 * Confirmation dialog for enabling a preconfigured dmc alert
 */

define([
	'jquery',
	'underscore',
	'backbone',
	'module',
	'models/shared/LinkAction',
	'views/shared/FlashMessages',
	'views/shared/Modal',
    'util/splunkd_utils'
], function (
	$,
	_,
	Backbone,
	module,
	LinkAction,
	FlashMessages,
	Modal,
    splunkDUtils
) {

    var licenseUsageSearchStringForCloud = '| rest splunk_server_group=dmc_group_license_master services/licenser/usage/license_usage | \
        fields slaves_usage_bytes, quota | eval usedGB=round(slaves_usage_bytes/1024/1024/1024,3) | \
        eval totalGB=round(quota/1024/1024/1024,3) | eval percentage=round(usedGB / totalGB, 3)*100 | \
        fields percentage, usedGB, totalGB | where percentage > 90';

	return Modal.extend({
		moduleId: module.id,
		className: Modal.CLASS_NAME,

		initialize: function (options) {
			Modal.prototype.initialize.apply(this, arguments);
			this.children.flashMessagesView = new FlashMessages({ model: { alert: this.model.alert } });
			this.alertName = this.model.alert.entry.get('name');
		},

		events: $.extend({}, Modal.prototype.events, {
			'click .modal-btn-enable': function(e) {
				e.preventDefault();

                // Cloud admins (sc_admin) don't have license_edit capabilities so they can't access normal licensing endpoints
                // The /services/licenser/usage endpoint is only available on splunk 6.3+, and so for backward compatibility, we only use this endpoint on the Cloud.
                if ((this.alertName === 'DMC Alert - Total License Usage Near Daily Quota') && (this.model.serverInfo.isCloud())) {
                    this.model.alert.entry.content.set({'search': licenseUsageSearchStringForCloud});
                }

				this.model.alert.entry.content.set('disabled', false);
				this.model.alert.save().done(_(function () {
                    this.updateEnableFailedMessage(false);
					this.hide();
				}).bind(this)).fail(_(function () {
                    this.updateEnableFailedMessage(true);
                }).bind(this));
			}
		}),

		updateEnableFailedMessage: function(failed) {
	        if (failed) {
	            var errMessage = _('Failed to enable alert.').t();
	            this.children.flashMessagesView.flashMsgHelper.addGeneralMessage('enable_failed',
	                {
	                    type: splunkDUtils.ERROR,
	                    html: errMessage
	                });
	        } else {
	            this.children.flashMessagesView.flashMsgHelper.removeGeneralMessage('enable_failed');
	        }
	    },

		render: function () {
            var BUTTON_ENABLE = '<a href="#" class="btn btn-primary modal-btn-enable modal-btn-primary">' + _('Enable').t() + '</a>';
			this.$el.html(Modal.TEMPLATE);
			this.$(Modal.HEADER_TITLE_SELECTOR).html( _('Enable Alert').t());
			this.$(Modal.BODY_SELECTOR).show();
			this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);
			this.$(Modal.BODY_FORM_SELECTOR).html(_(this.dialogFormBodyTemplate).template({alertName: this.alertName}));
			this.children.flashMessagesView.render().appendTo(this.$('.flash-messages-view-placeholder'));
			this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
			this.$(Modal.FOOTER_SELECTOR).append(BUTTON_ENABLE);
			return this;
		},

		dialogFormBodyTemplate: '\
			<div class="flash-messages-view-placeholder"></div>\
			<p class="confirmation-text"><%= _("Are you sure you want to enable the following alert?").t() %></p>\
			<p class="alert-name-text"><i><%= alertName %></i></p>\
		'
	});
});