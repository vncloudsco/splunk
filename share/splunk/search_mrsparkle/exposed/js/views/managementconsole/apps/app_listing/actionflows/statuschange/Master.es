import _ from 'underscore';
import DMCBaseDialog from 'views/managementconsole/apps/app_listing/actionflows/DMCBase';
import splunkUtils from 'splunk.util';

export default DMCBaseDialog.extend({
    className: [DMCBaseDialog.prototype.className, 'dmc-status-change-dialog'].join(' '),

    initialize(...args) {
        this.isDisabled = this.options.isDisabled;
        DMCBaseDialog.prototype.initialize.apply(this, args);

        this.GENERIC_ERROR_MSG = (() => {
            const operationLabel = this.isDisabled
                ? _('enable').t()
                : _('disable').t();

            return splunkUtils.sprintf(DMCBaseDialog.GENERIC_ERROR_MSG_TEMPLATE, operationLabel);
        })();

        this.MISSING_CAPABILITIES_MSG = (() => {
            const operationLabel = this.isDisabled
                ? _('enable').t()
                : _('disable').t();

            return splunkUtils.sprintf(DMCBaseDialog.MISSING_CAPABILITIES_MSG_TEMPLATE, operationLabel);
        })();
    },

    getConfirmTitle() {
        return this.isDisabled
            ? _('Enable - Confirm').t()
            : _('Disable - Confirm').t();
    },

    getConfirmBodyHTML() {
        const operationLabels = this.isDisabled
            ? [_('enable').t(), _('Enabling').t()]
            : [_('disable').t(), _('Disabling').t()];

        return splunkUtils.sprintf(DMCBaseDialog.CONFIRM_MSG_TEMPLATE,
            operationLabels[0],
            _.escape(this.appName),
            _.escape(this.appVersionLabel),
            operationLabels[1],
        );
    },

    getInProgressTitle() {
        return this.isDisabled
            ? _('Enable - In Progress').t()
            : _('Disable - In Progress').t();
    },

    getInProgressBodyHTML() {
        const operationLabel = this.isDisabled
            ? _('enabling').t()
            : _('disabling').t();

        return splunkUtils.sprintf(DMCBaseDialog.IN_PROGRESS_MSG_TEMPLATE,
            operationLabel,
            _.escape(this.appName),
            _.escape(this.appVersionLabel),
        );
    },

    getSuccessTitle() {
        return this.isDisabled
            ? _('Enable - Complete').t()
            : _('Disable - Complete').t();
    },

    getSuccessBodyHTML() {
        const operationLabel = this.isDisabled
            ? _('enabled').t()
            : _('disabled').t();

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
        return this.isDisabled
            ? _('Enable - Fail').t()
            : _('Disable - Fail').t();
    },

    getDeployFailBodyHTML() {
        const operationLabel = this.isDisabled
            ? _('enabled').t()
            : _('disabled').t();

        return splunkUtils.sprintf(DMCBaseDialog.DEPLOY_FAIL_MSG_TEMPLATE,
            _.escape(this.appName),
            _.escape(this.appVersionLabel),
            operationLabel,
        );
    },
});
