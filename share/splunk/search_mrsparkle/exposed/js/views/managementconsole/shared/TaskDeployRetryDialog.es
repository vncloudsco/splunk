import _ from 'underscore';
import $ from 'jquery';
import WaitSpinner from 'views/shared/waitspinner/Master';
import BaseDialog from 'views/managementconsole/apps/app_listing/controls/BaseDialog';
import splunkUtils from 'splunk.util';

const CONFIRMATION_TITLE = _('Deploy - Confirm').t();

export default BaseDialog.extend({
    moduleId: module.id,

    DEPLOY_FAIL_TEMPLATE: _('The previous deployment task failed. \n' +
        'You can retry the deployment task. \n' +
        'If this deployment task continues to fail, contact \n' +
        'Splunk Support.').t(),

    initialize(...args) {
        BaseDialog.prototype.initialize.apply(this, args);

        this.onDeployTaskSuccessCB = this.options.onDeployTaskSuccessCB;

        this.primFnSuccessCB = this.onDeploySuccess.bind(this);
        this.primFnFailCB = this.onDeployFail.bind(this);
        this.setInitialState(this.getInitialState());
    },

    events: $.extend({}, BaseDialog.prototype.events, {
        'click .confirm-deploy': function deploy(e) {
            e.preventDefault();

            this.retryDeploy();
        },
    }),

    onDeploySuccess(response) {
        this.setState(this.getInProgressState());
        const taskID = response.entry[0].name;
        this.model.task.entry.set('name', taskID);
        this.model.task.beginPolling()
            .done(this.onTaskSuccess.bind(this))
            .fail(this.onTaskFail.bind(this));
    },

    onDeployFail(response) {
        let errorMsg = response &&
                       response.responseJSON &&
                       response.responseJSON.error &&
                       response.responseJSON.error.message;

        errorMsg = errorMsg || this.DEPLOY_FAIL_TEMPLATE;

        this.setState({
            title: _('Deploy - Fail').t(),
            children: [$(`<div> ${errorMsg} </div>`)],
            footerBtns: [BaseDialog.BUTTON_CLOSE],
            postRenderFn: this.getCompletePostRenderFn,
        });
    },

    onTaskSuccess() {
        if (_.isFunction(this.onDeployTaskSuccessCB)) {
            this.onDeployTaskSuccessCB().done(() => {
                this.setState(this.getTaskSuccessState());
            });
        } else {
            this.setState(this.getTaskSuccessState());
        }
    },

    onTaskFail() {
        this.setState(this.getDeployFailState());
    },

    getInProgressTitle() {
        return _('Deploy - In Progress').t();
    },

    getInProgressChildren() {
        this.waitspinner = new WaitSpinner({
            color: 'green',
            size: 'medium',
            frameWidth: 19,
        });

        const bodyHtml = _('Splunk Cloud is retrying your \n' +
                'previous deployment task. This process might take several minutes and \n' +
                'cause Splunk Cloud to restart. Do not navigate away from this page \n' +
                'until the deployment process completes.').t();

        const bodyElem = $(`<div> ${bodyHtml} </div>`);
        return [bodyElem, this.waitspinner.render().el];
    },

    getInitialState() {
        return {
            title: this.getInitialTitle(),
            children: this.getInitialChildren(),
            footerBtns: this.getInitialFooterBtns(),
            postRenderFn: null,
        };
    },

    getInitialTitle() {
        return CONFIRMATION_TITLE;
    },

    getInitialChildren() {
        const bodyHtml = splunkUtils.sprintf(_('Are you sure that you want to \n' +
            'retry the previous deployment task? Deploying again might cause \n' +
            'Splunk Cloud to restart and be unavailable for some time.').t());
        return [$(`<div> ${bodyHtml} </div>`)];
    },

    getInitialFooterBtns() {
        const btnContinue = $(BaseDialog.BUTTON_CONTINUE);
        btnContinue.addClass('confirm-deploy');
        return [BaseDialog.BUTTON_CANCEL, btnContinue];
    },

    getTaskSuccessState() {
        return {
            title: this.getSuccessTitle(),
            children: this.getSuccessChildren(),
            footerBtns: this.getSuccessFooterBtns(),
            postRenderFn: null,
        };
    },

    getSuccessTitle() {
        return _('Deploy - Complete').t();
    },

    getSuccessChildren() {
        const bodyMsg = _('Your deploy was successful. Verify the status of the deployment \n' +
        'by clicking Last Deployment Status.').t();
        return [$(`<div> ${bodyMsg} </div>`)];
    },

    getSuccessFooterBtns() {
        return [BaseDialog.BUTTON_CLOSE];
    },

    getFailTitle() {
        return _('Deploy - Fail').t();
    },
});
