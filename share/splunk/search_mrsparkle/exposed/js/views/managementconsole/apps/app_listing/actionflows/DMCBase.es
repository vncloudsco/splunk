import _ from 'underscore';
import $ from 'jquery';
import BaseDialog from 'views/managementconsole/apps/app_listing/actionflows/Base';
import splunkUtils from 'splunk.util';
import urlHelper from 'helpers/managementconsole/url';

const MULTIPLE_SERVER_ERROR_MSG = _('The following server errors were reported: ').t();

const CONFIRM_MSG_TEMPLATE = _('Are you sure you want to %s \n' +
    '<b>%s</b>%s? %s%s this app might cause \n' +
    'Splunk Cloud to restart and be unavailable for some time.').t();

const SHC_WARNING_MSG = _('This app might not run on a search head cluster deployment. ').t();

const IN_PROGRESS_MSG_TEMPLATE = _('Splunk Cloud is %s \n' +
    '<b>%s</b>%s. This process might take several minutes \n' +
    'and cause Splunk Cloud to restart. Do not navigate away from this \n' +
    'page until the app disable process completes.').t();

const GENERIC_ERROR_MSG_TEMPLATE = _('Splunk Cloud cannot %s this app \n' +
    'at this time. Exit and try again later.').t();

const MISSING_CAPABILITIES_MSG_TEMPLATE = _('You do not have permission to %s this app.').t();

const DEPLOY_FAIL_MSG_TEMPLATE = _('<b>%s</b>%s could not be %s because the deploy task failed. \n' +
    'You can retry the deployment task. If this deployment task continues to fail, contact \n' +
    'Splunk Support.').t();

const UNSUPPORTED_DEPLOYMENT_MSG = _('App does not support current deployment.').t();

export default BaseDialog.extend({
    className: [BaseDialog.prototype.className, 'dmc-base-dialog'].join(' '),

    /**
     * The following options are required and used for url state management. e.g., when Splunk restarts
     * @option operation (string) - operation being performed
     * @option appName (string) - app name
     * @option appVersion (string) -app version
     */
    initialize(options) {
        this.operation = this.options.operation || this.operation;
        this.appName = this.options.appName || this.appName;
        this.appVersion = this.options.appVersion || this.appVersion;
        if (this.appVersion) {
            this.appVersionLabel = ` (${splunkUtils.sprintf(_('version %s').t(), _.escape(this.appVersion))})`;
        } else {
            this.appVersionLabel = '';
        }

        if (this.model.auth) {
            this.listenTo(this.model.auth, 'change:consent', this.toggleLoginButton.bind(this));
            this.listenTo(this.model.auth, 'login:fail', this.enableLoginButton.bind(this));
            this.listenTo(this.model.auth, 'invalid', this.disableLoginButton.bind(this));
        }
        BaseDialog.prototype.initialize.call(this, options);
    },

    setUrlParams() {
        const attr = {
            appLabel: this.appName,
            appVersion: this.appVersion,
            operation: this.operation,
        };

        urlHelper.replaceState(attr);
    },

    removeUrlParams() {
        urlHelper.removeUrlParam('operation');
        urlHelper.removeUrlParam('appLabel');
        urlHelper.removeUrlParam('appVersion');
    },

    onPrimFnSuccess(...args) {
        if (this.willDeploy) {
            this.setUrlParams();
        }
        BaseDialog.prototype.onPrimFnSuccess.apply(this, args);
    },

    onDeploySuccess() {
        this.removeUrlParams();
        BaseDialog.prototype.onDeploySuccess.call(this);
    },

    onDeployFail() {
        this.removeUrlParams();
        BaseDialog.prototype.onDeployFail.call(this);
    },

    getLoginState() {
        return {
            title: this.getLoginTitle(),
            childrenArr: this.getLoginChildren(),
            footerArr: this.getLoginFooterBtns(),
            renderCB: this.getLoginPostRenderFn.bind(this),
        };
    },

    getLoginChildren() {
        const bodyHtml = this.children.loginStateChildren.render().el;

        return [bodyHtml];
    },

    getLoginFooterBtns() {
        let btns;
        if (this.model.auth.get('consent')) {
            btns = [BaseDialog.BUTTON_CANCEL, this.BUTTON_LOGIN];
        } else {
            btns = [BaseDialog.BUTTON_CANCEL, this.BUTTON_LOGIN_DISABLED];
        }
        return btns;
    },

    getLoginPostRenderFn() {
        this.$('.username-placeholder').find('input').focus();
    },

    getFailChildren(response) {
        let errorMsg = response &&
                       response.responseJSON &&
                       response.responseJSON.error &&
                       response.responseJSON.error.message;

        errorMsg = errorMsg || this.GENERIC_ERROR_MSG;

        // Missing capability case
        // todo: Ask backend to change error object return in this case
        if (_.isObject(errorMsg) && _.has(errorMsg, 'missing_capabilities')) {
            errorMsg = this.MISSING_CAPABILITIES_MSG;
        } else if (errorMsg.includes('AppInstall_UnsupportedDeployment')) {
            errorMsg = UNSUPPORTED_DEPLOYMENT_MSG;
        } else if (_.isArray(errorMsg)) {
            errorMsg = this.handleMultipleErrorsResponse(errorMsg);
        }

        return [$(`<div> ${errorMsg} </div>`)];
    },

    handleMultipleErrorsResponse(errorMsgs) {
        return _.template(this.multipleErrorMessagesTemplate)({
            errorMsgs,
            MULTIPLE_SERVER_ERROR_MSG,
        });
    },

    toggleLoginButton() {
        if (this.model.auth.get('consent')) {
            this.enableLoginButton();
        } else {
            this.disableLoginButton();
        }
    },

    enableLoginButton() {
        this.$('.modal-btn-login').removeClass('disabled');
        this.$('.modal-btn-login').prop('disabled', false);
    },

    disableLoginButton() {
        this.$('.modal-btn-login').addClass('disabled');
        this.$('.modal-btn-login').prop('disabled', true);
    },

    /**
     * Return a confirmation message
     * @operationLabels     An array of words describing the operation, with different tenses and capitalization.
     *                      Refer to message templates and calling examples.
     *
     */
    getConfirmBodyHTMLForOperation(operationLabels) {
        const manifest = this.model.appRemote && this.model.appRemote.get('manifest');

        const showSHCWarning = this.options.isSHC && !(
            manifest &&
            manifest.supportedDeployments && (
                _.contains(manifest.supportedDeployments, '_search_head_clustering') ||
                _.contains(manifest.supportedDeployments, '*')
            )
        );

        return splunkUtils.sprintf(
            CONFIRM_MSG_TEMPLATE,
            operationLabels[0],
            _.escape(this.appName),
            _.escape(this.appVersionLabel),
            showSHCWarning ? SHC_WARNING_MSG : '',
            operationLabels[1],
        );
    },

    multipleErrorMessagesTemplate: `
        <p><%= MULTIPLE_SERVER_ERRORS %></p>
        <ul>
            <% _.each(errorMsgs, function(msg) { %>
            <li><%- msg %></li>
            <% }) %>
        </ul>
    `,
}, {
    CONFIRM_MSG_TEMPLATE,
    IN_PROGRESS_MSG_TEMPLATE,
    GENERIC_ERROR_MSG_TEMPLATE,
    MISSING_CAPABILITIES_MSG_TEMPLATE,
    DEPLOY_FAIL_MSG_TEMPLATE,
});
