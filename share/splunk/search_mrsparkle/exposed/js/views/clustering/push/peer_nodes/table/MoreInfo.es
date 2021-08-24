import BaseView from 'views/Base';
import ActionsModel from 'models/clustering/Actions';

export default BaseView.extend({
    moduleId: module.id,
    tagName: 'tr',
    className: 'more-info',

    /**
     * @param {Object} options {
     *     model: {
     *          peer: <models.services.cluster.master.Peer>,
     *          pushModel: <Backbone.Model>
     *     },
     *     index: <index_of_the_row>,
     *     colSpan: <columns_to_span>
     * }
     */
    initialize(...args) {
        BaseView.prototype.initialize.apply(this, args);
        this.$el.addClass((this.options.index % 2) ? 'even' : 'odd').css('display', 'none');
        this.activate();
    },
    render() {
        this.$el.html(this.compiledTemplate({
            activeChecksum: this.model.peer.entry.content.get('active_bundle_id'),
            latestChecksum: this.model.peer.entry.content.get('latest_bundle_id'),
            lastValidatedChecksum: this.model.peer.entry.content.get('last_validated_bundle'),
            cols: this.options.colSpan,
            actions: ActionsModel.actions,
        }));
        return this;
    },
    template: `
        <td class="details" colspan="<%= cols %>">
            <dl class="list-dotted">
                <dt class="active-checksum"><%- _("Active Bundle ID").t() %>
                    <dd class="active-checksum">
                        <%- activeChecksum %>
                    </dd>
                </dt>
                <dt class="latest-checksum"><%- _("Latest Bundle ID").t() %>
                    <dd class="latest-checksum">
                        <%- latestChecksum %>
                    </dd>
                </dt>
                <% if (this.model.pushModel.get('lastRunAction') === actions.CHECK_RESTART) { %>
                    <dt class="last-validated-checksum"><%- _("Last Validated Bundle ID").t() %>
                        <dd class="last-validated-checksum">
                            <%- lastValidatedChecksum %>
                        </dd>
                    </dt>
                <% } %>
            </dl>
        </td>
    `,
});
