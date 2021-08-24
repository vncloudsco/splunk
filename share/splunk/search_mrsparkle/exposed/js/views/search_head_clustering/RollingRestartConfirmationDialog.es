/**
 * @author stewarts
 * @date 01/30/17
 *
 * Rolling Restart confirmation dialog for SHC.
 */

import $ from 'jquery';
import _ from 'underscore';
import Modal from 'views/shared/Modal';
import FlashMessagesView from 'views/shared/FlashMessages';
import WaitSpinner from 'views/shared/waitspinner/Master';
import splunkUtil from 'splunk.util';
import SearchableSwitchView from './components/RollingDialog/Master';

const BUTTON_RESTART = splunkUtil.sprintf(
    '<a href="#" class="btn btn-primary modal-btn-primary pull-right restart-btn"> %s </a>', _('Restart').t(),
    );

export default Modal.extend({
    moduleId: module.id,

    /**
     * Opens a Dialog to initiate search head clustering rolling restart
     *
     * @param {object} options
     * @param {Backbone Collection} options.collection - collection of entities
     * @param {Backbone Collection} options.collection.entities - collection of models
     * @param {Backbone Model} options.controller
     * @param {object} options.learnMoreLink
     */
    initialize(options) {
        this.model = this.model || {};
        this.collection = this.collection || {};
        this.model.controller = options.controller;
        this.children.learnMoreLink = options.learnMoreLink;

        this.children.flashMessages = new FlashMessagesView({
            model: [this.collection.entities],
        });

        this.children.spinner = new WaitSpinner();
        this.children.spinner.$el.addClass('pull-right');

        Modal.prototype.initialize.call(this, options);

        this.listenTo(this.model.controller, 'rollingRestartInProgress', this.showRestartInProgress);
        this.listenTo(this.model.controller, 'rollingRestartSuccess', this.showRestartSuccess);
        this.listenTo(this.model.controller, 'rollingRestartError', this.showRestartError);
        this.listenTo(this.collection.entities, 'serverValidated', this.checkServerValidated);

        this.children.searchableSwitchView = new SearchableSwitchView({
            model: options.workingModel,
        });
    },

    events: $.extend({}, Modal.prototype.events, {
        'click .restart-btn': function rollingRestartClickHandler(e) {
            e.preventDefault();
            this.model.controller.trigger('beginRollingRestart');
        },
    }),

    checkServerValidated(isValid) {
        if (!isValid) {
            $('.restart-warning-container').hide();
            this.children.spinner.stop();
            this.children.spinner.$el.hide();
            this.showCancelButtons();
        }
    },

    showCancelButtons() {
        this.$(`${Modal.FOOTER_SELECTOR} .modal-btn-cancel`).show();
        this.$(`${Modal.HEADER_SELECTOR} .close`).show();
    },

    showRestartInProgress() {
        this.children.spinner.start();
        this.children.spinner.$el.show();
        this.$('.restart-progress-container').show();

        this.$('.restart-warning-container').hide();
        this.$(`${Modal.FOOTER_SELECTOR} .btn`).hide();
        this.$(`${Modal.HEADER_SELECTOR} .close`).hide();
        this.children.searchableSwitchView.$el.hide();
    },

    showRestartSuccess() {
        this.$(`${Modal.HEADER_SELECTOR} .close`).show();
        this.$('.restart-success-container').show();
        this.children.flashMessages.remove();
        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CLOSE);

        this.children.spinner.stop();
        this.children.spinner.$el.hide();
        this.$('.restart-progress-container').hide();
    },

    showRestartError(response) {
        this.$(`${Modal.HEADER_SELECTOR} .close`).show();
        if (!_.isUndefined(response) && !_.isUndefined(response.msg)) {
            this.$('.restart-error-container').html(
                splunkUtil.sprintf(_('<i class="icon-error"></i> %s').t(), response.msg),
            );
            this.$('.restart-error-container').show();
            this.children.flashMessages.remove();
            this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CLOSE);
        }

        this.children.spinner.stop();
        this.children.spinner.$el.hide();
        this.$('.restart-progress-container').hide();
    },

    render() {
        this.$el.html(Modal.TEMPLATE);
        this.$(Modal.HEADER_TITLE_SELECTOR).html(_.escape(_('Rolling Restart').t()));

        this.$(Modal.BODY_SELECTOR).append(_(this.bodyTemplate).template({
            learnMoreLink: this.children.learnMoreLink,
        }));

        this.children.flashMessages.render().appendTo(this.$('.flash-messages-view-placeholder'));

        this.$(Modal.BODY_SELECTOR).append(this.children.searchableSwitchView.activate({ deep: true }).render().$el);

        this.$(Modal.FOOTER_SELECTOR).append(BUTTON_RESTART);
        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL_PULL_RIGHT);

        this.$(Modal.FOOTER_SELECTOR).append(this.children.spinner.render().el);
        this.children.spinner.$el.hide();

        return this;
    },

    bodyTemplate: `
        <div class="flash-messages-view-placeholder" data-test="rolling-restart-error"></div>
        <div class="restart-warning-container">
            <p><i class="icon-alert"></i>
            <%= _('Are you sure you want to initiate a rolling restart? \
            Doing so will cause a phased restart of all cluster members,\
            with possible short-term inconvenience to current users.').t() %></p>
            <a class="external" href="<%- learnMoreLink %>" target="_blank"><%= _("Learn More").t() %></a>
        </div>
        <div class="restart-progress-container hide">
            <p><%= _('The rolling restart of your\
            search head cluster is currently in progress.').t()  %></p>
        </div>
        <div class="restart-success-container hide">
            <p>
                <i class="icon-check-circle"></i>
                <%= _('Your search head cluster has successfully been restarted.').t() %>
            </p>
        </div>
        <div class="restart-error-container hide">
            <p>
                <i class="icon-error"></i>
                <%= _('Searchable rolling restart cannot proceed due to health check failure. \
                For failure details, run <code>splunk show shcluster-status --verbose</code> on any member. \
                Fix this issue or use the force option to override health checks. \
                Use the force option with caution as it might impact searches during rolling restart.').t() %>
            </p>
        </div>
    `,
});
