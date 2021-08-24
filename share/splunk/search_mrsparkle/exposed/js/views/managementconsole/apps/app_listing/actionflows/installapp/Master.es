import _ from 'underscore';
import $ from 'jquery';
import Backbone from 'backbone';
import AppModel from 'models/managementconsole/App';
import DMCBaseDialog from 'views/managementconsole/apps/app_listing/actionflows/DMCBase';
import LoginView from 'views/managementconsole/apps/app_listing/actionflows/Login';
import SyntheticCheckboxControl from 'views/shared/controls/SyntheticCheckboxControl';
import splunkUtils from 'splunk.util';
import urlHelper from 'helpers/managementconsole/url';

const IN_PROGRESS_MSG_TEMPLATE_DEFAULT = _('Splunk Cloud is downloading and installing <b>%s</b> (version %s).\n' +
    'This might take several minutes and cause Splunk Cloud to restart. Do not navigate away from this page until\n' +
    'the app installation process completes.').t();
const IN_PROGRESS_MSG_TEMPLATE_DEPENDENCIES = _('Splunk Cloud is downloading and installing <b>%s</b> (version %s)\n' +
    'and its dependencies. This might take several minutes and cause Splunk Cloud to restart. Do not navigate away\n' +
    'from this page until the app installation process completes.').t();

const INSTALLED_DEPENDENCIES_STR1 = _('The following dependent app(s) are already installed on your machine:').t();
const INSTALLED_DEPENDENCIES_STR2 = _('These dependent app(s) were installed externally and are not compatible with\n' +
    'self-service app installation. To resolve this issue, contact Splunk Support.').t();

const MISSING_DEPENDENCIES_STR_1_TEMPLATE = _('<b>%s</b> (version %s) could not be \n' +
    'installed because it requires the following app dependencies to be \n' +
    'installed:').t();

const MISSING_DEPENDENCIES_STR_2_TEMPLATE = _('Do you want to continue and install \n' +
    '<b>%s</b> (version %s) with these dependencies?').t();

const LOGIN_INSTALL_LABEL = _('Login and Install').t();
const BUTTON_LOGIN_DISABLED = `<button class="btn btn-primary modal-btn-login pull-right disabled" disabled>
    ${LOGIN_INSTALL_LABEL}</button>`;

const BUTTON_LOGIN = `<button class="btn btn-primary modal-btn-login pull-right">
    ${LOGIN_INSTALL_LABEL}</button>`;

const CONTINUE_LABEL = _('Continue').t();
const BUTTON_INSTALL_DEPENDENCIES_CONTINUE = `<a href="#" class="btn btn-primary
    modal-btn-primary pull-right modal-btn-continue install-dependencies">
    ${CONTINUE_LABEL}</a>`;

const INSTALL_LABEL = _('Install').t();
const BUTTON_INSTALL_DEPENDENCIES_INSTALL = `<a href="#" class="btn btn-primary install-dependencies
    modal-btn-primary modal-btn-install pull-right">${INSTALL_LABEL}</a>`;

const GO_BACK_LABEL = _('Go back to App Browser').t();
const BUTTON_GO_BACK_TO_APP_BROWSER = `<a href="#" class="btn modal-btn-close pull-left" data-dismiss="modal">
    ${GO_BACK_LABEL}</a>`;

const SLIM_STATUS_CODES = {
    STATUS_ERROR_MISSING_DEPENDENCIES: 4,
};

