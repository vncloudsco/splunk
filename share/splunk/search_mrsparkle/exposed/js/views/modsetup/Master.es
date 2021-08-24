/**
 * This view loops through all the mod setup configurations proovided in the app in its dependencies.
 * Each app is rendered in using the ModSetup view. This method also handles validating and saving.
 */

import _ from 'underscore';
import $ from 'jquery';
import Backbone from 'backbone';
import BaseView from 'views/Base';
import SplunkUtil from 'splunk.util';
import WaitSpinner from 'views/shared/waitspinner/Master';
import ModSetupView from 'views/modsetup/ModSetup';
import FlashMessagesLegacyView from 'views/shared/FlashMessagesLegacy'; // TO-DO see if new FlashMessages could be used
import FlashMessagesCollection from 'collections/shared/FlashMessages';
import ModSetupAppsListDialog from './ModSetupAppsListDialog';
import './Master.pcss';


export default BaseView.extend({

    initialize(...args) {
        BaseView.prototype.initialize.apply(this, args);
        this.children.waitSpinner = new WaitSpinner();
        this.collection.flashMessages = new FlashMessagesCollection();
        this.children.flashMessagesView = new FlashMessagesLegacyView({
            collection: this.collection.flashMessages,
        });
        this.children.setup = []; // holds the setup for each app
        this.children.waitSpinner.start();
        this.children.waitSpinner.$el.hide();
        this.compiledSuccessTemplate = _.template(this.successTemplate);

        this.model.appsModel = new Backbone.Model();
        this.model.appsModel.set('apps', this.options.configurationManager.apps);
        if (this.options.configurationManager.apps.length > 1) {
            this.children.dialog = new ModSetupAppsListDialog({
                configurationManager: this.options.configurationManager,
                backdrop: 'static',
                keyboard: false,
                onHiddenRemove: true,
                model: {
                    appsModel: this.model.appsModel,
                },
            });
            this.listenTo(this.children.dialog, 'appsSelected', this.createSetupViews);
        }
    },

    events: {
        'click .mod-setup-save': 'saveClicked',
        'click .app-tab': 'leftTabClicked',
    },

    leftTabClicked(e) {
        e.preventDefault();
        const $target = $(e.currentTarget);
        const type = $target.find('a').data().type;

        _(this.children.setup).each((child) => {
            if (child.id === type) {
                child.view.$el.show();
                child.view.$el.trigger('setup:viewActive');
            } else {
                child.view.$el.hide();
            }
        });
        this.$el.find('.nav-tabs-left > li').removeClass('active');
        $target.addClass('active');
    },

    /**
     * Create new modsetupView for the bundleId. This view renders the html for the configuration.
     * @param bundleId
     */
    instantiateModSetupView(bundleId) {
        const modSetupViewOptions = {
            configuration: this.options.configurationManager.configurations[bundleId],
            bundleId,
            model: {
                application: this.model.application,
            },
            collection: {},
        };
        if (!_.isUndefined(this.options.supportedExtensions)) {
            modSetupViewOptions.supportedExtensions =
                this.options.supportedExtensions;
        }
        return new ModSetupView(modSetupViewOptions);
    },

    /**
     * Loops throught all the apps that are selected to be configured and views are instantiated
     */
    createSetupViews() {
        _.each(this.model.appsModel.get('apps'), (item) => {
            this.children.setup.push({
                id: item.value,
                view: this.instantiateModSetupView(item.value),
                appLabel: item.label,
            });
        });

        this.renderSetupViews();
    },

    /**
     * When next is clicked we validate all the mod setup's . If all the forms are valid then we save
     * the changes made by user.
     *
     * @param dfd
     * @param wizardControl
     */
    saveClicked(e) {
        e.preventDefault();
        const errors = this.validateAllForms();
        if (errors.length > 0) {
            // Addition show error stuff
        } else {
            // save all models and collections and get the dererreds
            const deferreds = this.saveAllForms();
            this.children.waitSpinner.$el.show();
            // disable save button
            this.$('.mod-setup-save').removeClass('enabled').addClass('disabled');

            $.when(...deferreds).then(() => {
                // On save of all configurations
                // 1) Update is_configured in app.conf
                // 2) redirect to default app page or show success screen
                $.when(...this.saveIsConfigured()).always(() => {
                    this.reloadConfigurations();
                });
            }).fail((errorsList) => {
                // Show error messages and hide loading indicator
                this.onSaveFailed(errorsList);
            });
        }
    },

    /**
     * set is_configured to true if the app is not configured.
     * @returns {Array}
     */
    saveIsConfigured() {
        const deferreds = [];
        _.each(this.model.appsModel.get('apps'), (item) => {
            const configuration = this.options.configurationManager.configurations[item.value];
            if (!SplunkUtil.normalizeBoolean(configuration.isConfiguredModel.entry.content.get('is_configured'))) {
                configuration.isConfiguredModel.entry.content.set('is_configured', true);
                deferreds.push(configuration.isConfiguredModel.save({}));
            }
        });
        return deferreds;
        // TO-DO Handle failure?
    },

    /**
     * Reload the configurations so splunk is aware of the new changes . Once the configuration has been reloaded
     * we redirect the user if a redirect url exists else we show a success screen.
     */
    reloadConfigurations() {
        const deferreds = [];
        _.each(this.model.appsModel.get('apps'), (item) => {
            const configuration = this.options.configurationManager.configurations[item.value];
            deferreds.push(configuration.isConfiguredModel.reloadAppConfigurations());
        });

        $.when(...deferreds).always(() => {
            this.children.waitSpinner.$el.hide();
            // In case redirect exist
            const redirectUrl = this.model.classicurl.get('redirect_override');
            // SPL-140395: We need to ensure the redirect_override has a valid form
            // before we redirect, otherwise XSS is possible
            const validRedirect = redirectUrl &&
                _.isString(redirectUrl) &&
                redirectUrl.charAt(0) === '/' &&
                redirectUrl.charAt(1) !== '\\' &&
                redirectUrl.charAt(1) !== '/';

            if (validRedirect) {
                window.location.href = redirectUrl;
            } else {
                this.$el.find('.main-section').html(this.compiledSuccessTemplate({
                    message: _('Splunk Web successfully saved your configuration.').t(),
                }));
            }
        });

        // TO-DO handle reload failure?
    },

    // Add errors to the page and disable loading weel and enable save button.
    onSaveFailed(errors) {
        this.children.waitSpinner.$el.hide();
        this.$('.mod-setup-save').removeClass('disabled').addClass('enabled');
        this.formatErrors(errors);
        this.collection.flashMessages.reset();
        this.collection.flashMessages.add(errors);
    },

    formatErrors(errors) {
        _.each(errors, (er) => {
            const error = er;
            if (error.text) {
                error.html = error.text;
            }
            delete error.text;
        });
    },

    /**
     * Validate all the form elements
     * @returns {Array}
     */
    validateAllForms() {
        let errors = [];
        this.clearErrors();
        _.each(this.children.setup, (item) => {
            errors = errors.concat(item.view.validateAllForms());
        });

        if (errors.length > 0) {
            this.showErrors();
        }

        return errors;
    },

    showErrors() {
        _.each(this.children.setup, (item) => {
            if (item.view.$el.find('.mod-setup-error-message').length > 0) {
                this.$el.find(`.nav-tabs-left li.${item.id} .icon-alert`).show();
            }
        });
    },

    clearErrors() {
        this.$el.find('.nav-tabs-left li .icon-alert').hide();
    },

    /**
     * Save all the forms
     * @returns {Array}
     */
    saveAllForms() {
        const deferreds = [];
        _.each(this.children.setup, (item) => {
            deferreds.push(item.view.save());
        });

        return deferreds;
    },

    render() {
        this.$el.html(this.compiledTemplate({}));

        this.children.waitSpinner.render().appendTo(this.$('.wait-spinner'));
        if (this.options.configurationManager.apps.length > 1) {
            this.children.dialog.render().appendTo($('body'));
            this.children.dialog.show();
        } else {
            this.createSetupViews();
        }

        this.$('.flash-messages-placeholder').append(this.children.flashMessagesView.render().el);
        return this;
    },

    renderSetupViews() {
        let parentEl = null;
        if (this.model.appsModel.get('apps').length > 1) {
            this.$el.find('.main-section').html(_(this.templateWithTabs).template({
                setups: this.children.setup,
            }));
            parentEl = this.$el.find('.tab-content');
        } else {
            this.$el.find('.main-section').html(_(this.templateWithoutTabs).template({
                setups: this.children.setup,
            }));
            parentEl = this.$el.find('.mod-setup-content');
        }
        _.each(this.children.setup, (item) => {
            item.view.render().$el.appendTo(parentEl);
            item.view.$el.hide();
        });

        this.children.setup[0].view.$el.show();
    },

    template: `
        <div class="section-header section-padded">
            <div>
                <span class="wait-spinner pull-right"></span>
                <button class="pull-right btn btn-primary mod-setup-save"><%- _("Save configuration").t() %></button>
            </div>
            <h3 class="section-title"><%- _("Setup").t() %></h3>
            <p class="description"><%- _("Provide initial configurations for the app").t() %></p>
            <div class="flash-messages-placeholder"></div>
            <div clas="clearfix"></div>
        </div>
        <div class="main-section">
    `,

    templateWithoutTabs: '<div class="mod-setup-content"></div>',

    templateWithTabs: `
        <ul class="nav nav-tabs-left">
            <% _(setups).each((setup, i) => { %>
                <li class="<%= i === 0 ? "active" : "" %> app-tab  <%- setup.id %>"</li>
                    <a href="#" data-toggle="tab" data-type="<%- setup.id %>">\
                        <%- setup.appLabel %>
                        <i class="icon-alert" style="display: none"></i>
                    </a>
                </li>
            <% }) %>
        </ul>
        <div class="tab-content">
    `,

    successTemplate: `<div class="success-section">
            <div class="success-header">
                <h3><%- message %></h3>
            </div>
        </div>`,

});
