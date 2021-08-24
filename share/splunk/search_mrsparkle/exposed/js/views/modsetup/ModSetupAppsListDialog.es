/**
 * This dialog displays the list of app dependencies and also a warning if any of the dependencies can not be configured
 * using modsetup
 */
import _ from 'underscore';
import Backbone from 'backbone';
import Modal from 'views/shared/Modal';
import ControlGroup from 'views/shared/controls/ControlGroup';
import splunkUtils from 'splunk.util';
import './ModSetupAppsListDialog.pcss';


export default Modal.extend({

    initialize(options) {
        Modal.prototype.initialize.apply(this, options);

        const appsWithSetup = this.model.appsModel.get('apps').filter(obj => obj.hasSetup && !obj.parentApp);
        this.model.list = new Backbone.Model({ apps: _.pluck(appsWithSetup, 'value') });
        this.children.list = new ControlGroup({
            label: _('Apps list').t(),
            controlType: 'CheckboxGroup',
            controlOptions: {
                model: this.model.list,
                modelAttribute: 'apps',
                items: appsWithSetup,
            },
        });
    },

    events: {
        'click .btn-primary': 'nextClicked',
    },

    nextClicked(e) {
        e.preventDefault();
        const newApps = this.model.appsModel.get('apps').filter((item) => {
            if (_.contains(this.model.list.get('apps'), item.value) || item.parentApp) {
                return true;
            }
            return false;
        });
        this.model.appsModel.set('apps', newApps);
        this.trigger('appsSelected');
        this.hide();
    },

    // Returns the apps list that do not have a valid modsetup configuration.
    getAppsWithoutSetup() {
        return _.pluck(this.model.appsModel.get('apps').filter(obj => !obj.hasSetup), 'label');
    },

    render() {
        this.$el.html(Modal.TEMPLATE);
        this.$(Modal.HEADER_TITLE_SELECTOR).html(_.escape(_('Select apps to configure').t()));

        this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);

        // List message
        const appStr = _('<span class="app-name">%s</span> ' +
            'requires the following dependencies. Select one or more of the following apps to configure them now.').t();
        const parentApp = this.model.appsModel.get('apps').find(item => item.parentApp === true);
        const listMessage = splunkUtils.sprintf(appStr, parentApp.label);

        const appsWithoutSetup = this.getAppsWithoutSetup();
        this.$(Modal.BODY_FORM_SELECTOR).html(this.compiledTemplate({
            message: listMessage,
            appsWithoutSetupList: appsWithoutSetup,
            missingSetupMessage: _('You cannot configure the following dependencies at this time.' +
                ' Check the App Listing page to see if any of the following apps need additional setup.').t(),
        }));
        this.children.list.render().appendTo(this.$('.mod-setup-apps-list'));
        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_NEXT);
        this.$(`.${Modal.BUTTON_CLOSE_CLASS}`).remove();
    },

    template: '<%= message %>' +
        '<div class="mod-setup-apps-list">' +
        '</div>' +
        '<% if (appsWithoutSetupList && appsWithoutSetupList.length > 0) { %>' +
            '<p> <%- missingSetupMessage %></p>' +
            '<ul class="modsetup-missing-setup-app">' +
                '<% _.each(appsWithoutSetupList, function(app) { %>' +
                    '<li> <%- app %></li>' +
                '<% });%>' +
            '</ul>' +
        '<% } %>',

});
