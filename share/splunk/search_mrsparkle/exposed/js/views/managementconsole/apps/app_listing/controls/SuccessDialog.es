import _ from 'underscore';
import Modal from 'views/shared/Modal';
import splunkUtils from 'splunk.util';
import stringUtils from 'util/string_utils';
import 'views/managementconsole/apps/app_listing/actionflows/Base.pcss';

const OPS_PAST_TENSE = {
    install: 'installed',
    uninstall: 'uninstalled',
    update: 'updated',
    enable: 'enabled',
    disable: 'disabled',
};

export default Modal.extend({
    moduleId: module.id,
    className: [Modal.prototype.className, 'base-dialog'].join(' '),

    initialize(options) {
        _.defaults(options, {
            onHiddenRemove: true,
            backdrop: 'static',
            keyboard: false,
        });

        Modal.prototype.initialize.call(this, options);

        if (this.options.appVersion && this.options.operation !== 'update') {
            this.versionLabel = splunkUtils.sprintf(
                _(' (version %s)').t(),
                _.escape(this.options.appVersion),
            );
        } else {
            this.versionLabel = '';
        }
    },

    render() {
        this.$el.html(Modal.TEMPLATE);
        this.$(Modal.HEADER_TITLE_SELECTOR).html(splunkUtils.sprintf(
            _('%s - Completed').t(),
            _.escape(stringUtils.capitalize(this.options.operation)),
        ));

        this.$(Modal.BODY_SELECTOR).append(splunkUtils.sprintf(_('Splunk Cloud %s <b>%s</b>%s. \n' +
                'Verify the status of the deployment by clicking Last Deployment Status.').t(),
            _.escape(OPS_PAST_TENSE[this.options.operation]),
            _.escape(this.options.appLabel),
            _.escape(this.versionLabel),
        ));

        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CLOSE);

        return this;
    },
});
