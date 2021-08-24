/**
 * @author stewarts
 * @date 11/29/16
 *
 * Restart button to bring up a
 * Rolling Restart confirmation dialog.
 */

import BaseView from 'views/Base';

export default BaseView.extend({
    moduleId: module.id,

    render() {
        const html = this.compiledTemplate();
        this.$el.html(html);
        return this;
    },

    events: {
        'click .rolling-restart-button': function restartButtonClickHandler(e) {
            e.preventDefault();
            this.model.controller.trigger('openRollingRestartConfirmationDialog');
        },
    },

    template: '<a href="#" class="btn rolling-restart-button"><%- _("Begin Rolling Restart").t() %></a>',
});