/**
 * @author stewarts
 * @date 02/03/17
 *
 * Dialog to be displayed when the SHC
 * status service_ready_flag is false
 */

import _ from 'underscore';
import WaitSpinner from 'views/shared/waitspinner/Master';
import Modal from 'views/shared/Modal';
import splunkUtil from 'splunk.util';

export default Modal.extend({
    moduleId: module.id,

    initialize(options) {
        this.children.spinner = new WaitSpinner();
        this.children.spinner.$el.addClass('pull-right');
        this.statusResponse = options.statusResponse;

        Modal.prototype.initialize.call(this, options);
    },

    render() {
        this.$el.html(Modal.TEMPLATE);
        this.$(Modal.HEADER_TITLE_SELECTOR).html(_('Search Head Clustering Service Not Ready').t());

        const bodyMessage = splunkUtil.sprintf(
            '<p> %s </p>', _('Please wait, the status of your search head cluster is not ready.').t(),
        );
        this.$(Modal.BODY_SELECTOR).append(bodyMessage);
        this.$(Modal.BUTTON_CLOSE_SELECTOR).remove();
        if (this.statusResponse) {
            const serviceString = splunkUtil.sprintf(_('Service ready flag: %s').t(), this.statusResponse.serviceReady);
            const restartString = splunkUtil.sprintf(_('Rolling restart in progress: %s').t(),
                                                        this.statusResponse.serviceReady);
            this.$(Modal.BODY_SELECTOR).append(`<p>${serviceString}</p>`);
            this.$(Modal.BODY_SELECTOR).append(`<p>${restartString}</p>`);
        }

        this.$(Modal.FOOTER_SELECTOR).append(this.children.spinner.render().el);
        this.children.spinner.start();
        this.children.spinner.$el.show();

        return this;
    },

});
