import _ from 'underscore';
import $ from 'jquery';
import splunkUtils from 'splunk.util';
import DMCBaseDialog from 'views/managementconsole/apps/app_listing/actionflows/DMCBase';
import LoginView from '../Login';

const LOGIN_UPDATE_LABEL = _('Login and Update').t();
const BUTTON_LOGIN_DISABLED = `<button class="btn btn-primary modal-btn-login pull-right disabled" disabled>
    ${LOGIN_UPDATE_LABEL}</button>`;

const BUTTON_LOGIN = `<button class="btn btn-primary modal-btn-login pull-right">
    ${LOGIN_UPDATE_LABEL}</button>`;

export default DMCBaseDialog.extend({
    className: [DMCBaseDialog.prototype.className, 'dmc-update-dialog'].join(' '),

    initialize(...args) {
        this.appCanUpdate = this.model.app.canUpdate();
        this.appName = this.model.app.getAppLabel();
        this.appVersion = this.model.app.getVersion();
        this.operation = 'update';

        // Login Step Body
        this.children.loginStateChildren = new LoginView({
            model: {
                auth: this.model.auth,
                app: this.model.app,
            },
            operation: this.operation,
        });

        DMCBaseDialog.prototype.initialize.apply(this, args);

        const operationLabel = _('uninstall').t();
        this.GENERIC_ERROR_MSG = splunkUtils.sprintf(DMCBaseDialog.GENERIC_ERROR_MSG_TEMPLATE, operationLabel);
        this.MISSING_CAPABILITIES_MSG = splunkUtils.sprintf(DMCBaseDialog.MISSING_CAPABILITIES_MSG_TEMPLATE,
             operationLabel);

        this.listenTo(this.model.auth, 'login:success', this.triggerUpdate.bind(this));
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
    }),

    triggerUpdate() {
        this.model.app.entry.content.set('auth', this.model.auth.get('sbsessionid'));
        this.executePrimaryFn();
    },

    getLoginTitle() {
        return _('Login and Update').t();
    },

    getConfirmTitle() {
        let title;
        if (this.appCanUpdate) {
            title = _('Update - Confirm').t();
        } else {
            title = _('Update - Contact Splunk Support').t();
        }
        return title;
    },

    getConfirmBodyHTML() {
        let bodyHtml;
        if (this.appCanUpdate) {
            const operationLabels = [_('update').t(), _('Updating').t()];
            bodyHtml = this.getConfirmBodyHTMLForOperation(operationLabels);
        } else {
            bodyHtml = splunkUtils.sprintf(_('You cannot update <b>%s</b> (version %s) \n' +
                    'by using self-service app installation. To update this app, contact Splunk Support.').t(),
                _.escape(this.appName),
                _.escape(this.appVersion),
            );
        }
        return bodyHtml;
    },

    getConfirmFooter() {
        let btns;
        if (this.appCanUpdate) {
            btns = [DMCBaseDialog.BUTTON_CANCEL, DMCBaseDialog.BUTTON_CONTINUE];
        } else {
            btns = [DMCBaseDialog.BUTTON_CLOSE];
        }
        return btns;
    },

    getInProgressTitle() {
        return _('Update - In Progress').t();
    },

    getInProgressBodyHTML() {
        const operationLabel = _('updating').t();

        return splunkUtils.sprintf(DMCBaseDialog.IN_PROGRESS_MSG_TEMPLATE,
            operationLabel,
            _.escape(this.appName),
            _.escape(this.appVersionLabel),
        );
    },

    getSuccessTitle() {
        return _('Update - Complete').t();
    },

    getSuccessBodyHTML() {
        const operationLabel = _('updated').t();

        let html = splunkUtils.sprintf(_('Splunk Cloud %s <b>%s</b>.').t(),
            operationLabel,
            _.escape(this.appName),
        );

        if (this.options.willDeploy) {
            html += _('Verify the status of the deployment by clicking Last Deployment Status.').t();
        }

        return html;
    },

    getFailTitle() {
        return _('Update - Fail').t();
    },

    getDeployFailBodyHTML() {
        const operationLabel = _('updated').t();

        return splunkUtils.sprintf(DMCBaseDialog.DEPLOY_FAIL_MSG_TEMPLATE,
            _.escape(this.appName),
            _.escape(this.appVersionLabel),
            operationLabel,
        );
    },
});
