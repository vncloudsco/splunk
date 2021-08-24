import _ from 'underscore';
import $ from 'jquery';
import Backbone from 'backbone';
import Modal from 'views/shared/Modal';
import splunkUtils from 'splunk.util';
import DeployModel from 'models/managementconsole/Deploy';
import WaitSpinner from 'views/shared/waitspinner/Master';
import 'views/managementconsole/apps/app_listing/actionflows/Base.pcss';

const CONTINUE = splunkUtils.sprintf(_('Continue').t());
const MODAL_BUTTON_CONTINUE = `<a href="#" class="btn btn-primary modal-btn-continue
pull-right">${CONTINUE}</a>`;
const RETRY = splunkUtils.sprintf(_('Retry').t());
const MODAL_RETRY_BTN = `<a href="#" class="btn btn-primary modal-btn-primary modal-btn-retry">${RETRY}</a>`;

/**
 * Base Action Flow View (author: Ricky Tran)
 *
 * The goal of this view is to provide an abstraction for actions that trigger a dialog flow within Splunk. A simple
 * usage example could be an action flow that requires:
 *      1) Confirmation Step
 *      2) In Progress Step (task is deploying?)
 *      3) Completion step
 *
 * Options supported:
 *      @option bool willDeploy (required) - whether the primary function call (primFn) will deploy and require
 *       an in progress step
 *      @option function primFn (required) - primary function that will get called on confirmation. optionally return a
 *      promise
 *      @option function getSuccessPromises (optional) - function that returns an array of promises to wait on before
 *      dialog shows success state. (e.g., may want to refetch a model or collection before showing success step)
 *      @option string customInitialState (optional) - the name (string) of the function that should be called to
 *      set the initial state. the function should follow the setState interface specified below.
 *
 * Usage:
 * Out of the box, this view will take care of the confirmation, in progress, and completion step. Based on the action
 * being performed, you may want to change the title, body contents, and footer buttons, or even add a few more steps.
 * To accomplish this, simply modify:
 *  - get<STEP>Title (string)
 *  - get<STEP>BodyHTML (html string) or get<STEP>Children (array of jQuery elements)
 *  - get<STEP>Footer (array of jQuery button elements)
 *
 * To add custom steps, simply call 'setState,' passing an object with the following properties:
 *  - title (string)
 *  - childrenArr (array of jQuery elements to be appended to body)
 *  - footerArr (array of jQuery button elements to be appended to footer)
 *  - renderCB (optional callback that is invoked after rendering. this can be useful if some extra logic,
 *    starting a waitspinner, needs to be performed)
 */
