define(
	[
		'jquery',
		'underscore',
		'module',
		'backbone',
		'collections/shared/FlashMessages',
		'views/shared/Modal',
		'views/shared/FlashMessagesLegacy',
		'splunk.config',
		'uri/route'
	],
	function(
		$,
		_,
		module,
		Backbone,
		FlashMessagesCollection,
		ModalView,
		FlashMessagesView,
		config,
		route
	) {

		return ModalView.extend({
			moduleId: module.id,
			initialize: function() {
				ModalView.prototype.initialize.apply(this, arguments);

				this.collection = this.collection || {};
				this.collection.flashMessages = new FlashMessagesCollection();

				this.children.flashMessage = new FlashMessagesView({ 
					collection: this.collection.flashMessages
				});

				this.collection.flashMessages.reset(_.map(this.options.messages, function(message) {
	            	return {
	            		type: 'warning',
	            		html: message
	            	};
	            }));
			},
			events: $.extend({}, ModalView.prototype.events, {
				'click .btn-primary': function(e) {
					e.preventDefault();
					this.hide();
					this.model.confirm.trigger('confirmed');
				}
			}),
	        render: function() {
	        	var root = (config.MRSPARKLE_ROOT_PATH.indexOf("/") === 0 ? 
                    config.MRSPARKLE_ROOT_PATH.substring(1) : 
                    config.MRSPARKLE_ROOT_PATH
                );

	            this.$el.html(ModalView.TEMPLATE);
	            this.$(ModalView.HEADER_TITLE_SELECTOR).html(_("Are you sure?").t());
	            this.$(ModalView.HEADER_SELECTOR).append("<div><p style='font-size: 10px;'><a style='font-weight:bold;' href='"+route.docHelp(root, config.LOCALE, "app.splunk_monitoring_console.warnings")+"' target='_blank'>"+_("Learn more").t()+"</a>"+_(" about warnings.").t()+"</p></div>");

	            this.$(ModalView.BODY_SELECTOR).prepend(this.children.flashMessage.render().el);
	            this.$(ModalView.FOOTER_SELECTOR).append(ModalView.BUTTON_CANCEL);
	            this.$(ModalView.FOOTER_SELECTOR).append(ModalView.BUTTON_SAVE);

	            this.$('.btn-primary').text(_("Save").t());
	            this.$('.btn.cancel').text(_("Continue editing").t());

	            this.$(ModalView.HEADER_SELECTOR).css({'padding':'15px 0 10px 20px'});
	            return this;
	        }
		});
	}
);