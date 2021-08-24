/**
 * Mod setup view is responsible for :
 *
 *  1) Rendering the html content specified in the app
 *  2) Reading handler( js and css) and setting up the handlers.
 *  3) validating and saving the values.
 *
 *
 *  Events: listens to 'setup:viewActive'
 */

import $ from 'jquery';
import _ from 'underscore';
import BaseModel from 'models/Base';
import BaseView from 'views/Base';
import HtmlFormDataBindWithDelegate from 'views/shared/databind/HtmlFormDataBindWithDelegate';
import ModHandlerHelpers from 'helpers/modsetup/ModHandlersHelper';
import ModSetupDataHelper from 'helpers/modsetup/ModSetupDataHelper';
import './ModSetup.pcss';

const PREFIX = 'setup';

export default BaseView.extend({

    initialize(options) {
        BaseView.prototype.initialize.call(this, options);
        let modHandlersHelperOptions = {};

        this.options = options || {};

        // Create instance of data helper with bundleId and prefix
        this.setupDataHelper = new ModSetupDataHelper(
            this.options.bundleId, PREFIX, this.options.configuration.isDMCEnabled);

        this.tabsConfig = []; // stores tabs info
        this.setupProperties = this.options.configuration.json; // UI properties to stanzas map
        this.setupHtml = this.options.configuration.html;

        // Target model for html form handler
        this.model.target = new BaseModel();

        this.createFormViews();

        // Loads the JS and CSS files if provided in the app . If no FormHandler is provided in the app
        // Then the base SplunkFormHandle is instantiated
        if (!_.isUndefined(this.options.supportedExtensions)) {
            modHandlersHelperOptions = {
                supportedExtensions: this.options.supportedExtensions,
            };
        }
        this.modHandlers = new ModHandlerHelpers(modHandlersHelperOptions);
        const $deferred = this.modHandlers.initialize({
            bundle: this.options.bundleId,
            path: '/static/app',
        });

        // Wait for the attributes and the (js css) files to be loaded
        $.when($deferred).done(() => {
            this.updateViewWithDefaultValues();
        });
    },

    events: {
        'click a[data-toggle]': 'tabClicked',
        // Handle navigating to the first tab that has errors
        'setup:viewActive': 'viewActive',
    },

    tabClicked(e) {
        e.preventDefault();
        const $target = $(e.currentTarget);
        const type = $target.data().type;
        const newTabConfig = _.find(this.tabsConfig, config => config.id === type);

        _(this.children.form.$el.find('.mod-parent > form')).each((child) => {
            $(child).hide();
        });
        this.children.form.$el.find(`[section-label="${newTabConfig.label}"]`).show();
        this.$el.find('.nav > li').removeClass('active');
        $target.parent().addClass('active');
    },

    viewActive() {
        const item = _.find(this.tabsConfig, (config) => {
            const el = $(`li.${config.id} i`);
            if (el) {
                return el.is(':visible');
            }
            return false;
        });

        if (item) {
            $(`li.${item.id} a`).click();
        }
    },

    /**
     * If the properties in conf files already had value , we populate the associated UI field
     * with the values from the stanza files
     */
    updateViewWithDefaultValues() {
        // Build all the models/collections for the configuration
        $.when(this.setupDataHelper.manageConfigurations(this.setupProperties, this.setupHtml)).done(() => {
            // Fetch default values and load on the target model
            this.model.target.set(this.setupDataHelper.getDefaultValues());
            this.children.form.registerDelegate(this.modHandlers.handler);
            this.children.form.writeFormValues();
            this.children.form.readFormValues();
        });
    },

    /**
     * If multiple forms are specified in the setup.html then multiple tabs will be rendered in the UI.
     * This method creates the configuration for each tab and creates the HtmlFormData element.
     *
     * @private
     */
    createFormViews() {
        const html = this.options.configuration.html;
        const formElements = $(html).filter('form');
        _.each(formElements, (element, index) => {
            let label = $(element).attr('section-label');
            if (!label) {
                label = `${_('Section').t()} ${index}`;
            }

            const config = {
                label,
                id: label.replace(/ /g, '_'),
            };

            this.tabsConfig.push(config);
        });

        this.children.form = new HtmlFormDataBindWithDelegate({
            className: 'tab-pane',
            model: {
                application: this.model.application,
                target: this.model.target,
            },
            html,
            attributePrefix: PREFIX,
            entityReference: `${PREFIX}:`,
        });
    },

    /**
     * Adds an error icon on the tab when the elements in the tab has errors
     * @param errors
     */
    showErrors() {
        _.each(this.tabsConfig, (item) => {
            const tabErrors = this.$el.find(`[section-label="${item.label}"]`).find('.mod-setup-error-message');
            if (tabErrors.length > 0) {
                this.$el.find(`li.${item.id} .icon-alert`).show();
            }
        });
    },

    /**
     * Clears all the errors on the tabs
     */
    clearErrors() {
        this.$el.find('.main-tabs li .icon-alert').hide();
    },

    /**
     * Clears the errors on the tabs and validate form again.
     * @returns {Array}
     */
    validateAllForms() {
        let errors = [];
        this.clearErrors();
        errors = errors.concat(this.children.form.validateForm());
        if (errors.length > 0) {
            this.showErrors(errors);
        }
        return errors;
    },

    /**
     * Save the UI values to the stanzas
     *
     * @returns {*}
     */
    save() {
        this.children.form.save();
        return this.setupDataHelper.save(this.model.target.toJSON(), PREFIX);
    },

    render() {
        this.$el.append(this.compiledTemplate({
            config: this.tabsConfig,
            useTabs: this.tabsConfig.length !== 1,
            bundleId: this.options.bundleId,
        }));

        this.children.form.render().$el.appendTo(this.$el.find('.tab-content'));
        this.children.form.$el.find('form')
            .hide()
            .filter(':first-child')
            .show();
        this.$el.find(`.${this.tabsConfig[0].id}`).addClass('active');
        return this;
    },

    template:
        `
        <div class="content-body">
            <% if(useTabs) { %>
            <ul class="nav nav-tabs main-tabs">
                <% _.each(config, function(item) { %>
                <li class="<%- item.id %>">
                    <a href="#<%- item.id %>" data-toggle="tab" data-type="<%- item.id %>">
                        <%- item.label %>
                        <i class="icon-alert" style="display: none"></i>
                    </a>
                </li>
                <% }); %>
            </ul>
            <% } %>
            <div class="tab-content">
            </div>
        </div>
        `,
});
