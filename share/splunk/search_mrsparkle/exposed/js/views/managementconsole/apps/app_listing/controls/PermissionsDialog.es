import $ from 'jquery';
import _ from 'underscore';
import ACLReadOnlyModel from 'models/ACLReadOnly';
import Modal from 'views/shared/Modal';
import PermissionsView from 'views/shared/permissions/Master';
import 'views/shared/documentcontrols/dialogs/permissions_dialog/Master.pcss';

const modalDescription = _('Users with write access can share objects with \n' +
    'other users, while users with read access can save objects for \n' +
    'themselves only. Select Display For App or Display For All apps to \n' +
    'toggle whether these objects are available to this app only or to all apps.').t();

export default Modal.extend({
    moduleId: module.id,

    initialize(options) {
        _.defaults(options, {
            onHiddenRemove: true,
        });

        Modal.prototype.initialize.call(this, options);

        this.model = this.model || {};
        this.collection = this.collection || {};

        this.model.inmem = new ACLReadOnlyModel($.extend(true, {}, this.model.app.entry.acl.toJSON()));

        this.permissionsView = new PermissionsView({
            displayForLabel: _('Display For').t(),
            model: {
                inmem: this.model.inmem,
                user: this.model.user,
                serverInfo: this.model.serverInfo,
            },
            collection: this.collection.roles,
        });
    },

    events: $.extend(true, {}, Modal.prototype.events, {
        'click .btn-primary': function save(e) {
            e.preventDefault();

            const data = this.model.inmem.toDataPayload();
            this.model.app.acl.save({}, {
                data,
                success: () => {
                    this.hide();
                    this.model.app.fetch();
                },
            });
        },
    }),

    render() {
        this.$el.html(Modal.TEMPLATE);
        this.compiledDescriptionTemplate = _.template(this.descriptionTemplate);

        this.$(Modal.HEADER_TITLE_SELECTOR).html(_('Edit Permissions').t());

        this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);
        this.$(Modal.BODY_FORM_SELECTOR).append(this.compiledDescriptionTemplate({
            modalDescription,
        }));
        this.$(Modal.BODY_FORM_SELECTOR).append(this.permissionsView.render().el);

        if (this.model.inmem.get('can_change_perms')) {
            this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
            this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_SAVE);
        } else {
            this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CLOSE);
            this.$(Modal.FOOTER_SELECTOR).find('.modal-btn-close').addClass('pull-left');
        }

        return this;
    },

    descriptionTemplate: ' \n' +
    '<div class="modal-description permissions-description"> \n' +
        '<%- modalDescription %> \n' +
    '</div> \n ',
});
