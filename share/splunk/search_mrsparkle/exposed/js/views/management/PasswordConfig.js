define(
    [
        'underscore',
        'splunk.util',
        'module', 
        'uri/route',
        'views/Base',
        'views/shared/FlashMessages',
        'views/shared/controls/ControlGroup',
        './PasswordConfig.pcss',
        'util/splunkd_utils'
    ],
    function(
        _,
        splunkUtil,
        module,
        route,
        Base,
        FlashMessagesView,
        ControlGroup,
        css,
        splunkDUtils
    ){
        return Base.extend({
            moduleId: module.id,

            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);

                var pages = (this.model.serverInfo.isLite()) ? ['authentication', 'users'] : ['password', 'management'];
                this.backUrl = route.manager(
                            this.model.application.get("root"),
                            this.model.application.get("locale"),
                            this.model.application.get("app"),
                            pages);

                this.children.minPasswordLength = new ControlGroup({
                    controlType: 'Text',
                    help: _('Must be a number between 1 and 256. For better security, we recommend a number between 8 and 256.').t(),
                    controlOptions: {
                        modelAttribute: 'minPasswordLength',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Minimum characters').t()
                });

                this.children.minPasswordDigit = new ControlGroup({
                    controlType: 'Text',
                    help: _('Minimum number of digits required.').t(),
                    controlOptions: {
                        modelAttribute: 'minPasswordDigit',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Numeral').t()
                });

                this.children.minPasswordLowercase = new ControlGroup({
                    controlType: 'Text',
                    help: _('Minimum number of lowercase letters required.').t(),
                    controlOptions: {
                        modelAttribute: 'minPasswordLowercase',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Lowercase').t()
                });

                this.children.minPasswordUppercase = new ControlGroup({
                    controlType: 'Text',
                    help: _('Minimum number of uppercase letters required.').t(),
                    controlOptions: {
                        modelAttribute: 'minPasswordUppercase',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Uppercase').t()
                });

                this.children.minPasswordSpecial = new ControlGroup({
                    controlType: 'Text',
                    help: _('Minimum number of printable ASCII characters.').t(),
                    controlOptions: {
                        modelAttribute: 'minPasswordSpecial',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Special character').t()
                });

                this.children.forceWeakPasswordChange = new ControlGroup({
                    controlType: 'SyntheticCheckbox',
                    controlOptions: {
                        modelAttribute: 'forceWeakPasswordChange',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Force existing users to change weak passwords').t()
                });

                this.children.enableExpiration = new ControlGroup({
                    controlType: 'SyntheticRadio',
                    controlOptions: {
                        modelAttribute: 'expireUserAccounts',
                        model: this.model.splunkAuth.entry.content,
                        items: [
                            {
                                label: _('Enable').t(),
                                value: true
                            },
                            {
                                label: _('Disable').t(),
                                value: false
                            }
                        ]
                    }
                });

                this.children.expirePasswordDays = new ControlGroup({
                    controlType: 'Text',
                    help: _('Number of days until a password expires.').t(),
                    controlOptions: {
                        modelAttribute: 'expirePasswordDays',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Days until password expires').t()
                });

                this.children.expireAlertDays = new ControlGroup({
                    controlType: 'Text',
                    help: _('Number of days before expiration when the warning first appears.').t(),
                    controlOptions: {
                        modelAttribute: 'expireAlertDays',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Expiration alert in days').t()
                });

                this.children.enableLockout = new ControlGroup({
                    controlType: 'SyntheticRadio',
                    controlOptions: {
                        modelAttribute: 'lockoutUsers',
                        model: this.model.splunkAuth.entry.content,
                        items: [
                            {
                                label: _('Enable').t(),
                                value: true
                            },
                            {
                                label: _('Disable').t(),
                                value: false
                            }
                        ]
                    }
                });

                this.children.lockoutAttempts = new ControlGroup({
                    controlType: 'Text',
                    help: _('Number of unsuccessful login attempts that can occur before a user is locked out.').t(),
                    controlOptions: {
                        modelAttribute: 'lockoutAttempts',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Failed login attempts').t()
                });

                this.children.lockoutThresholdMins = new ControlGroup({
                    controlType: 'Text',
                    help: _('Number of minutes that must pass from the time of the first failed login until the failed login attempt counter resets.').t(),
                    controlOptions: {
                        modelAttribute: 'lockoutThresholdMins',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Lockout threshold in minutes').t()
                });

                this.children.lockoutMins = new ControlGroup({
                    controlType: 'Text',
                    help: _('Number of minutes a user must wait before attempting login.').t(),
                    controlOptions: {
                        modelAttribute: 'lockoutMins',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Lockout duration in minutes').t()
                });

                this.children.enablePasswordHistory = new ControlGroup({
                    controlType: 'SyntheticRadio',
                    controlOptions: {
                        modelAttribute: 'enablePasswordHistory',
                        model: this.model.splunkAuth.entry.content,
                        items: [
                            {
                                label: _('Enable').t(),
                                value: true
                            },
                            {
                                label: _('Disable').t(),
                                value: false
                            }
                        ]
                    }
                });

                this.children.passwordHistoryCount = new ControlGroup({
                    controlType: 'Text',
                    help: _('Number of passwords that are stored in history; a user cannot reuse passwords stored in history when changing their password.').t(),
                    controlOptions: {
                        modelAttribute: 'passwordHistoryCount',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Password history count').t()
                });
				
                this.children.constantLoginTime = new ControlGroup({
                    controlType: 'Text',
                    help: _('Sets a login time that stays consistent regardless of user settings. Set a time between .001 and 5 seconds. Set to 0 to disable the feature.').t(),
                    controlOptions: {
                        modelAttribute: 'constantLoginTime',
                        model: this.model.splunkAuth.entry.content
                    },
                    label: _('Constant login time').t()
                });

                this.children.verboseLoginFailMsg = new ControlGroup({
                    controlType: 'SyntheticRadio',
                    help: _('Setting the fail message to simple means that the user is not told why their login failed (for example, expired password or user lockout).').t(),
                    controlOptions: {
                        modelAttribute: 'verboseLoginFailMsg',
                        model: this.model.splunkAuth.entry.content,
                        items: [
                            {
                                label: _('Verbose').t(),
                                value: true
                            },
                            {
                                label: _('Simple').t(),
                                value: false
                            }
                        ]
                    },
                    label: _('Login fail message').t()
                });
				
                this.children.flashMessages = new FlashMessagesView({model: this.model.splunkAuth.entry.content});
                this.model.splunkAuth.entry.content.on('change:expireUserAccounts', this.toggleEnableExpiration, this);
                this.model.splunkAuth.entry.content.on('change:lockoutUsers', this.toggleEnableLockout, this);
                this.model.splunkAuth.entry.content.on('change:enablePasswordHistory', this.toggleEnablePasswordHistory, this);
            },

            toggleEnableExpiration: function(model, value, options) {
                if (value === true){
                    this.children.expirePasswordDays.enable();
                    this.children.expireAlertDays.enable();
                }else{
                    this.children.expirePasswordDays.disable();
                    this.children.expireAlertDays.disable();
                }
            },

            toggleEnableLockout: function(model, value, options) {
                if (value === true){
                    this.children.lockoutAttempts.enable();
                    this.children.lockoutThresholdMins.enable();
                    this.children.lockoutMins.enable();
                }else{
                    this.children.lockoutAttempts.disable();
                    this.children.lockoutThresholdMins.disable();
                    this.children.lockoutMins.disable();
                }
            },

            toggleEnablePasswordHistory: function(model, value, options) {
                if (value === true){
                    this.children.passwordHistoryCount.enable();
                }else{
                    this.children.passwordHistoryCount.disable();
                }
            },

            events: {
                'click .btn.save-button': function(e) {

                    this.children.flashMessages.flashMsgHelper.removeGeneralMessage("saved");
                    if (!this.model.splunkAuth.entry.content.isValid(true)) {
                        return;
                    }

                    this.model.splunkAuth.save({}, {
                        validate: true,
                        success: function(model, response) {
                            if (this.model.serverInfo.isLite()) {
                             window.location.href = this.backUrl;
                            } else {
                                var savedMessage = {
                                    type: 'success',
                                    html: _('Password settings saved.').t()
                                };
                                this.children.flashMessages.flashMsgHelper.addGeneralMessage("saved", savedMessage);
                                window.scrollTo(0, 0);
                            }
                        }.bind(this)
                    }); 

                    e.preventDefault();
                }
            },
 
            render: function() {
                this.$el.html(this.compiledTemplate({
                    url: this.backUrl
                }));

                this.children.minPasswordLength.render().replaceAll(this.$(".minPasswordLength-placeholder"));
                this.children.minPasswordDigit.render().replaceAll(this.$(".minPasswordDigit-placeholder"));
                this.children.minPasswordLowercase.render().replaceAll(this.$(".minPasswordLowercase-placeholder"));
                this.children.minPasswordUppercase.render().replaceAll(this.$(".minPasswordUppercase-placeholder"));
                this.children.minPasswordSpecial.render().replaceAll(this.$(".minPasswordSpecial-placeholder"));
                this.children.forceWeakPasswordChange.render().replaceAll(this.$(".forceWeakPasswordChange-placeholder"));
                this.children.enableExpiration.render().replaceAll(this.$(".enableExpiration-placeholder"));
                this.children.expirePasswordDays.render().replaceAll(this.$(".expirePasswordDays-placeholder"));
                this.children.expireAlertDays.render().replaceAll(this.$(".expireAlertDays-placeholder"));
                this.children.enableLockout.render().replaceAll(this.$(".enableLockout-placeholder"));
                this.children.lockoutAttempts.render().replaceAll(this.$(".lockoutAttempts-placeholder"));
                this.children.lockoutThresholdMins.render().replaceAll(this.$(".lockoutThresholdMins-placeholder"));
                this.children.lockoutMins.render().replaceAll(this.$(".lockoutMins-placeholder"));
                this.children.enablePasswordHistory.render().replaceAll(this.$(".enablePasswordHistory-placeholder"));
                this.children.passwordHistoryCount.render().replaceAll(this.$(".passwordHistoryCount-placeholder"));
                this.children.constantLoginTime.render().replaceAll(this.$(".constantLoginTime-placeholder"));
                this.children.verboseLoginFailMsg.render().replaceAll(this.$(".verboseLoginFailMsg-placeholder"));
                this.children.flashMessages.render().prependTo(this.$('.form-wrapper'));

                if (splunkUtil.normalizeBoolean(this.model.splunkAuth.entry.content.get('expireUserAccounts')) === false) {
                    this.toggleEnableExpiration(null, false, null);
                }

                if (splunkUtil.normalizeBoolean(this.model.splunkAuth.entry.content.get('lockoutUsers')) === false) {
                    this.toggleEnableLockout(null, false, null);
                }

                if (splunkUtil.normalizeBoolean(this.model.splunkAuth.entry.content.get('enablePasswordHistory')) === false) {
                    this.toggleEnablePasswordHistory(null, false, null);
                }

                return this;
            },
            
            template: '\
                <div class="section-padded section-header"> \
                    <h1 class="section-title"><%- _("Password Policy Management").t() %></h1> \
                    <% if (this.model.serverInfo.isLite()) { %> \
                        <div class="breadcrumb"><a href="<%- url%>"><%- _("Manage Accounts").t() %></a> &raquo <%- _("Password Policy Management").t() %></div> \
                    <% } %> \
                    <label class="password-description"> \
                        <i class="icon-info-circle"></i> \
                        <%- _("These Password Policy Management settings apply only to Internal Splunk Authentication, not to SAML or LDAP.").t() %> \
                    </label> \
                </div> \
                <div class="edit-form-wrapper"> \
                    <div class="form-wrapper form-horizontal"> \
                        <h2><%- _("Password Rules").t() %></h2> \
                        <div class="minPasswordLength-placeholder"></div> \
                        <div class="minPasswordDigit-placeholder"></div> \
                        <div class="minPasswordLowercase-placeholder"></div> \
                        <div class="minPasswordUppercase-placeholder"></div> \
                        <div class="minPasswordSpecial-placeholder"></div> \
                        <h2><%- _("Expiration").t() %></h2> \
                        <div class="enableExpiration-placeholder"></div> \
                        <div class="expirePasswordDays-placeholder"></div> \
                        <div class="expireAlertDays-placeholder"></div> \
                        <h2><%- _("History").t() %></h2> \
                        <div class="enablePasswordHistory-placeholder"></div> \
                        <div class="passwordHistoryCount-placeholder"></div> \
                        <h2><%-_("Login Settings").t() %></h2> \
                        <div class="constantLoginTime-placeholder"></div> \
                        <div class="verboseLoginFailMsg-placeholder"></div> \
                        <div class="forceWeakPasswordChange-placeholder"></div> \
                        <h2><%- _("Lockout").t() %></h2> \
                        <div class="enableLockout-placeholder"></div> \
                        <div class="lockoutAttempts-placeholder"></div> \
                        <div class="lockoutThresholdMins-placeholder"></div> \
                        <div class="lockoutMins-placeholder"></div> \
                    </div> \
                    <div class="jm-form-actions"> \
                        <a href="#" class="btn btn-primary save-button"><%- _("Save").t() %></a> \
                        <% if (this.model.serverInfo.isLite()) { %> \
                            <a href="<%- url%>" class="btn btn-secondary cancel-button"><%- _("Cancel").t() %></a> \
                        <% } %> \
                    </div> \
                </div> \
                '
        });
    }
);
