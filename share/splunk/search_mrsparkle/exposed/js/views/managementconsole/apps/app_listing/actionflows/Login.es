import LoginView from 'views/shared/apps_remote/dialog/Login';
import './Login.pcss';

export default LoginView.extend({
    moduleId: module.id,

    initialize(options) {
        LoginView.prototype.initialize.call(this, options);

        this.operation = this.options.operation;
        this.appName = this.options.appName || this.model.app.getAppLabel();
        this.splunkBaseLink = this.options.splunkBaseLink || this.model.app.getRemotePath();
        this.licenseName = this.options.licenseName || this.model.app.getLicenseName();
        this.licenseURL = this.options.licenseURL || this.model.app.getLicenseUrl();
    },
    render() {
        this.el.innerHTML = this.compiledTemplate({
            operation: this.operation,
        });
        this.children.flashMessages.render().appendTo(this.$('.flash-messages-placeholder'));

        this.children.username.render().appendTo(this.$('.username-placeholder'));
        this.children.password.render().appendTo(this.$('.password-placeholder'));
        this.children.consent.render().appendTo(this.$('.consent-placeholder'));

        this.$('#splunk-base-link').text(this.appName);
        this.$('#splunk-base-link').attr('href', this.splunkBaseLink);
        this.$('#app-license').text(this.licenseName);
        this.$('#app-license').attr('href', this.licenseURL);

        return this;
    },

    doLogin() {
        this.model.auth.save({
            username: this.model.auth.get('username'),
            password: this.model.auth.get('password'),
            consent: this.model.auth.get('consent'),
        }, {
            error: (model) => {
                model.trigger('login:fail');
            },
            success: (model) => {
                model.trigger('login:success');
            },
        });
    },

    template:
        '<div class="flash-messages-placeholder"></div>' +
        '<div class="form form-horizontal">' +
        '<p><%- _("Enter your Splunk.com username and password to ").t() + operation + _(" the app.").t() %></p>' +
        '<div class="username-placeholder"></div>' +
        '<div class="password-placeholder"></div>' +
        '<a href="#" class="forgot-password"><%- _("Forgot your password?").t() %></a>' +
        '<p class="rights"><%- _("The app, and any related dependency that will be installed, ' +
        'may be provided by Splunk and/or a third party and your right to use these app(s) is in ' +
        'accordance with the applicable license(s) provided by Splunk and/or the third-party licensor. ' +
        'Splunk is not responsible for any third-party app and does not provide any warranty or support. ' +
        'If you have any questions, complaints or claims with respect to an app, please contact the applicable ' +
        'licensor directly whose contact information can be found on the Splunkbase download page.").t() %></p>' +
        '<p class="rights"><a target="_blank" class="license-agreement" id="splunk-base-link"></a>' +
        '<%- _(" is governed by the following license: ").t() %>' +
        '<a target="_blank" class="license-agreement" id="app-license"></a></p>' +
        '<div class="consent-placeholder"></div> ' +
        '</div>',
});
