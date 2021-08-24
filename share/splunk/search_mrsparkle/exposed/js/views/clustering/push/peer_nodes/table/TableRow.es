import _ from 'underscore';
import BaseView from 'views/Base';
import PeerModel from 'models/services/cluster/master/Peer';

export default BaseView.extend({
    moduleId: module.id,
    tagName: 'tr',
    className: 'expand',

    /**
     * @param {Object} options {
     *     model: {
     *          peer: <models.services.cluster.master.Peer>,
     *          state: <Backbone.Model>,
     *          pushModel: <Backbone.Model>
     *     },
     *     index: <index_of_the_row>
     * }
     */
    initialize(...args) {
        BaseView.prototype.initialize.apply(this, args);
        this.$el.addClass((this.options.index % 2) ? 'even' : 'odd');
        this.activate();
    },
    getBundleActionStatus() {
        if (_.isUndefined(this.model.pushModel.get('lastRunAction'))) {
            return 'None';
        }
        const rawStatus = this.model.peer.entry.content.get('apply_bundle_status').status;
        switch (rawStatus) {
            case PeerModel.VALIDATED:
                return _('Validation Done').t();
            case PeerModel.RELOADING:
                return _('Reload In Progress').t();
            case PeerModel.CHECKING_RESTART:
                return _('Validating and Checking For Restart').t();
            default:
                return rawStatus;
        }
    },
    render() {
        this.$el.html(this.compiledTemplate({
            peerLabel: this.model.peer.entry.content.get('label'),
            site: this.model.peer.entry.content.get('site'),
            bundleActionStatus: this.getBundleActionStatus(),
            peerStatus: this.model.peer.entry.content.get('status'),
        }));
        return this;
    },
    template: `
        <td class="expands">
            <a href="#"><i class="icon-triangle-right-small"></i></a>
        </td>
        <td class="peer-label">
            <%- peerLabel %>
        </td>
        <td class="site">
            <%- site %>
        </td>
        <td class="peer-status">
            <%- peerStatus %>
        </td>
        <td class="actions-status">
            <%= bundleActionStatus %>
        </td>
    `,
});