export default DMCBaseDialog.extend({
    className: [DMCBaseDialog.prototype.className, 'dmc-install-app-dialog'].join(' '),

    initialize(...args) {
        this.appName = this.model.appRemote.get('title');
        this.appVersion = this.model.appRemote.get('release').title;
        DMCBaseDialog.prototype.initialize.apply(this, args);

        const operationLabel = _('install').t();
        this.GENERIC_ERROR_MSG = splunkUtils.sprintf(DMCBaseDialog.GENERIC_ERROR_MSG_TEMPLATE, operationLabel);
        this.MISSING_CAPABILITIES_MSG = splunkUtils.sprintf(DMCBaseDialog.MISSING_CAPABILITIES_MSG_TEMPLATE,
            operationLabel);

        this.model.app = this.model.app || new AppModel();
        this.model.controller = this.model.controller || new Backbone.Model();
        this.children.loginStateChildren = new LoginView({
            model: {
                auth: this.model.auth,
                application: this.model.application,
                appRemote: this.model.appRemote,
            },
            operation: _('install').t(),
            appName: this.model.appRemote.get('title'),
            splunkBaseLink: this.model.appRemote.get('path'),
            licenseName: this.model.appRemote.get('license_name'),
            licenseURL: this.model.appRemote.get('license_url'),
        });

        this.listenTo(this.model.auth, 'login:success', this.onLoginSuccess);
        this.listenTo(this.model.controller, 'change:consent', (model, newVal) => {
            if (newVal) {
                this.$('.modal-btn-install.install-dependencies').removeClass('disabled');
                this.$('.modal-btn-login').prop('disabled', false);
            } else {
                this.$('.modal-btn-install.install-dependencies').addClass('disabled');
                this.$('.modal-btn-login').prop('disabled', true);
            }
        });
    },

    BUTTON_LOGIN_DISABLED,
    BUTTON_LOGIN,

    events: $.extend(true, {}, DMCBaseDialog.prototype.events, {
        'click .modal-btn-continue': function next(e) {
            e.preventDefault();

            this.setState(this.getLoginState());
        },
        'click .modal-btn-login': function next(e) {
            e.preventDefault();

            this.children.loginStateChildren.doLogin();
        },
        'click .modal-btn-continue.install-dependencies': function next(e) {
            e.preventDefault();

            this.setState(this.getInstallDependencyState());
        },
        'click .modal-btn-install.install-dependencies': function next(e) {
            e.preventDefault();

            this.executePrimaryFn();
        },
        'click .appslisting': function next(e) {
            e.preventDefault();
            const url = urlHelper.pageUrl('apps');
            document.location.href = url;
        },
    }),

    primFn() {
        this.model.app.clear();
        this.model.app.entry.content.set({
            appId: this.model.appRemote.get('appid'),
            auth: this.model.auth.get('sbsessionid'),
            installDependencies: !!this.model.controller.get('consent'),
        });

        return this.model.app.install();
    },

    setUrlParams() {
        urlHelper.replaceState({
            appId: this.model.appRemote.get('uid'),
        });
    },

    removeUrlParams() {
        urlHelper.removeUrlParam('appId');
    },

    onLoginSuccess() {
        this.executePrimaryFn();
    },

    onPrimFnSuccess(response) {
        if (this.willDeploy) {
            if (response.status === SLIM_STATUS_CODES.STATUS_ERROR_MISSING_DEPENDENCIES) {
                this.setState(this.getDependenciesFoundState(response));
                return;
            }

            this.setUrlParams(this.model.appRemote.get('uid'));
        }
        DMCBaseDialog.prototype.onPrimFnSuccess.call(this, response);
    },

    getConfirmTitle() {
        return _('Install - Confirm').t();
    },

    getConfirmBodyHTML() {
        const operationLabels = [_('install').t(), _('Installing').t()];
        return this.getConfirmBodyHTMLForOperation(operationLabels);
    },

    getLoginTitle() {
        return _('Login and Install').t();
    },

    isInstalledLocally(appId) {
        return !_.isUndefined(this.collection.appLocalsUnfiltered.findByEntryName(appId));
    },

    // retrieves list of app dependencies that were installed externally
    getInstalledDependencies(dependencies) {
        const installedDependencies = [];
        _.each(dependencies, (dependency) => {
            if (this.isInstalledLocally(dependency.app_id)) {
                installedDependencies.push(dependency);
            }
        });
        return installedDependencies;
    },

    getDependenciesFoundState(response) {
        this.dependencies = response.missing_dependencies;
        const installedDependencies = this.getInstalledDependencies(this.dependencies);
        // if there are any dependencies that were installed externally -> report install method conflict;
        if (installedDependencies.length > 0) {
            return {
                title: _('App installation failed - Install method conflict').t(),
                childrenArr: [$(_.template(this.installMethodConflictTemplate)({
                    _,
                    installedDependencies,
                }))],
                footerArr: [DMCBaseDialog.BUTTON_CLOSE],
            };
        }
        return {
            title: _('App installation failed - Missing dependencies').t(),
            childrenArr: [$(_.template(this.dependencyResolutionTemplate)({
                dependencies: this.dependencies,
                MISSING_DEPENDENCIES_STR_1: splunkUtils.sprintf(
                    MISSING_DEPENDENCIES_STR_1_TEMPLATE,
                    _.escape(this.appName),
                    _.escape(this.appVersion),
                ),
                MISSING_DEPENDENCIES_STR_2: splunkUtils.sprintf(
                    MISSING_DEPENDENCIES_STR_2_TEMPLATE,
                    _.escape(this.appName),
                    _.escape(this.appVersion),
                ),
            }))],
            footerArr: [DMCBaseDialog.BUTTON_CANCEL, BUTTON_INSTALL_DEPENDENCIES_CONTINUE],
        };
    },
    getInstallDependencyState() {
        return {
            title: _('App Dependency License Agreement').t(),
            childrenArr: this.getInstallDependencyChildren(),
            footerArr: [BUTTON_GO_BACK_TO_APP_BROWSER, BUTTON_INSTALL_DEPENDENCIES_INSTALL],
            renderCB: () => {
                const consent = new SyntheticCheckboxControl({
                    label: _('I have read the terms and conditions of the license(s) and agree to be bound by\n' +
                    'them.').t(),
                    model: this.model.controller,
                    modelAttribute: 'consent',
                });

                this.$('.app-dependency-consent-placeholder').append(consent.render().el);

                if (!this.model.controller.get('consent')) {
                    this.$('.modal-btn-install.install-dependencies').addClass('disabled');
                }
            },
        };
    },

    getInstallDependencyChildren() {
        const bodyhtml = _.template(this.installDependenciesTemplate)({
            licenses: AppModel.getLicenseMap(this.dependencies),
        });
        return [$(`<div>${bodyhtml}</div>`)];
    },

    getInProgressTitle() {
        return _('Install - In Progress').t();
    },

    getInProgressBodyHTML() {
        const isInstallingDependencies = this.model.app.entry.content.get('installDependencies');
        const template = isInstallingDependencies
            ? IN_PROGRESS_MSG_TEMPLATE_DEPENDENCIES
            : IN_PROGRESS_MSG_TEMPLATE_DEFAULT;
        const bodyHTML = splunkUtils.sprintf(template, this.appName, this.appVersion);
        return bodyHTML;
    },

    getSuccessState() {
        return {
            title: _('Install - Complete').t(),
            childrenArr: this.getSuccessChildren(),
            footerArr: [DMCBaseDialog.BUTTON_DONE],
        };
    },

    getSuccessChildren() {
        const compiledTemplate = _.template(this.successTemplate);
        const childrenArr = [];
        const bodyHTML = compiledTemplate({
            appName: this.appName,
            appVersion: this.appVersion,
        });

        childrenArr.push($(`<div>${bodyHTML}</div>`));

        const releaseNotesURI = this.model.app.getReleaseNotesURI();
        const sourcePackageDownloadLink = this.model.app.getExportUrl();
        if (!_.isNull(releaseNotesURI)) {
            childrenArr.push(`<a target="_blank" href="${releaseNotesURI}" class="btn btn-secondary successbtn
            releasenotes">${_('Read Release Notes').t()} <i class="icon-external"></i></a>`);
        }

        if (!_.isNull(sourcePackageDownloadLink)) {
            childrenArr.push(`<a href="${sourcePackageDownloadLink}"
              class="btn btn-secondary successbtn
              downloadpackage">${_('Download Source Package').t()}</a>`);
        }

        childrenArr.push(`<a href="#" class="btn btn-secondary successbtn appslisting">${_('View Apps').t()}</a>`);

        return childrenArr;
    },

    getSuccessPromises() {
        const appid = this.model.appRemote.get('appid');
        this.model.app.entry.set('name', appid); // need to update name
        return [this.model.app.fetch()];
    },

    getFailTitle() {
        return _('Install - Fail').t();
    },

    getDeployFailBodyHTML() {
        const operationLabel = _('installed').t();

        return splunkUtils.sprintf(DMCBaseDialog.DEPLOY_FAIL_MSG_TEMPLATE,
            _.escape(this.appName),
            _.escape(this.appVersionLabel),
            operationLabel,
        );
    },

    dependencyResolutionTemplate: `
        <p><%= MISSING_DEPENDENCIES_STR_1 %></p>
        <ul>
        <% _.each(dependencies, function(dependency) { %>
            <li><%- dependency.app_title %></li>
        <% }) %>
        </ul>
        <p><%= MISSING_DEPENDENCIES_STR_2 %></p>
    `,

    installMethodConflictTemplate: `
        <p>${INSTALLED_DEPENDENCIES_STR1}</p>
        <ul>
        <% _.each(installedDependencies, function(dependency) { %>
            <li><%- dependency.app_title %></li>
        <% }) %>
        </ul>
        <p>${INSTALLED_DEPENDENCIES_STR2}</p>
    `,

    installDependenciesTemplate:
    '<% _.each(licenses, function(licenseGroup, licenseName) { %>' +
        '<div class="license-group">' +
            '<p class="rights"><%- _("The").t() %> ' +
                '<a target="_blank" class="license-link" ' +
                'href="<%- licenseGroup.license_url %>"><%- licenseName %></a> ' +
            '<%- _("governs the following dependent app(s):").t() %>' +
            '<ul>' +
            '<% _.each(licenseGroup.apps, function(app) { %>' +
                '<li><%- app.app_title %></li>' +
            '<% }) %>' +
            '</ul>' +
        '</div>' +
    '<% }) %>' +
    '<a target="_blank" class="license-agreement" id="cloud-terms-conditions" href="' +
    'https://www.splunk.com/en_us/legal/terms/splunk-cloud-terms-of-service.html">' +
    '<%- _("Splunk Cloud Terms of Service").t() %></a></br> ' +
    '<div class="app-dependency-consent-placeholder"></div> ',

    successTemplate: '<%- _("Splunk Cloud installed").t() %> <strong><%- appName %></strong> (<%- appVersion %>).',
});
