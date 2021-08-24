define([
    'jquery',
    'underscore',
    'module',
    'uri/route',
    'views/Base',
    'contrib/text!./Contents.html',
    './Contents.pcssm',
    'splunk.time',
    'splunk.util',
    'util/color_utils',
    'util/htmlcleaner',
    'views/shared/Icon'
],
function(
    $,
    _,
    module,
    route,
    BaseView,
    Template,
    css,
    Time,
    util,
    color_utils,
    HtmlCleaner,
    IconView
){
    return BaseView.extend({
        moduleId: module.id,
        template: Template,
        css: css,
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
            var currentAppName = this.model.application.get('app'),
                currentApp,
                date = new Time.DateTime();

            this.copyrightyear = process.env.copyrightYear|| '';
            if (currentAppName === 'launcher') {
                this.currentAppLabel = _('Home').t();
            }
            else {
                if (this.collection) {
                    currentApp = this.collection.find(function(app) {
                        return app.entry.get('name') === currentAppName;
                    });
                }
                this.currentAppLabel = currentApp ? currentApp.entry.content.get('label') : _('N/A').t();
                this.currentAppAttributionLink = this.computeAttributionLink(currentApp);
            }
            this.model.serverInfo.on('change reset', function() {
                this.render();
            }, this);

            this.children.splunk = new IconView({icon: 'splunk'});
            this.children.prompt = new IconView({icon: 'greaterRegistered'});
            this.children.product = new IconView({icon: this.model.serverInfo.getProductIconName()});
        },
        getListOfProducts: function() {
            var addOns = this.model.serverInfo.getAddOns(),
                result;
            if (addOns && !$.isEmptyObject(addOns)) {
                result = _(addOns).keys().join(', ');
            }
            return result;
        },
        computeAttributionLink: function(currentApp) {
            var attributionLink = currentApp && currentApp.entry.content.get('attribution_link');
            if (!attributionLink) {
                return null;
            }
            // If the attribution link contains any XSS vulnerable URL schemes, do not display the link.
            if (HtmlCleaner.isBadUrl(attributionLink)) {
                return null;
            }
            // If the attribution link does not start with http:// or https://, treat it as a docs location string.
            if (!/http[s]?:\/\//.test(attributionLink)) {
                var app = this.model.application.get("app");
                return route.docHelpInAppContext(
                    this.model.application.get('root'),
                    this.model.application.get('locale'),
                    attributionLink,
                    app,
                    this.model.appLocal.entry.content.get('version'),
                    app === 'system' ? true : this.model.appLocal.isCoreApp(),
                    this.model.appLocal.entry.content.get('docs_section_override')
                );
            }
            return attributionLink;
        },
        getAppColor: function() {
            if (!this.model.appNav) {
                return false;
            }
            var appColor = color_utils.normalizeHexString(this.model.appNav.get('color')||'#818D99');
            var isHexColor = /(^#[0-9A-F]{6}$)|(^#[0-9A-F]{3}$)/i.test(appColor);
            if (!isHexColor){
                return false;
            }
            return appColor;
        },
        showIcon: function() {
            // Do not show an app icon if this isLite.
            if (this.model.serverInfo.isLite()) {
                return;
            }
            var logoSelector = '[data-role=app-logo]';
            if (this.model.appNav && this.model.appNav.get('icon')) {
                var img = new Image();
                img.onload = function(){
                    this.$el.find(logoSelector).empty().append(img);
                    $(img).attr('class', css.aboutIcon).attr('data-role', 'icon');
                    var appColor = color_utils.normalizeHexString(this.model.appNav.get('color')||'#818D99');
                    var isHexColor = /(^#[0-9A-F]{6}$)|(^#[0-9A-F]{3}$)/i.test(appColor);
                    if (isHexColor){
                        this.$el.find(logoSelector + ' img').css('background-color', appColor);
                    }
                }.bind(this);
                img.src = this.model.appNav.get('icon');
            }
        },
        showLogo: function(){
            if (this.model.appNav && this.model.appNav.get('logo')) {
                var img = new Image();
                var logoSelector = '[data-role=app-logo]';
                img.onload = function(){
                    if (parseInt(img.width, 10) < 2){
                        this.showIcon();
                    } else {
                        this.$el.find(logoSelector).empty().append(img);
                        $(img).attr('class', css.aboutIcon).attr('data-role', 'logo');
                        this.$el.find(logoSelector).show();
                    }
                }.bind(this);

                img.onerror = function(){
                    this.showIcon();
                }.bind(this);

                img.src = this.model.appNav.get('logo');
            } else {
                this.showIcon();
            }
        },
        render: function() {
            //this.$el.html(Modal.TEMPLATE);
            //this.$(Modal.HEADER_TITLE_SELECTOR).html('splunk<span class="prompt">&gt;&#x00AE;'+this.model.serverInfo.getProductLogo()+'</span>');
            var isLite = this.model.serverInfo.isLite(),
                isLiteFree = this.model.serverInfo.isLiteFree(),
                versionNumberText = this.model.serverInfo.getVersion() || _('N/A').t(),
                liteVersionText = (isLiteFree) ? _('Splunk Light Free Version ').t() + versionNumberText : _('Splunk Light Version ').t() + versionNumberText,
                versionText = (isLite) ? liteVersionText : versionNumberText,
                template = this.compiledTemplate({
                    serverName: this.model.serverInfo.getServerName() || _('N/A').t(),
                    productName: this.model.serverInfo.getProductName(),
                    version: versionText,
                    isEnterprise: this.model.serverInfo.isEnterprise(),
                    build: this.model.serverInfo.getBuild() || _('N/A').t(),
                    appVersion: this.model.appLocal.entry.content.get('version') || null,
                    appBuild: this.model.appLocal.entry.content.get('build') || null,
                    appAttributionLink: this.currentAppAttributionLink,
                    listOfProducts: this.getListOfProducts(),
                    currentApp: this.currentAppLabel,
                    isLite: isLite,
                    isCloud: this.model.serverInfo.isCloud(),
                    thirdPartyCredits: route.docHelp(this.model.application.get('root'), this.model.application.get('locale'), 'ReleaseNotes.Credits'),
                    copyrightYear: this.copyrightyear,
                    sprintf: util.sprintf,
                    css: css
                });
            this.$el.html(template);
            this.showLogo();

            this.children.splunk.render().appendTo(this.$('[data-title-role=splunk]'));
            this.children.prompt.render().appendTo(this.$('[data-title-role=prompt]'));
            this.children.product.set({icon: this.model.serverInfo.getProductIconName()}).render().appendTo(this.$('[data-title-role=product]'));

            return this;
        }
    });
});
