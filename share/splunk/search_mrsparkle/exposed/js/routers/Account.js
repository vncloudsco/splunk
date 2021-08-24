define(
    [
        'jquery',
        'backbone',
        'underscore',
        'uri/route',
        'splunk.config',
        'splunk.util',
        'models/shared/SessionStore',
        'models/shared/Application',
        'models/classicurl',
        'models/services/server/ServerInfo',
        'models/services/configs/Web',
        'models/shared/User',
        'models/account/Session',
        'models/account/Login',
        'models/account/TOS',
        'models/account/MFAStatus',
        'models/account/Duo',
        'models/account/Rsa',
        'views/account/Master',
        'util/login_page',
        'jquery.cookie'
    ],
    function(
        $,
        Backbone,
        _,
        route,
        splunkConfig,
        util,
        SessionStoreModel,
        ApplicationModel,
        classicurlModel,
        ServerInfoModel,
        WebModel,
        UserModel,
        SessionModel,
        LoginModel,
        TOSModel,
        MFAStatusModel,
        DuoModel,
        RsaModel,
        MasterView,
        LoginPageUtils,
        jqueryCookie
    ) {
        // These translations are used in the /templates/pages/static.html page but need to be declared here so that
        // they will be extracted and added to the javascript translation scope.
        _('This browser is not supported by Splunk.').t();
        _('Please refer to the list of %s.').t();
        _('Supported Browsers').t();

        return Backbone.Router.extend({
            routes: {
                ':locale/account/:page': 'page',
                ':locale/account/:page?*params': 'page',
                ':locale/account/:page/': 'page',
                ':locale/account/:page/?*params': 'page',
                '*root/:locale/account/:page': 'pageRooted',
                '*root/:locale/account/:page?*params': 'pageRooted',
                '*root/:locale/account/:page/': 'pageRooted',
                '*root/:locale/account/:page/?*params': 'pageRooted'
            },
            status: {
                MFA_SUCCESSFUL: 0,
                MFA_BOOTSTRAP_TOS: 4,
                MFA_BOOTSTRAP: 5,
                RSA_TOKENMODE: 7
            },
            initialize: function() {
                this.model = {};
                this.model.application = new ApplicationModel();
                this.model.classicurl = classicurlModel;
                this.model.serverInfo = new ServerInfoModel({}, {splunkDPayload: __splunkd_partials__['/services/server/info']});
                this.model.session = new SessionModel({}, {splunkDPayload: __splunkd_partials__['/services/session']});
                this.model.tos = new TOSModel();
                this.model.web = new WebModel({}, {splunkDPayload: __splunkd_partials__['/configs/conf-web']});
                this.model.login = new LoginModel();
                this.model.duo = new DuoModel();
                this.model.rsa = new RsaModel();
                this.model.mfaStatus = new MFAStatusModel({}, {splunkDPayload: __splunkd_partials__['/account/mfa/status']});
                this.model.user = new UserModel({}, {serverInfoModel: this.model.serverInfo});
                this.model.user.urlRoot = undefined;//urlRoot is relied on by other consumers; required to be deleted in order to set a fully qualified link as id
                this.model.login.on('error', function(model, response, option) {
                    var responseJSON = response.responseJSON;
                    if (this.model.login.isPasswordChangeRequired()) {
                        this.model.application.set('page', 'passwordchange');
                    } else if(this.model.login.isTOSAcceptRequired() && responseJSON && responseJSON.tos_version && responseJSON.tos_url) {
                        this.bootstrapTOS(responseJSON.tos_version, responseJSON.tos_url);
                    }
                }, this);
                this.model.login.on('skipChangePassword', this.setLoginCookie, this);
                this.model.login.on('sync', function() {
                    if (this.model.login.get('status') === this.status.MFA_BOOTSTRAP) {
                        if (this.model.login.get('mfa_vendor') === 'rsa-mfa') {
                            // Initialize the Rsa model and its listeners.
                            this.model.application.set('page', 'rsaauth');
                            this.model.rsa.on('sync', this.handleRsaSuccess, this);
                            this.model.rsa.on('error', this.handleRsaError, this);
                        } else {
                            // Initialize the Duo model and its listeners.
                            this.model.duo.fetch().done(function() {
                                    this.model.application.set('page', 'duoauth');
                                }.bind(this));
                            this.model.duo.on('sync', this.handleDuoSuccess, this);
                            this.model.duo.on('error', this.handleDuoError, this);
                        }
                    } else if(this.model.login.isPasswordExpiring()) {
                        var id = '/services/' + this.model.user.url + '/' + encodeURIComponent(this.model.login.get('username'));
                        this.model.user.set('id', id);
                        this.model.user.entry.content.set('oldpassword', this.model.login.get('password'));
                        this.model.application.set('page', 'passwordchange');
                    } else {
                        this.successRedirect();
                    }
                    var sessionStore = SessionStoreModel.getInstance(true);
                }, this);
                this.model.user.on('sync', function() {
                    this.successRedirect();
                }, this);
                this.model.tos.on('sync', function() {
                    this.model.application.set('page', 'tosaccept');
                }, this);
                //ensure globals ie., window.$C sync'd with splunkd session partial values
                splunkConfig.LOCALE = this.model.session.entry.content.get('lang');
                //SSO initiated TOS
                if (this.model.session.entry.content.get('tos_version') && this.model.session.entry.content.get('tos_url')) {
                    this.model.application.set('page', 'tosaccept'); // Set data-page attribute for proper stying.
                    this.bootstrapTOS(this.model.session.entry.content.get('tos_version'), this.model.session.entry.content.get('tos_url'));
                }
            },
            handleDuoSuccess: function(model, response, options){
                if (response.status && response.status == this.status.MFA_BOOTSTRAP_TOS && response.tos_url && response.tos_version){
                    this.bootstrapTOS(response.tos_version, response.tos_url);
                } else if (response.status === this.status.MFA_SUCCESSFUL) {
                    this.successRedirect();
                }
            },
            handleDuoError: function(model, response, option){
                var responseJSON = response.responseJSON;
                if (responseJSON && responseJSON.status == this.status.MFA_BOOTSTRAP_TOS && responseJSON.tos_version && responseJSON.tos_url && responseJSON.login_type) {
                        this.model.login.set('login_type', responseJSON.login_type);
                        this.bootstrapTOS(responseJSON.tos_version, responseJSON.tos_url);
                } else {
                    this.model.application.set('page','login');
                }
            },
            handleRsaSuccess: function(model, response, options){
                if (response.status && response.status == this.status.MFA_BOOTSTRAP_TOS && response.tos_url && response.tos_version){
                    this.bootstrapTOS(response.tos_version, response.tos_url);
                } else if (response.status === this.status.MFA_SUCCESSFUL) {
                    this.successRedirect();
                }
            },
            handleRsaError: function(model, response, option){
                var responseJSON = response.responseJSON;
                if (responseJSON && responseJSON.status == this.status.MFA_BOOTSTRAP_TOS && responseJSON.tos_version && responseJSON.tos_url && responseJSON.login_type) {
                        this.model.login.set('login_type', responseJSON.login_type);
                        this.bootstrapTOS(responseJSON.tos_version, responseJSON.tos_url);
                } else if (responseJSON && responseJSON.status == this.status.RSA_TOKENMODE) {
                    this.model.login.set('tokenmode', true);
                    this.model.rsa.set('authnAttemptId', responseJSON.authnAttemptId);
                    this.model.rsa.set('inResponseTo', responseJSON.inResponseTo);
                } else {
                    this.model.application.set('page','rsaauth');
                }
            },
            successRedirect: function(options) {
                this.setLoginCookie();
                this.bootstrapSplunkWebUIDCookie();
                options || (options = {});
                var root = this.model.application.get('root'),
                    locale = this.model.application.get('locale'),
                    url = route.returnTo(root, locale, this.model.application.get('return_to') || ''),
                    licenseUrl = route.manager(root, locale, 'system', 'licensing'),
                    expired = this.model.serverInfo.isLicenseStateExpired();

                if (expired && this.model.serverInfo.isLite()) {
                    window.location = licenseUrl;
                } else if (options.delay) {
                    setTimeout(function() {
                        window.location = url;
                    }, options.delay);
                } else {
                    window.location = url;
                }
            },
            bootstrapSplunkWebUIDCookie: function() {
                var uid = this.model.session.entry.content.get('splunkweb_uid');
                if (uid) {
                    // Adding another splunkweb_uid cookie with root path
                    // for updatechecker in Base router.
                    $.cookie('splunkweb_uid', uid, {path: '/'});
                }
            },
            setLoginCookie: function() {
                $.cookie('login', true, {path: '/'});
            },
            bootstrapTOS: function(tosVersion, tosURL) {
                this.model.tos.set({
                    tos_version: tosVersion
                });
                this.model.tos.fetch({url: tosURL});
            },
            page: function(locale, page) {
                document.title = LoginPageUtils.getDocumentTitle(
                    _('Login').t(),
                    this.model.web.entry.content.get('loginDocumentTitleOption'),
                    this.model.web.entry.content.get('loginDocumentTitleText'));
                this.model.classicurl.fetch(); //is synchronous
                this.model.application.set({
                    locale: locale,
                    app: '-',
                    page: page,
                    return_to: this.model.classicurl.get('return_to')
                });
                var masterView = new MasterView({
                    model: {
                        application: this.model.application,
                        serverInfo: this.model.serverInfo,
                        session: this.model.session,
                        tos: this.model.tos,
                        web: this.model.web,
                        login: this.model.login,
                        user: this.model.user,
                        mfaStatus: this.model.mfaStatus,
                        duo: this.model.duo,
                        rsa: this.model.rsa
                    }
                });

                // Defer fixes flash of unstyled content. SPL-120335.
                _.defer(function() {
                    masterView.render().attachToDocument(document.body, 'appendTo');
                    LoginPageUtils.setupBackgroundImage(
                        this.model.application.get('root'),
                        this.model.application.get('locale'),
                        this.model.serverInfo.entry.content.get('build'),
                        this.model.web.entry.content.get('loginBackgroundImageOption'),
                        this.model.web.entry.content.get('loginCustomBackgroundImage'));
                }.bind(this));

                if (this.model.application.get('page')==='login') {
                    this.bootstrapSplunkWebUIDCookie();
                    if (this.model.serverInfo.isFreeLicense()) {
                        setTimeout(function() {
                            this.model.login.saveAsFree(this.model.session.entry.content.get('cval'), this.model.application.get('return_to'));
                        }.bind(this), 1500);
                    }
                }
            },
            pageRooted: function(root, locale, page) {
                this.model.application.set({
                    root: root
                }, {silent: true});
                this.page(locale, page);
            }
        });
    }
);
