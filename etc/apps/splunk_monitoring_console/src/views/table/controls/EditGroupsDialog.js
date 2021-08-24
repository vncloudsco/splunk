define(
	[
		'jquery',
		'underscore',
		'backbone',
		'module',
		'collections/shared/FlashMessages',
		'views/shared/Modal',
		'views/shared/controls/ControlGroup',
	    'splunk_monitoring_console/views/table/controls/MultiInputControl',
	    'splunk_monitoring_console/views/table/controls/ConfirmationDialog',
	    'splunk_monitoring_console/views/table/controls/FailureDialog',
	    'views/shared/FlashMessagesLegacy'
	],
	function(
		$,
		_,
		Backbone,
		module,
		FlashMessagesCollection,
		Modal,
		ControlGroup,
		MultiInputControl,
		ConfirmationDialog,
		FailureDialog,
		FlashMessagesView
	) {
		return Modal.extend({
			moduleId: module.id,
			initialize: function() {
				Modal.prototype.initialize.apply(this, arguments);

				this.model.working = new Backbone.Model({
					'tags': this.model.peer.entry.content.get('tags').join(',')
				});
				this.collection = this.collection || {};
				this.collection.flashMessages = new FlashMessagesCollection();

				this.groupTagsInputControl = new MultiInputControl({
					model: this.model.working,
					collection: this.collection.peers,
					modelAttribute: 'tags',
					attributeType: 'array',
					collectionMethod: 'getAllTags',
					placeholder: _('Choose groups').t()
				});

				this.children.groupTags = new ControlGroup({
					label: _("Group Tags").t(),
					controlClass: 'controls-block',
					controls: [this.groupTagsInputControl]
				});

				this.children.flashMessage = new FlashMessagesView({
					collection: this.collection.flashMessages
				});

			},
			events: $.extend({}, Modal.prototype.events, {
	            'click .btn-primary': function(e) {
	            	e.preventDefault();

	            	var tags = this.model.working.get('tags');
	            	tags = $.trim(tags) ? tags.split(',') : [];

	            	this.collection.flashMessages.reset();
	            	var error = this.model.peer.entry.content.validate({
	            		'tags': tags
	            	});

	            	if (error) {
	            		this.collection.flashMessages.reset([{
	            			type: 'error',
	            			html: error
	            		}]);
	            	} else {
	            		var oldTags = this.model.peer.entry.content.get('tags');
		            	this.model.peer.entry.content.set('tags', tags);

		            	$(e.target).prop('disabled', true);
		            	this.model.peer.save().done(function() {
		            		this.model.state.set('changesMade', true);
		            		
		            		this.hide();
		            		var confirmationDialog = new ConfirmationDialog({
		            			message: _("Your custom groups have updated successfully.").t()
		            		}).render();
		            		$('body').append(confirmationDialog.el);
		            		confirmationDialog.show();
		            	}.bind(this)).fail(function() {
		      				this.hide();

		            		this.model.peer.entry.content.set('tags',oldTags);
		            		var dialog = new FailureDialog().render();
		            		$('body').append(dialog.el);
                        	dialog.show();
		            	}.bind(this));
		            }
	            }
	        }),
			render: function() {
	            this.$el.html(Modal.TEMPLATE);
	            this.$(Modal.HEADER_TITLE_SELECTOR).html(_("Edit Group Tags").t());
	            this.$(Modal.BODY_SELECTOR).prepend(this.children.flashMessage.render().el);
	            this.$(Modal.BODY_SELECTOR).append('<h4 class="instance-name">' + _.escape(this.model.peer.entry.content.get('peerName')) + '</h4>');
	            this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);
	            this.$(Modal.BODY_FORM_SELECTOR).append(this.children.groupTags.render().el);
	            this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
	            this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_SAVE);
	            return this;
	        }
		});
	}
);