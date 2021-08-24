define(
    [
        'module',
        'underscore',
        'views/Base',
        'contrib/text!views/account/login/Error.html'
    ],
    function(
        module,
        _,
        BaseView,
        template
    ) {
        return BaseView.extend({
            template: template,
            moduleId: module.id,
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                this.listenTo(this.model.login, 'error', this.render);
                this.listenTo(this.model.duo, 'error', this.render);
                this.listenTo(this.model.rsa, 'error', this.render);
            },
            getErrorMessages: function() {
                var messages = [];
                if ((this.model.login.error.get('messages') || []).length) {
                    _.each(this.model.login.error.get('messages'), function(message) {
                        messages.push({message: message.message});
                    });
                }
                if (this.model.serverInfo.isLicenseStatePreviouslyKeyed()) {
                    messages.push({
                        message: _('Splunk has detected that you are using a license for an older version of Splunk.').t(),
                        link: {
                            url: "http://www.splunk.com/r/my_licenses",
                            title: _("Get an updated license.").t(),
                            className: "external",
                            newPage: true
                        }
                    });
                }
                else if (this.model.serverInfo.isLicenseStateExpired()) {
                    messages.push({message: _('Your license is expired.').t()});
                    messages.push({message: _('Please login as an administrator to update the license.').t()});
                }
                if (this.model.application.get("page") === "logout") {
                    messages.push({message: _('You have been logged out. Log in to return to the system.').t()});
                }
                if (!this.model.session.isCookieEnabled()) {
                    messages.push({message: _('No cookie support detected.  Check your browser configuration.').t()});
                }
                else if (!this.model.session.isCookieValid()) {
                    messages.push({message: _('Invalid cookie detected.  Try reloading this page or restarting your browser.').t()});
                }
                else if (this.model.session.isClientTimeSkewed()) {
                    messages.push({message: _('Warning: The time on the server differs significantly from this machine which may cause login problems and other errors.').t()});
                }
                else if (this.model.application.get("page") !== "logout" && this.model.session.isSessionExpired()) {
                    messages.push({message: _('Your session has expired. Log in to return to the system.').t()});
                }
                if (this.model.mfaStatus.hasError()) {
                    messages.push({message: this.model.mfaStatus.getErrorMessage()});
                }
                if (this.model.duo.hasError()) {
                    messages.push({message: this.model.duo.getErrorMessage()});
                }
                if (this.model.rsa.hasError()) {
                    messages.push({message: this.model.rsa.getErrorMessage()});
                }
               return messages;
            },
            render: function() {
                var messages = this.getErrorMessages(),
                    html = this.compiledTemplate({
                    _: _,
                    model: {
                        login: this.model.login,
                        serverInfo: this.model.serverInfo,
                        application: this.model.application,
                        session: this.model.session,
                        mfaStatus: this.model.mfaStatus,
                        duo: this.model.duo,
                        rsa: this.model.rsa
                    },
                    messages: this.getErrorMessages()
                });
                this.$el.html(html);

                if (!messages.length) {
                    this.$el.attr('data-no-messages', 'true');
                }
                return this;
            }
        });
    }
);