export default Modal.extend({
    className: [Modal.prototype.className, 'base-dialog'].join(' '),

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

        this.primFn = this.primFn || this.options.primFn;
        this.willDeploy = this.options.willDeploy;
        this.getSuccessPromises = this.getSuccessPromises || this.options.getSuccessPromises;

        // this store should never be physically manipulated
        // use setState and setInitialState instead
        this.state = {
            title: '',
            children: [],
            footerBtns: [],
        };

        this.state = new Backbone.Model(this.state);
        this.listenTo(this.state, 'change', this.render);

        // confirm step is always first
        const customInitialState = this.options.customInitialState || this.customInitialState;
        const initialStateFn = this[customInitialState] || this.getConfirmState;
        this.setInitialState(initialStateFn.call(this));
    },

    events: $.extend({}, Modal.prototype.events, {
        'click .modal-btn-continue': function next(e) {
            e.preventDefault();
            if (!_.isFunction(this.primFn)) throw new Error('No primary function passed');

            this.executePrimaryFn();
        },
        'click .modal-btn-retry': function next(e) {
            e.preventDefault();

            this.model.deploy.deploy()
                .done(this.onPrimFnSuccess.bind(this))
                .fail(this.onPrimFnFail.bind(this));
        },
    }),

    setInitialState(state) {
        this.setState(state, { silent: true });
    },

    setState(state, options) {
        this.state.set(state, options);
    },

    executePrimaryFn() {
        $.when(this.primFn())
            .done(this.onPrimFnSuccess.bind(this))
            .fail(this.onPrimFnFail.bind(this));
    },

    // if the action triggers a deploy -> start polling on task passed back in response
    onPrimFnSuccess(response) {
        if (this.willDeploy) {
            this.setState(this.getInProgressState());

            const taskId = response.entry[0].name;
            this.model.deployTask.entry.set('name', taskId);
            const pollDeployTask = () => {
                this.model.deployTask.beginPolling()
                    .done(this.onDeploySuccess.bind(this))
                    .fail(this.onDeployFail.bind(this));
            };

            pollDeployTask();
            this.model.deployTask.on('serverValidated', (success, context, messages) => {
                const netErrorMsg = _.find(messages, msg =>
                    msg.type === 'network_error',
                );
                if (netErrorMsg) {
                    pollDeployTask();
                }
            }, this);
        } else {
            this.handleSuccess();
        }
    },

    onPrimFnFail(response) {
        this.setState(this.getFailState(response));
    },

    onDeploySuccess() {
        this.handleSuccess();
    },

    onDeployFail() {
        this.handleDeployFail();
    },

    // if getSuccessPromises function is defined -> invoke and wait on promises until setting success state
    handleSuccess() {
        let successPromises = [];
        if (!_.isUndefined(this.getSuccessPromises) && _.isFunction(this.getSuccessPromises)) {
            successPromises = this.getSuccessPromises();
        }
        if (!_.isArray(successPromises)) throw new Error('Expected success promises to be an array');

        $.when(...successPromises).done(() => {
            this.setState(this.getSuccessState());
        });
    },

    handleDeployFail() {
        this.setState(this.getDeployFailState());
    },

    /* START OF CONFIRM STATE */
    getConfirmState() {
        return {
            title: this.getConfirmTitle(),
            childrenArr: this.getConfirmChildren(),
            footerArr: this.getConfirmFooter(),
        };
    },

    getConfirmTitle() {
        return _('Default Confirm Title').t();
    },

    getConfirmChildren() {
        const html = this.getConfirmBodyHTML();
        return [$(`<div>${html}</div>`)];
    },

    getConfirmBodyHTML() {
        return _('Default confirm message').t();
    },

    getConfirmFooter() {
        return [Modal.BUTTON_CANCEL, MODAL_BUTTON_CONTINUE];
    },

    /* END OF CONFIRM STATE */

    /* START OF IN PROGRESS STATE */
    getInProgressState() {
        return {
            title: this.getInProgressTitle(),
            childrenArr: this.getInProgressChildren(),
            footerArr: this.getInProgressFooter(),
            renderCB: this.getInProgressRenderCB.bind(this),
        };
    },

    getInProgressTitle() {
        return _('Default In Progress Title').t();
    },

    getInProgressChildren() {
        this.waitspinner = new WaitSpinner({
            color: 'green',
            size: 'medium',
            frameWidth: 19,
        });

        const html = this.getInProgressBodyHTML();
        const bodyElem = $(`<div> ${html} </div>`);
        return [bodyElem, this.waitspinner.render().el];
    },

    getInProgressBodyHTML() {
        return _('Default in progress message').t();
    },

    getInProgressFooter() {
        return [];
    },

    getInProgressRenderCB() {
        this.$(Modal.BUTTON_CLOSE_SELECTOR).remove();
        this.waitspinner.start();
    },
    /* END OF IN PROGRESS STATE */

    /* START OF SUCCESS STATE */
    getSuccessState() {
        return {
            title: this.getSuccessTitle(),
            childrenArr: this.getSuccessChildren(),
            footerArr: this.getSuccessFooter(),
            renderCB: this.getSuccessRenderCB(),
        };
    },

    getSuccessTitle() {
        return _('Default Success Title').t();
    },

    getSuccessChildren() {
        const html = this.getSuccessBodyHTML();
        return [$(`<div>${html}</div>`)];
    },

    getSuccessBodyHTML() {
        return _('Default success msg').t();
    },

    getSuccessFooter() {
        return [Modal.BUTTON_CLOSE];
    },

    getSuccessRenderCB() {
        return this.appendButtonCloseX.bind(this);
    },
    /* END OF SUCCESS STATE */

    /* START OF FAIL STATE */
    getFailState(response) {
        return {
            title: this.getFailTitle(),
            childrenArr: this.getFailChildren(response),
            footerArr: this.getFailFooter(),
        };
    },

    getFailTitle() {
        return _('Default Fail Title').t();
    },

    // user can define own fail body html or specify a msg
    getFailChildren(response) {
        const html = this.getFailBodyHTML(response);
        return [$(`<div>${html}</div>`)];
    },

    getFailBodyHTML() {
        return _('Default fail message').t();
    },

    getFailFooter() {
        return [Modal.BUTTON_CLOSE];
    },
    /* END OF FAIL STATE */

    /* START OF DEPLOY FAIL STATE */
    getDeployFailState() {
        return {
            title: this.getFailTitle(), // re uses fail title
            childrenArr: this.getDeployFailChildren(),
            footerArr: this.getDeployFailFooter(),
            renderCB: this.getDeployFailRenderCB(),
        };
    },

    getDeployFailChildren() {
        const html = this.getDeployFailBodyHTML();
        return [$(`<div>${html}</div>`)];
    },

    getDeployFailBodyHTML() {
        return _('Default deploy fail message').t();
    },

    getDeployFailFooter() {
        return [Modal.BUTTON_CLOSE, MODAL_RETRY_BTN];
    },

    getDeployFailRenderCB() {
        return this.appendButtonCloseX.bind(this);
    },
    /* END OF DEPLOY FAIL STATE */

    appendButtonCloseX() {
        // if BUTTON_CLOSE_X already exists, dont append
        if (this.$(Modal.BUTTON_CLOSE_SELECTOR).length) return;

        this.$(Modal.HEADER_SELECTOR).append(Modal.BUTTON_CLOSE_X);
    },

    render() {
        this.$el.html(Modal.TEMPLATE);

        this.$(Modal.HEADER_TITLE_SELECTOR).html(this.state.get('title'));

        _.each(this.state.get('childrenArr'), (child) => {
            this.$(Modal.BODY_SELECTOR).append(child);
        }, this);

        _.each(this.state.get('footerArr'), (button) => {
            this.$(Modal.FOOTER_SELECTOR).append(button);
        }, this);

        const renderCB = this.state.get('renderCB');
        if (!_.isUndefined(renderCB)) {
            if (!_.isFunction(renderCB)) throw new Error('Expected function for render callback');

            renderCB();
        }

        return this;
    },
},
    {
        BUTTON_CONTINUE: MODAL_BUTTON_CONTINUE,
        BUTTON_CANCEL: Modal.BUTTON_CANCEL,
        BUTTON_CLOSE: Modal.BUTTON_CLOSE,
    },
);
