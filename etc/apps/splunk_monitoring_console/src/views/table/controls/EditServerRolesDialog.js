define(
	[
		'jquery',
		'underscore',
		'module',
		'backbone',
		'collections/shared/FlashMessages',
		'splunk_monitoring_console/models/Peer',
		'views/shared/Modal',
		'views/shared/controls/ControlGroup',
		'splunk_monitoring_console/views/table/controls/ConfirmationDialog',
		'splunk_monitoring_console/views/table/controls/FailureDialog',
		'views/shared/FlashMessagesLegacy'
	],
	function(
		$,
		_,
		module,
		Backbone,
		FlashMessagesCollection,
		PeerModel,
		ModalView,
		ControlGroupView,
		ConfirmationDialog,
		FailureDialog,
		FlashMessagesView
	) {

		return ModalView.extend({
			moduleId: module.id,
			initialize: function(options) {
				ModalView.prototype.initialize.apply(this, arguments);

				this.model.working = new Backbone.Model();
				this.collection = this.collection || {};
				this.collection.flashMessages = new FlashMessagesCollection();

				var canonicalRoles = PeerModel.getAllPrimaryRoles();
				_.each(canonicalRoles, function(roleId) {
					this.model.working.set(
						roleId, 
						_.contains(
							this.model.peer.entry.content.get('active_server_roles'), 
							roleId
						)
					);
					this.children[roleId + 'Field'] = new ControlGroupView({
						controlType: 'SyntheticCheckbox',
						controlOptions: {
							modelAttribute: roleId,
							model: this.model.working
						},
						label: this.model.peer.getServerRoleI18n(roleId)
					});
				}, this);


				this.children.flashMessage = new FlashMessagesView({ 
					collection: this.collection.flashMessages
				});

			},

			events: $.extend({}, ModalView.prototype.events, {
				'click .btn-primary': function(e) {
					e.preventDefault();
					var dialog = this;
					var uiRoles = this.model.working.toJSON();
					var roles = [];

					this.collection.flashMessages.reset();

					_.each(_.keys(uiRoles), function(uiRoleKey) {
						if (uiRoles[uiRoleKey]) {
							roles.push(uiRoleKey);
						}
					});

					var error = this.model.peer.entry.content.validate({
						'active_server_roles': roles
					});

					if (error) {
						this.collection.flashMessages.reset([{
							type: 'error',
							html: error
						}]);
					} else {
						var oldRoles = this.model.peer.entry.content.get('active_server_roles');
						this.model.peer.entry.content.set('active_server_roles', roles);

						$(e.target).prop('disabled', true);
						this.model.peer.save().done(function() {
							this.model.state.set('changesMade', true);
							dialog.hide();
							var confirmationDialog = new ConfirmationDialog({
		            			message: _("Your server roles have updated successfully.").t()
		            		}).render();
		            		$('body').append(confirmationDialog.el);
		            		confirmationDialog.show();
						}.bind(dialog)).fail(function() {
							dialog.hide();
							this.model.peer.entry.content.set('active_server_roles', oldRoles);
                    		var failureDialog = new FailureDialog().render();
                    		$('body').append(failureDialog.el);
                       		failureDialog.show();
						}.bind(dialog));
					}
				}
			}),
	        render : function() {
	            this.$el.html(ModalView.TEMPLATE);
	            this.$(ModalView.HEADER_TITLE_SELECTOR).html(_("Edit Server Roles").t());
	            this.$(ModalView.BODY_SELECTOR).prepend(this.children.flashMessage.render().el);
				this.$(ModalView.BODY_SELECTOR).append('<h4 class="instance-name">' + _.escape(this.model.peer.entry.content.get('peerName')) + '</h4>');
	            this.$(ModalView.BODY_SELECTOR).append(ModalView.FORM_HORIZONTAL);
	            _.each(_.keys(this.children), function(childKey) {
	            	if (childKey !== 'flashMessage') {
	            		this.$(ModalView.BODY_FORM_SELECTOR).append(this.children[childKey].render().el);
	            	}
	            }, this);
	            this.$(ModalView.FOOTER_SELECTOR).append(ModalView.BUTTON_CANCEL);
	            this.$(ModalView.FOOTER_SELECTOR).append(ModalView.BUTTON_SAVE);
	            return this;
	        }
		});
	}
);