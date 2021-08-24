import _ from 'underscore';
import $ from 'jquery';
import DMCBaseDialog from 'views/managementconsole/apps/app_listing/actionflows/DMCBase';
import splunkUtils from 'splunk.util';

const ERROR_STATUS = {
    dependencyConflict: 5,
};

export default DMCBaseDialog.extend({
    className: [DMCBaseDialog.prototype.className, 'dmc-uninstall-dialog'].join(' '),

    initialize(...args) {
        this.appName = this.model.app.getAppLabel();
        this.appVersion = this.model.app.getVersion();
        this.operation = 'uninstall';

        DMCBaseDialog.prototype.initialize.apply(this, args);

        const operationLabel = _('uninstall').t();
        this.GENERIC_ERROR_MSG = splunkUtils.sprintf(DMCBaseDialog.GENERIC_ERROR_MSG_TEMPLATE, operationLabel);
        this.MISSING_CAPABILITIES_MSG = splunkUtils.sprintf(DMCBaseDialog.MISSING_CAPABILITIES_MSG_TEMPLATE,
            operationLabel);
    },

    getConfirmTitle() {
        return _('Uninstall - Confirm').t();
    },

    getConfirmBodyHTML() {
        const operationLabels = [_('uninstall').t(), _('Uninstalling').t()];

        return splunkUtils.sprintf(DMCBaseDialog.CONFIRM_MSG_TEMPLATE,
            operationLabels[0],
            _.escape(this.appName),
            _.escape(this.appVersionLabel),
            operationLabels[1],
        );
    },

    // why does this request succeed if the expected behavior (status code 5) is to fail?
    onPrimFnSuccess(response) {
        if (response.status === ERROR_STATUS.dependencyConflict) {
            this.onPrimFnFail(response);
        } else {
            DMCBaseDialog.prototype.onPrimFnSuccess.call(this, response);
        }
    },

    getInProgressTitle() {
        return _('Uninstall - In Progress').t();
    },

    getInProgressBodyHTML() {
        const operationLabel = _('uninstalling').t();

        return splunkUtils.sprintf(DMCBaseDialog.IN_PROGRESS_MSG_TEMPLATE,
            operationLabel,
            _.escape(this.appName),
            _.escape(this.appVersionLabel),
        );
    },

    getSuccessTitle() {
        return _('Uninstall - Complete').t();
    },

    getSuccessBodyHTML() {
        const operationLabel = _('uninstalled').t();

        let html = splunkUtils.sprintf(_('Splunk Cloud %s <b>%s</b>%s. ').t(),
            operationLabel,
            _.escape(this.appName),
            _.escape(this.appVersionLabel),
        );

        if (this.options.willDeploy) {
            html += _('Verify the status of the deployment by clicking Last Deployment Status.').t();
        }

        return html;
    },

    getFailTitle() {
        return _('Uninstall - Fail').t();
    },

    getFailChildren(response) {
        // Dependencies required case
        if (response.status === ERROR_STATUS.dependencyConflict) {
            const requiredAppStr = _.map(response.required_apps, app => app.app_title).join(', ');
            const errorMsg = splunkUtils.sprintf(_('<b>%s</b> (version %s) could not be uninstalled \n' +
                'because it is required by the following apps: <b>%s<b>.').t(),
                _.escape(this.appName),
                _.escape(this.appVersion),
                _.escape(requiredAppStr),
            );
            return [$(`<div> ${errorMsg} </div>`)];
        }
        return DMCBaseDialog.prototype.getFailChildren.call(this, response);
    },

    getDeployFailBodyHTML() {
        const operationLabel = _('uninstalled').t();

        return splunkUtils.sprintf(DMCBaseDialog.DEPLOY_FAIL_MSG_TEMPLATE,
            _.escape(this.appName),
            _.escape(this.appVersionLabel),
            operationLabel,
        );
    },
});
