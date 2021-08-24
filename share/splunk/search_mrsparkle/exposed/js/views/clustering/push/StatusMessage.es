import _ from 'underscore';
import BaseView from 'views/Base';
import Spinner from 'views/shared/waitspinner/Master';

export default BaseView.extend({
    moduleId: module.id,

    initialize(...args) {
        BaseView.prototype.initialize.apply(this, args);
        this.listenTo(this.model.masterInfo.entry.content, 'change:apply_bundle_status', this.render);
        this.firstRender = true;
        this.children.spinner = new Spinner();
    },

    getStatusMessage() {
        const applyBundleStatus = this.model.masterInfo.entry.content.get('apply_bundle_status');
        let message = applyBundleStatus && applyBundleStatus.status;

        if (message === 'None' || _.isUndefined(message)) {
            if (this.firstRender) {
                message = 'Initializing...';
                this.firstRender = false;
            } else {
                message = '';
            }
        }
        return message;
    },

    render() {
        const statusMessage = this.getStatusMessage();
        const html = this.compiledTemplate({
            applyBundleStatusMessage: statusMessage,
        });
        if (statusMessage) {
            this.$el.html(html);
        }
        this.children.spinner.render().appendTo(this.$('.wait-spinner'));
        this.children.spinner.start();
        return this;
    },

    template: `
        <div class="section-padded">
            <div class="wait-spinner"></div>
            <h3 class="bundle-status-message">
                <%- applyBundleStatusMessage %>
            </h3>
        </div>
    `,
});
