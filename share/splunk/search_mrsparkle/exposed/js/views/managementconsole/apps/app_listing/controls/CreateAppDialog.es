import $ from 'jquery';
import _ from 'underscore';
import splunkdUtils from 'util/splunkd_utils';
import splunkUtil from 'splunk.util';
import FlashMessagesCollection from 'collections/shared/FlashMessages';
import Modal from 'views/shared/Modal';
import ControlGroup from 'views/shared/controls/ControlGroup';
import FlashMessagesView from 'views/shared/FlashMessagesLegacy';
import 'views/managementconsole/apps/app_listing/controls/CreateAppDialog.pcss';

const ERROR_MESSAGES = {
    AppCreateFromTemplate_AlreadyExists: _('App ID <b>%s</b> already exists.').t(),
    AppCreateFromTemplate_Fail: _('App Creation Failed: ' +
        'Contact your administrator for details or try again later.').t(),
    AppCreateFromTemplate_NoTemplate: _('Invalid template provided.').t(),
    AppCreateFromTemplate_AppIDConflict: _('App has the same ID as a public app.' +
        'Update this app with a unique ID to remove this conflict.').t(),
    AppCreateFromTemplate_BadVersion: _('Invalid version provided.').t(),
    BadNameError: _('App ID cannot contain special characters.').t(),
    NoAppIDError: _('Enter <b>App ID</b> for your app.').t(),
    NoAppVersionError: _('Enter <b>Version</b> for your app.').t(),
    DefaultMessage: _('App Creation Failed: ' +
        'Contact your administrator for details or try again later.').t(),
};
const SUCCESS_MESSAGE = _('<b>%s</b> (version %s) was created successfully!').t();
const SAVE = _('Save').t();
const CANCEL = _('Cancel').t();
const CLOSE = _('Close').t();

const SAVE_BUTTON = '<a href="#" class="btn btn-primary modal-btn-primary pull-right save-close-btn"> %s </a>';
const CANCEL_BUTTON = '<a href="#" class="btn cancel modal-btn-cancel cancel-btn" data-dismiss="modal"> %s </a>';

