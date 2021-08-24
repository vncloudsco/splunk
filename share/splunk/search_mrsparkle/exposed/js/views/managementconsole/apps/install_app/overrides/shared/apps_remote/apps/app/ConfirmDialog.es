import $ from 'jquery';
import _ from 'underscore';
import Modal from 'views/shared/Modal';
import splunkUtils from 'splunk.util';

const CONTINUE = splunkUtils.sprintf(_('Continue').t());
const BUTTON_CONTINUE = `<a href="#" class="btn btn-primary modal-btn-continue
pull-right" data-dismiss="modal">${CONTINUE}</a>`;

const CONFIRMATION_MSG_TEMPLATE = _('Are you sure you want to install \n' +
    '<b>%s</b> (version %s)? Installing this app might cause \n' +
    'Splunk Cloud to restart and be unavailable for some time.').t();

export default Modal.extend({
    moduleId: module.id,

    initialize(options) {
        _.defaults(options, {
            onHiddenRemove: true,
            backdrop: 'static',
            keyboard: false,
        });
        Modal.prototype.initialize.call(this, options);

        this.appName = this.model.appRemote.get('title');
        this.appVersion = this.model.appRemote.get('release').title;
    },

    events: $.extend({}, Modal.prototype.events, {
        'click .btn-primary': function onClick(e) {
            e.preventDefault();

            this.model.confirmation.trigger('installApp');
        },
    }),

    render() {
        const confirmationMsg = splunkUtils.sprintf(
            CONFIRMATION_MSG_TEMPLATE,
            _.escape(this.appName),
            _.escape(this.appVersion),
        );

        this.$el.html(Modal.TEMPLATE);
        this.$(Modal.HEADER_TITLE_SELECTOR).text(_('App Install - Confirm').t());
        this.$(Modal.BODY_SELECTOR).append(confirmationMsg);
        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
        this.$(Modal.FOOTER_SELECTOR).append(BUTTON_CONTINUE);
    },
});
