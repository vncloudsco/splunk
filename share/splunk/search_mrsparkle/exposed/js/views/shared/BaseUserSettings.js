define([
        'jquery',
        'underscore',
		'splunk.util',
        'backbone',
        'module',
		'views/shared/PasswordFeedback',
        'views/Base',
        'views/shared/controls/ControlGroup',
		'./BaseUserSettings.pcss'
    ],
    function(
        $,
        _,
		splunkutil,
        Backbone,
        module,
        PasswordFeedbackView,
        Base,
		ControlGroup,
		css
    ) {
        return Base.extend({
            moduleId: module.id,

			events: {
				'input #password': function(e) {
                    var curValue = $(e.currentTarget).val();
                    // valResults is a dictionary of whether each criteria passes or not
                    var valResults = this.model.splunkAuth.validatePassword(curValue);
                    // then pass what onInputChange returns to PasswordFeedbackView to change the classes and color 
                    this.children.passwordFeedbackView.onInputChange(valResults);
                    // if user decides not to set optional password and clears password field, remove mismatch error
                    var confirmPass = $("#confirmpassword").val();
                    if (curValue == confirmPass) {
                        this.children.passwordFeedbackView.onPasswordMatch();
                    }
                },
                'focus #confirmpassword': function(e) {
                    var curValue = $("#password").val();
                    var valResults = this.model.splunkAuth.validatePassword(curValue);
                    this.children.passwordFeedbackView.onRemoveFocus(valResults);
                },
                'input #confirmpassword': function(e) {
                    var newPass = $("#password").val();
                    var confirmPass = $(e.currentTarget).val();
                    if (newPass == confirmPass) {
                        this.children.passwordFeedbackView.onPasswordMatch();
                    }
                },
                'blur #confirmpassword': function(e) {
                    var newPass = $("#password").val();
                    var confirmPass = $(e.currentTarget).val();
                    if (newPass == "" && confirmPass == "") {
                        this.children.passwordFeedbackView.resetIcons();
                    }
                    (newPass != confirmPass) ? this.children.passwordFeedbackView.onPasswordMismatch() : this.children.passwordFeedbackView.onPasswordMatch();
                }
            },
			
            initialize: function(options) {
                Base.prototype.initialize.call(this, options);
				
                this.renderDfd = new $.Deferred();
				
				this.children.entityDesc = new ControlGroup({
                    controlType: 'Text',
                    controlOptions: {
                        modelAttribute: 'realname',
                        model: this.model.entity.entry.content,
                        placeholder: _('optional').t()
                    },
                    controlClass: 'controls-block',
                    label: _('Full name').t(),
                    required: false
                });

                this.children.entityEmail = new ControlGroup({
                    controlType: 'Text',
                    controlOptions: {
                        modelAttribute: 'email',
                        model: this.model.entity.entry.content,
                        placeholder: _('optional').t()
                    },
                    controlClass: 'controls-block',
                    label: _('Email address').t(),
                    required: false
                });

                this.children.oldPassword = new ControlGroup({
                    controlType: 'Text',
                    controlOptions: {
                        model: this.model.entity.entry.content,
                        modelAttribute: 'oldpassword',
                        elementId: 'oldpassword',
                        placeholder: _('Old password').t(),
                        password: true
                    },
                    controlClass: 'controls-block',
                    label: _('Old password').t()
                });
				
				this.children.password = new ControlGroup({
                    controlType: 'Text',
                    controlOptions: {
                        model: this.model.entity.entry.content,
                        modelAttribute: 'password',
                        elementId: 'password',
                        placeholder: _('New password').t(),
                        password: true
                    },
                    controlClass: 'controls-block',
                    label: _('Set password').t()
                });

                this.children.confirmPassword = new ControlGroup({
                    controlType: 'Text',
                    controlOptions: {
                        model: this.model.entity.entry.content,
                        modelAttribute: 'confirmpassword',
                        elementId: 'confirmpassword',
                        placeholder: _('Confirm new password').t(),
                        password: true
                    },
					label: _('Confirm password').t(),
                    controlClass: 'controls-block'
                });

                this.children.passwordFeedbackView = new PasswordFeedbackView({
                    model: {
						splunkAuth: this.model.splunkAuth
					}
				});
            },
			
			render: function() {
				this.$el.html(this.compiledTemplate());
				this.children.entityDesc.render().replaceAll(this.$(".name-placeholder"));
				this.children.entityEmail.render().replaceAll(this.$(".email-placeholder"));
                // Since admin doesn't need to enter old password when changing other users' passwords, only show oldpassword field when
                // (1) Editing an existing user AND (2) the logged in user does not have edit user capability, or is editing their own password  
                if (!this.options.isNew && 
                    !this.options.isClone && 
                    (!this.options.canEditUser || this.model.application.get('owner') == this.model.entity.entry.get('name'))) {
                    this.children.oldPassword.render().replaceAll(this.$(".oldPassword-placeholder"));
                }
				this.children.password.render().replaceAll(this.$(".password-placeholder"));
                this.children.confirmPassword.render().replaceAll(this.$(".confirmPassword-placeholder"));
				this.children.passwordFeedbackView.render().replaceAll(this.$(".passwordReqSection-placeholder"));
				return this;
			},
			
			resetFields: function() {
                this.model.entity.entry.content.unset('oldpassword');
				this.model.entity.entry.content.unset('password');
				this.model.entity.entry.content.unset('confirmpassword');
				this.children.passwordFeedbackView.resetIcons();
			},
			
			template: '\
				<div class="user-edit-form-wrapper">\
					<div class="name-placeholder"></div>\
					<div class="email-placeholder"></div>\
                    <div class="oldPassword-placeholder"></div>\
					<div class="password-placeholder"></div>\
					<div class="confirmPassword-placeholder"></div>\
					<div class="passwordReqSection-placeholder"></div>\
				</div>\
				'				
        });
    });
