define(
    [
        'jquery',
    	'module',
        'contrib/text!views/account/passwordchange/Master.html',
        'underscore',
        'splunk.util',
        'uri/route',
        'models/account/PasswordChange',
        'views/Base',
        'views/shared/controls/TextControl',
        'views/shared/FlashMessages',
        'views/account/passwordchange/Skip',
        'views/shared/PasswordFeedback'
    ],
    function($, module, template, _, splunkutil, route, PasswordChangeModel, BaseView, TextControlView, FlashMessagesView, SkipView, PasswordFeedbackView) {
        return BaseView.extend({
            moduleId: module.id,
            template: template,
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                this.model.passwordChange = new PasswordChangeModel({}, {loginModel: this.model.login});
                this.children.newpassword = new TextControlView({
                    model: this.model.passwordChange,
                    modelAttribute: 'newpassword',
                    elementId: 'newpassword',
                    placeholder: _('New password').t(),
                    password: true
                });
                this.children.confirmpassword = new TextControlView({
                    model: this.model.passwordChange,
                    modelAttribute: 'confirmpassword',
                    elementId: 'confirmpassword',
                    placeholder: _('Confirm new password').t(),
                    password: true
                });
                this.children.flashMessages = new FlashMessagesView({
                    model: {
                        login: this.model.login,
                        user: this.model.user,
                        passwordChange: this.model.passwordChange
                    },
                    template: '\
                        <% flashMessages.each(function(flashMessage, index){ %>\
                            <p class="error">\
                                <% if (index === 0) { %>\
                                    <svg width="24px" height="24px" viewBox="463 396 28 28" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">\
                                        <defs>\
                                            <circle id="path-1" cx="12" cy="12" r="12"></circle>\
                                            <mask id="mask-2" maskContentUnits="userSpaceOnUse" maskUnits="objectBoundingBox" x="0" y="0" width="24" height="24" fill="white">\
                                                <use xlink:href="#path-1"></use>\
                                            </mask>\
                                        </defs>\
                                        <g id="Group-2" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd" transform="translate(465.000000, 398.000000)">\
                                            <use class="stroke-svg" id="Oval-5" mask="url(#mask-2)" stroke-width="3" xlink:href="#path-1"></use>\
                                            <path class="fill-svg" d="M10.2194542,7.75563395 C10.098253,6.78602409 10.7902713,6 11.7661018,6 L12.2338982,6 C13.2092893,6 13.902295,6.7816397 13.7805458,7.75563395 L13.2194542,12.244366 C13.098253,13.2139759 12.209547,14 11.2294254,14 L12.7705746,14 C11.7927132,14 10.902295,13.2183603 10.7805458,12.244366 L10.2194542,7.75563395 Z" id="Rectangle-64"></path>\
                                            <circle class="fill-svg" id="Oval-2" cx="12" cy="17" r="2"></circle>\
                                        </g>\
                                    </svg>\
                                <% } %>\
                                <%= flashMessage.get("html") %>\
                            </p>\
                        <% }); %>\
                    '
                });
                this.children.skip = new SkipView({
                    model: {
                        application: this.model.application,
                        login: this.model.login
                    }
                });
            },
            events: {
                'submit form': function(e) {
                    e.preventDefault();
                    if (!this.model.passwordChange.isValid(true)) {
                        e.preventDefault();
                        return;
                    }
                    //optional first time run password change for authenticated user
                    if (!this.model.user.isNew()) {
                        this.model.user.entry.content.set('password', this.model.passwordChange.get('newpassword'));
                        this.model.user.save({}, {
                            headers: {
                                'X-Splunk-Form-Key': splunkutil.getFormKey()
                            }
                        });
                    //force password on unauthenticated user (operate on /account/login resource)
                    } else {
                        this.model.login.save({
                            cval: this.model.session.entry.content.get('cval'),
                            return_to: this.model.application.get('return_to'),
                            username: this.model.login.get('username'),
                            new_password: this.model.passwordChange.get('newpassword'),
                            set_has_logged_in: !this.model.session.entry.content.get('hasLoggedIn')
                        });
                    }
                },
                'input #newpassword': function(e) {
                    var curValue = $(e.currentTarget).val();
                    // valResults is a dictionary of whether each criteria passes or not
                    var valResults = this.validatePassword(curValue);
                    // then pass what onInputChange returns to PasswordFeedbackView to change the classes and color
                    this.children.passwordFeedbackView.onInputChange(valResults);
                    // if user decides not to set optional password and clears newpassword field, remove mismatch error
                    var confirmPass = $("#confirmpassword").val();
                    if (curValue == confirmPass) {
                        this.children.passwordFeedbackView.onPasswordMatch();
                    }
                },
                'focus #confirmpassword': function(e) {
                    var curValue = $("#newpassword").val();
                    var valResults = this.validatePassword(curValue);
                    this.children.passwordFeedbackView.onRemoveFocus(valResults);
                },
                'input #confirmpassword': function(e) {
                    var newPass = $("#newpassword").val();
                    var confirmPass = $(e.currentTarget).val();
                    if (newPass == confirmPass) {
                        this.children.passwordFeedbackView.onPasswordMatch();
                    }
                },
                'blur #confirmpassword': function(e) {
                    var newPass = $("#newpassword").val();
                    var confirmPass = $(e.currentTarget).val();
                    if (newPass == "" && confirmPass == "") {
                        this.children.passwordFeedbackView.resetIcons();
                    }
                    (newPass != confirmPass) ? this.children.passwordFeedbackView.onPasswordMismatch() : this.children.passwordFeedbackView.onPasswordMatch();
                }
            },
            validatePassword: function(value) {
                var validationResults = {
                    passLengthReq: (value.length >= this.model.login.get('minPasswordLength')),
                    passDigitReq: (value.replace(/[^0-9]/g,"").length >= this.model.login.get('minPasswordDigit')),
                    passLowercaseReq: (value.replace(/[^a-z]/g, "").length >= this.model.login.get('minPasswordLowercase')),
                    passUppercaseReq: (value.replace(/[^A-Z]/g, "").length >= this.model.login.get('minPasswordUppercase')),
                    passSpecialReq: (value.replace(/[^!-/;-@\[-`{-~]/g, "").length >= this.model.login.get('minPasswordSpecial'))
                };
                return validationResults;
            },
            visibility: function() {
                if (!this.model.login.isPasswordChangeRequired()) {
                    this.children.skip.render().$el.show();
                    this.children.skip.$el.removeClass('hidden');
                } else {
                    this.children.skip.render().$el.hide();
                    this.children.skip.$el.addClass('hidden');
                }
            },
            show: function() {
                this.children.passwordFeedbackView = new PasswordFeedbackView({
                    firstTimeLogin: true,
                    minPasswordLength: this.model.login.get("minPasswordLength"),
                    minPasswordDigit: this.model.login.get("minPasswordDigit"),
                    minPasswordLowercase: this.model.login.get("minPasswordLowercase"),
                    minPasswordUppercase: this.model.login.get("minPasswordUppercase"),
                    minPasswordSpecial: this.model.login.get("minPasswordSpecial")
                });
                this.visibility();
                this.$el.show();
                this.children.passwordFeedbackView.render().appendTo(this.$el);
                this.children.newpassword.focus();
            },
            render: function() {
                var html = this.compiledTemplate({
                    _: _,
                    model: {
                        application: this.model.application,
                        session: this.model.session,
                        login: this.model.login,
                        user: this.model.user,
                        passwordChange: this.model.passwordChange
                    },
                    route: route
                });
                this.$el.html(html);
                this.visibility();
                this.children.newpassword.render().insertBefore(this.$('input[type=submit]'));
                this.children.confirmpassword.render().insertBefore(this.$('input[type=submit]'));
                this.children.skip.render().appendTo(this.$el);
                this.children.flashMessages.render().appendTo(this.$el);
                return this;
            }
        });
    }
);
