import _ from 'underscore';  // eslint-disable-line no-unused-vars
import $ from 'jquery';
import BaseView from 'views/Base';
import ConfirmDialog from 'views/clustering/push/ConfirmDialog';
import ActionsModel from 'models/clustering/Actions';

export default BaseView.extend({
    moduleId: module.id,

    initialize(...args) {
        BaseView.prototype.initialize.apply(this, args);
    },
    createConfirmDialog(action) {
        if (this.children.confirmDialog) {
            this.children.confirmDialog.remove();
        }
        this.children.confirmDialog = new ConfirmDialog({
            model: this.model,
            onHiddenRemove: true,
            action,
        });
        $('body').append(this.children.confirmDialog.render().el);
        this.children.confirmDialog.show();
    },
    disableButtons() {
        $('.action-btn').addClass('disabled');
    },
    enableButtons() {
        $('.action-btn').removeClass('disabled');
        this.disableUnavailableButtons();
    },
    disableUnavailableButtons() {
        const previousBundleChecksum = this.model.masterInfo.entry.content.get('previous_active_bundle').checksum;
        // Disable Rollback button if there is no previous bundle.
        if (!previousBundleChecksum) {
            $('.action-btn.rollback').addClass('disabled');
        }
    },
    events: {
        'click a.apply:not(.disabled)'(e) {  // eslint-disable-line object-shorthand
            e.preventDefault();
            this.createConfirmDialog(ActionsModel.actions.PUSH);
        },
        'click a.check-restart:not(.disabled)'(e) {  // eslint-disable-line object-shorthand
            e.preventDefault();
            this.createConfirmDialog(ActionsModel.actions.CHECK_RESTART);
        },
        'click a.rollback:not(.disabled)'(e) {  // eslint-disable-line object-shorthand
            this.createConfirmDialog(ActionsModel.actions.ROLLBACK);
            e.preventDefault();
        },
    },
    render() {
        this.$el.html(this.compiledTemplate({}));
        this.disableUnavailableButtons();
        return this;
    },
    template: `
        <div class="btn-toolbar">
            <a class="btn btn-primary action-btn check-restart" href="#"><%= _('Validate and Check Restart').t() %></a>
            <a class="btn btn-primary action-btn apply"><%= _('Push').t() %></a>
            <a class="btn btn-primary action-btn rollback" href="#"><%= _('Rollback').t() %></a>
        </div>
    `,
});