export default Modal.extend({
    moduleId: module.id,

    initialize(options) {
        Modal.prototype.initialize.call(this, options);
        this.flashMessagesCollection = new FlashMessagesCollection();
        this.flashMessagesView = new FlashMessagesView({
            collection: this.flashMessagesCollection,
            escape: false,
        });

        this.setUpModalView();
    },

    setUpModalView() {
        this.label = new ControlGroup({
            controlType: 'Text',
            controlOptions: {
                additionalClassNames: 'label-control',
            },
            label: _('Name').t(),
            help: _('Friendly name for display in Splunk Web').t(),
        });

        this.name = new ControlGroup({
            controlType: 'Text',
            controlOptions: {
                additionalClassNames: 'name-control',
            },
            label: 'App ID*',
            help: _('Unique ID - can contain underscore and alphanumeric characters.').t(),
        });

        this.version = new ControlGroup({
            controlType: 'Text',
            controlOptions: {
                additionalClassNames: 'version-control',
            },
            label: _('Version*').t(),
            help: _('App version').t(),
        });

        this.visible = new ControlGroup({
            controlType: 'SyntheticRadio',
            controlOptions: {
                items: [
                    { label: _('Yes').t(), value: true },
                    { label: _('No').t(), value: false },
                ],
                additionalClassNames: 'visible-control',
            },
            label: _('Visible').t(),
            help: _('Only apps with views should be made visible').t(),
        });

        this.author = new ControlGroup({
            controlType: 'Text',
            controlOptions: {
                additionalClassNames: 'author-control',
            },
            label: _('Author').t(),
            help: _('Name of the app\'s owner').t(),
        });

        this.description = new ControlGroup({
            controlType: 'Textarea',
            controlOptions: {
                additionalClassNames: 'description-control',
            },
            label: _('Description').t(),
            help: _('Description for your app').t(),
        });

        this.template = new ControlGroup({
            controlType: 'SyntheticRadio',
            controlOptions: {
                items: [
                    { label: 'barebones', value: 'barebones_cloud' },
                    { label: 'sample app', value: 'sample_app_cloud' },
                ],
                additionalClassNames: 'template-control',
            },
            label: _('Template').t(),
            help: _('These templates contain example views and searches').t(),
        });

        // Set up defaults for visible, template and version fields
        this.visible.getAllControls()[0].buttonClicked(true);
        this.template.getAllControls()[0].buttonClicked('barebones_cloud');
        this.setValue(this.version, _('1.0.0').t());
    },

    setValue(control, value) {
        return control.getAllControls()[0].setValue(value);
    },

    getValue(control) {
        return control.getAllControls()[0].getValue() || undefined;
    },

    isInputValid(data) {
        if (data.name === undefined) {
            this.flashMessagesCollection.reset([{
                type: 'error',
                html: ERROR_MESSAGES.NoAppIDError,
            }]);
            this.name.error(true);
            this.name.getAllControls()[0].focus();
            return false;
        }

        const regex = /^[0-9a-zA-Z_-]+$/;
        if (!regex.test(data.name)) {
            this.flashMessagesCollection.reset([{
                type: 'error',
                html: ERROR_MESSAGES.BadNameError,
            }]);
            return false;
        }

        if (data.version === undefined) {
            this.flashMessagesCollection.reset([{
                type: 'error',
                html: ERROR_MESSAGES.NoAppVersionError,
            }]);
            this.version.error(true);
            this.version.getAllControls()[0].focus();
            return false;
        }

        return true;
    },

    events: $.extend(true, {}, Modal.prototype.events, {
        'click .btn-primary': function save(e) {
            e.preventDefault();
            if (this.$('.save-close-btn').text() === CLOSE) {
                this.hide();
                return;
            }

            this.name.error(false);
            this.version.error(false);

            const data = {
                name: this.getValue(this.name),
                label: this.getValue(this.label),
                version: this.getValue(this.version),
                visible: this.getValue(this.visible),
                author: this.getValue(this.author),
                description: this.getValue(this.description),
                template: this.getValue(this.template),
            };

            if (!this.isInputValid(data)) {
                return;
            }

            $.ajax({
                url: splunkdUtils.fullpath('dmc/apps-create'),
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(data),
                beforeSend: () => {
                    $('.save-close-btn').addClass('disabled');
                    $('.cancel-btn').addClass('disabled');
                },
                complete: (jqXhr, status) => {
                    if (status === 'success') {
                        this.flashMessagesCollection.reset([{
                            type: 'info',
                            html: splunkUtil.sprintf(SUCCESS_MESSAGE, data.name, data.version),
                        }]);
                        this.$('.save-close-btn').text(CLOSE);
                        // hide irrelevant control elements
                        this.$('.cancel-btn').hide();
                        this.label.hide();
                        this.name.hide();
                        this.version.hide();
                        this.visible.hide();
                        this.author.hide();
                        this.description.hide();
                        this.template.hide();
                    } else if (jqXhr.responseJSON.type === 'AppCreateFromTemplate_AlreadyExists' ||
                        jqXhr.responseJSON.type === 'AppCreateFromTemplate_AppIDConflict') {
                        this.flashMessagesCollection.reset([{
                            type: 'error',
                            html: splunkUtil.sprintf(ERROR_MESSAGES[jqXhr.responseJSON.type], data.name),
                        }]);
                        this.name.error(true);
                        this.name.getAllControls()[0].focus();
                    } else {
                        this.flashMessagesCollection.reset([{
                            type: 'error',
                            html: ERROR_MESSAGES[jqXhr.responseJSON.type] ||
                                ERROR_MESSAGES.DefaultMessage,
                        }]);
                    }

                    $('.save-close-btn').removeClass('disabled');
                    $('.cancel-btn').removeClass('disabled');
                },
            });
        },
    }),

    render() {
        this.$el.html(Modal.TEMPLATE);
        this.$(Modal.HEADER_TITLE_SELECTOR).html(_('Create App').t());

        this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);
        this.$(Modal.BODY_FORM_SELECTOR).append(this.flashMessagesView.render().el);

        this.$(Modal.BODY_FORM_SELECTOR).append(this.label.render().el);
        this.$(Modal.BODY_FORM_SELECTOR).append(this.name.render().el);
        this.$(Modal.BODY_FORM_SELECTOR).append(this.version.render().el);
        this.$(Modal.BODY_FORM_SELECTOR).append(this.visible.render().el);
        this.$(Modal.BODY_FORM_SELECTOR).append(this.author.render().el);
        this.$(Modal.BODY_FORM_SELECTOR).append(this.description.render().el);
        this.$(Modal.BODY_FORM_SELECTOR).append(this.template.render().el);

        this.$(Modal.FOOTER_SELECTOR).append(splunkUtil.sprintf(CANCEL_BUTTON, CANCEL));
        this.$(Modal.FOOTER_SELECTOR).append(splunkUtil.sprintf(SAVE_BUTTON, SAVE));

        return this;
    },
});
