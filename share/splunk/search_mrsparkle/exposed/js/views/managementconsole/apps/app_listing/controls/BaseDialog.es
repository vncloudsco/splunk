import _ from 'underscore';
import $ from 'jquery';
import Backbone from 'backbone';
import Modal from 'views/shared/Modal';
import splunkUtils from 'splunk.util';
import urlHelper from 'helpers/managementconsole/url';
import DeployModel from 'models/managementconsole/Deploy';
import 'views/managementconsole/apps/app_listing/actionflows/Base.pcss';

const CONTINUE = splunkUtils.sprintf(_('Continue').t());
const RETRY = splunkUtils.sprintf(_('Retry').t());
const MODAL_RETRY_BTN = `<a href="#" class="btn btn-primary modal-btn-primary retry-deploy">${RETRY}</a>`;
const ERROR_MSGS = {
    MULTIPLE_SERVER_ERRORS: _('The following server errors were reported: ').t(),
};

export default Modal.extend({
    className: [Modal.prototype.className, 'base-dialog', 'dmc-base-dialog'].join(' '),

    initialize(options) {
        _.defaults(options, {
            onHiddenRemove: true,
            backdrop: 'static',
            keyboard: false,
        });

        Modal.prototype.initialize.call(this, options);

        // will move out once we refactor code
        this.model = this.model || {};
        this.model.deploy = new DeployModel();

        this.request = {
            state: null,
            isComplete() {
                return this.state === 'complete';
            },
            complete() {
                this.state = 'complete';
            },
            running() {
                this.state = 'running';
            },
        };

        // this store should never be physically manipulated
        // use setState and setInitialState instead
        this.state = {
            title: '',
            children: [],
            footerBtns: [],
            postRenderFn: null,
        };

        this.state = new Backbone.Model(this.state);
        this.state.on('change', this.render);
    },

    events: $.extend({}, Modal.prototype.events, {
        'click .retry-deploy': function retry(e) {
            e.preventDefault();

            this.retryDeploy();
        },
    }),

    retryDeploy() {
        this.executeAction(
            this.model.deploy.deploy.bind(this.model.deploy),
            this.primFnSuccessCB.bind(this),
            this.primFnFailCB.bind(this),
        );
    },

    setInitialState(state) {
        this.setState(state, { silent: true });
    },

    setState(state, options) {
        this.state.set(state, options);
    },

    setUrlParams(appLabel, appVersion, operation) {
        const attr = { appLabel, appVersion, operation };

        urlHelper.replaceState(attr);
    },

    removeUrlParams() {
        urlHelper.removeUrlParam('operation');
        urlHelper.removeUrlParam('appLabel');
        urlHelper.removeUrlParam('appVersion');
    },

    render() {
        this.$el.html(Modal.TEMPLATE);

        this.$(Modal.HEADER_TITLE_SELECTOR).html(this.state.get('title'));

        _.each(this.state.get('children'), (child) => {
            this.$(Modal.BODY_SELECTOR).append(child);
        }, this);

        _.each(this.state.get('footerBtns'), (button) => {
            this.$(Modal.FOOTER_SELECTOR).append(button);
        }, this);

        const postRenderFn = this.state.get('postRenderFn');
        if (postRenderFn) {
            postRenderFn();
        }

        return this;
    },

    // will move out when we refactor code
    executeAction(primFn, successCB, failCB) {
        this.request.running();
        // timeout used to remove flicker
        setTimeout(() => {
            if (!this.request.isComplete()) {
                this.setState(this.getInProgressState());
                this.setUrlParams(this.appName, this.appVersion, this.operation);
            }
        }, 200);

        primFn().done(successCB).fail(failCB);
    },

    getInProgressState() {
        return {
            title: this.getInProgressTitle(),
            children: this.getInProgressChildren(),
            footerBtns: this.getInProgressFooterBtns(),
            postRenderFn: this.getInProgressPostRenderFn.bind(this),
        };
    },

    getInProgressFooterBtns() {
        return [];
    },

    getInProgressPostRenderFn() {
        this.$(Modal.BUTTON_CLOSE_SELECTOR).remove();

        this.waitspinner.start();
    },

    getDeployFailState(appName, appVersion) {
        const CLOSE_BTN_PULL_LEFT = $(Modal.BUTTON_CLOSE)
            .removeClass('pull-right')
            .addClass('pull-left');

        const bodyHtml = splunkUtils.sprintf(this.DEPLOY_FAIL_TEMPLATE,
            _.escape(appName),
            _.escape(appVersion),
        );

        return {
            title: this.getFailTitle(),
            children: [$(`<div> ${bodyHtml} </div>`)],
            footerBtns: [CLOSE_BTN_PULL_LEFT, MODAL_RETRY_BTN],
            postRenderFn: this.getCompletePostRenderFn.bind(this),
        };
    },
    // Post render function for both success and fail states
    getCompletePostRenderFn() {
        this.removeUrlParams();
        this.appendButtonCloseX();
    },

    appendButtonCloseX() {
        // if BUTTON_CLOSE_X already exists, dont append
        if (this.$(Modal.BUTTON_CLOSE_SELECTOR).length) return;

        this.$(Modal.HEADER_SELECTOR).append(Modal.BUTTON_CLOSE_X);
    },

    handleMultipleErrorsResponse(errorMsgs) {
        return _.template(this.multipleErrorMessagesTemplate)({
            errorMsgs,
            MULTIPLE_SERVER_ERRORS: ERROR_MSGS.MULTIPLE_SERVER_ERRORS,
        });
    },

    multipleErrorMessagesTemplate: `
        <p><%= MULTIPLE_SERVER_ERRORS %></p>
        <ul>
            <% _.each(errorMsgs, function(msg) { %>
            <li><%- msg %></li>
            <% }) %>
        </ul>
    `,
},
    {
        BUTTON_CONTINUE: `<a href="#" class="btn btn-primary modal-btn-continue
        pull-right">${CONTINUE}</a>`,
        BUTTON_CANCEL: Modal.BUTTON_CANCEL,
        BUTTON_CLOSE: Modal.BUTTON_CLOSE,
    },
);
