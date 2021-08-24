define(
    [
        'module',
        'contrib/text!./Master.html',
        'underscore',
        'splunk.util',
        'util/login_page',
        'uri/route',
        'views/Base',
        'views/account/login/Master',
        'views/account/passwordchange/Master',
        'views/account/TOSAccept',
        'views/account/mfa_duo/Master',
        'views/account/mfa_rsa/Master',
        './shared.pcss'
    ],
    function(module, template, _, splunkutil, LoginPageUtils, route, BaseView, LoginView, PasswordChangeView, TOSAcceptView, DuoAuthView, RsaAuthView, css) {
        return BaseView.extend({
            moduleId: module.id,
            template: template,
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                this.children.passwordChange = new PasswordChangeView({
                    model: {
                        application: this.model.application,
                        session: this.model.session,
                        login: this.model.login,
                        user: this.model.user
                    }
                });
                this.children.login = new LoginView({
                    model: {
                        application: this.model.application,
                        serverInfo: this.model.serverInfo,
                        session: this.model.session,
                        web: this.model.web,
                        login: this.model.login,
                        duo: this.model.duo,
                        rsa: this.model.rsa,
                        mfaStatus: this.model.mfaStatus
                    }
                });
                this.children.tosAccept = new TOSAcceptView({
                    model: {
                        tos: this.model.tos,
                        login: this.model.login
                    }
                });
                this.children.duoAuth = new DuoAuthView({
                    model: this.model.duo
                });
                this.children.rsaAuth = new RsaAuthView({
                    model: {
                        rsa: this.model.rsa,
                        login: this.model.login
                    }
                });
                this.listenTo(this.model.application, 'change:page', this.visibility);
            },
            visibility: function() {
                this.$el.attr('data-page', this.model.application.get('page'));
                if (this.model.application.get('page') === 'passwordchange' || this.model.session.entry.content.get('forcePasswordChange')) {
                    this.children.duoAuth.hide();
                    this.children.login.$el.hide();
                    this.children.passwordChange.show();
                    this.children.tosAccept.$el.hide();
                    this.children.rsaAuth.$el.hide();
                } else if (this.model.application.get('page') === 'tosaccept') {
                    this.children.duoAuth.hide();
                    this.children.login.$el.hide();
                    this.children.passwordChange.$el.hide();
                    this.children.tosAccept.$el.show();
                    this.children.rsaAuth.$el.hide();
                } else if (this.model.application.get('page') === 'duoauth') {
                    this.children.login.$el.hide();
                    this.children.passwordChange.$el.hide();
                    this.children.tosAccept.$el.hide();
                    this.children.duoAuth.show();
                    this.children.rsaAuth.$el.hide();
                } else if (this.model.application.get('page') === 'rsaauth') {
                    this.children.login.$el.hide();
                    this.children.passwordChange.$el.hide();
                    this.children.tosAccept.$el.hide();
                    this.children.duoAuth.hide();
                    this.children.rsaAuth.$el.show();
                } else {
                    this.children.duoAuth.hide();
                    this.children.passwordChange.$el.hide();
                    this.children.login.show();
                    this.children.tosAccept.$el.hide();
                    this.children.rsaAuth.$el.hide();
                }
            },
            onAddedToDocument: function() {
                BaseView.prototype.onAddedToDocument.apply(this, arguments);
                this.visibility();
            },
            render: function() {
                var html = this.compiledTemplate({
                    _: _,
                    version: this.model.serverInfo.getVersion(),
                    build: this.model.serverInfo.getBuild(),
                    logo: this.model.serverInfo.getProductLogo(),
                    customLogo: route.loginPageLogo(
                        this.model.application.get('root'),
                        this.model.application.get('locale'),
                        this.model.serverInfo.entry.content.get('build'),
                        this.model.web.entry.content.get('loginCustomLogo')),
                    footer: LoginPageUtils.getFooter(
                        this.model.web.entry.content.get('loginFooterOption'),
                        this.model.web.entry.content.get('loginFooterText')),
                    splunkutil: splunkutil
                });
                this.$el.html(html);
                this.visibility();
                this.children.login.render().appendTo(this.$('.content'));
                this.children.passwordChange.render().appendTo(this.$('.content'));
                this.children.duoAuth.render().appendTo(this.$('.content'));
                this.children.rsaAuth.render().appendTo(this.$('.content'));
                this.children.tosAccept.render().appendTo(this.$('.content'));
                return this;
            }
        });
    }
);
