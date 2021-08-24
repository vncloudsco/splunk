/**
 * @author stewarts
 * @date 12/13/16
 *
 * Confirmation Dialog for Search Head Clustering
 * captaincy transfer
 */

import _ from 'underscore';
import $ from 'jquery';
import splunkUtils from 'splunk.util';
import FlashMessagesView from 'views/shared/FlashMessages';
import Modal from 'views/shared/Modal';
import WaitSpinner from 'views/shared/waitspinner/Master';
import './TransferCaptain.pcss';

const BUTTON_RESTART = splunkUtils.sprintf(
    '<a href="#" class="btn btn-primary modal-btn-primary pull-right transfer-captain-btn"> %s </a>',
    _('Start Transfer').t(),
);

export default Modal.extend({
    moduleId: module.id,

    /**
     * Opens a Dialog to initiate search head clustering captaincy transfer
     *
     * @param {object} options
     * @param {string} options.targetCaptainName - Name of the target captain to be displayed on dialog
     * @param {Backbone Collection} options.collection - collection of entities
     * @param {Backbone Collection} options.collection.entities - collection of models
     * @param {Backbone Model} options.controller
     * @param {object} options.learnMoreLink
     */
    initialize(options) {
        this.model = this.model || {};
        this.targetCaptainName = options.targetCaptainName || '';
        this.collection = options.collection;
        this.model.controller = options.controller;
        this.children.learnMoreLink = options.learnMoreLink;

        if (!this.collection) {
            throw new Error('this.collection is required');
        }

        this.children.spinner = new WaitSpinner();
        this.children.spinner.$el.addClass('pull-right');

        this.children.flashMessages = new FlashMessagesView({
            model: [this.collection.entities],
        });

        Modal.prototype.initialize.call(this, options);
        this.listenTo(this.collection.entities, 'serverValidated', this.checkServerValidated);
        this.listenTo(this.model.controller, 'showCaptainTransferSuccess', this.showTransferSuccess);
    },

    events: $.extend({}, Modal.prototype.events, {
        'click .transfer-captain-btn': function transferCaptainClickHandler(e) {
            this.model.controller.trigger('beginTransferCaptaincy');
            e.preventDefault();
            this.showInProgress();
        },
    }),

    checkServerValidated(isValid) {
        if (!isValid) {
            $('.captain-warning-container').hide();
            this.children.spinner.stop();
            this.children.spinner.$el.hide();
            this.showCancelButtons();
        }
    },

    showInProgress() {
        this.$(`${Modal.FOOTER_SELECTOR} .btn`).hide();
        this.$(`${Modal.HEADER_SELECTOR} .close`).hide();
        this.children.spinner.start();
        this.children.spinner.$el.show();
    },

    showTransferSuccess() {
        this.children.spinner.stop();
        this.children.spinner.$el.hide();
        this.$('.captain-warning-container').hide();

        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CLOSE);
        this.$('.captain-success-container').show();
        this.$(`${Modal.HEADER_SELECTOR} .close`).show();
    },

    showCancelButtons() {
        this.$(`${Modal.FOOTER_SELECTOR} .modal-btn-cancel`).show();
        this.$(`${Modal.HEADER_SELECTOR} .close`).show();
    },

    render() {
        this.$el.html(Modal.TEMPLATE);
        this.$(Modal.HEADER_TITLE_SELECTOR).html(_('Transfer Captain').t());

        const targetCaptainName = this.targetCaptainName;

        this.$(Modal.BODY_SELECTOR).append(this.children.flashMessages.render().el);

        this.$(Modal.BODY_SELECTOR).append(
            _(this.bodyTemplate).template({
                learnMoreLink: this.children.learnMoreLink,
                linkClass: 'external learn-more-link',
                targetCaptainName,
            }),
        );

        this.$(Modal.FOOTER_SELECTOR).append(BUTTON_RESTART);
        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL_PULL_RIGHT);

        this.$(Modal.FOOTER_SELECTOR).append(this.children.spinner.render().el);
        this.children.spinner.$el.hide();

        return this;
    },

    bodyTemplate: `
        <div class="flash-messages-view-placeholder"></div>
        <div class="captain-warning-container">
            <p>
                <i class="icon-alert"></i>
                <%= _("Here are some details about what will happen if you choose to continue.").t() %>
                <a class="<%- linkClass %>" href="<%- learnMoreLink %>" target="_blank"><%= _("Learn More").t() %></a>
            </p>
            <p><%= _("Are you sure you want to transfer captain to").t() %> <b><%= targetCaptainName %>?</b></p>
        </div>

        <div class="captain-success-container hide">
            <p><i class="icon-check-circle"></i> <%= _("Captain transferred successfully.").t() %> </p>
        </div>
    `,
});
