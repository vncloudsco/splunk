import $ from 'jquery';
import _ from 'underscore';
import BaseView from 'views/Base';
import TableHeadView from 'views/shared/TableHead';
import TableRow from 'views/clustering/push/peer_nodes/table/TableRow';
import TableDock from 'views/shared/delegates/TableDock';
import TableRowToggleView from 'views/shared/delegates/TableRowToggle';
import MoreInfo from 'views/clustering/push/peer_nodes/table/MoreInfo';

export default BaseView.extend({
    moduleId: module.id,

    /**
     * @param {Object} options {
     *     model:
     *          state: <Backbone.Model>
     *          application: <models.Application>,
     *     }
     *     collection: {
     *         peers: <collections.services.cluster.master.Peers>
     *     }
     * }
     */
    initialize(...args) {
        BaseView.prototype.initialize.apply(this, args);
        this.children.tableRowToggle = new TableRowToggleView({ el: this.el, collapseOthers: false });
        this.tableHeaders = [];
        this.tableHeaders.push({ label: _('i').t(), className: 'col-info', html: '<i class="icon-info"></i>' });
        this.tableHeaders.push({ label: _('Peer').t(), sortKey: 'label' });
        this.tableHeaders.push({ label: _('Site').t(), className: 'col-actions' });
        this.tableHeaders.push({ label: _('Status').t(), className: 'col-status' });
        this.tableHeaders.push({ label: _('Action Status').t(), className: 'col-action-status' });
        this.children.head = new TableHeadView({
            model: this.model.state,
            columns: this.tableHeaders,
        });
        this.children.rows = this.rowsFromCollection();
        this.activate();
        this.children.tableDock = new TableDock({
            el: this.el,
            offset: 36,
            dockScrollBar: false,
            defaultLayout: 'fixed',
            flexWidthColumn: 1,
        });
    },
    startListening() {
        this.listenTo(this.collection.peers, 'reset', this.updateAndRenderRows);
    },
    rowsFromCollection() {
        return _.flatten(
            this.collection.peers.map((model, i) => {  // eslint-disable-line arrow-body-style
                return [
                    new TableRow({
                        model: {
                            peer: model,
                            state: this.model.state,
                            pushModel: this.model.pushModel,
                        },
                        index: i,
                    }),
                    new MoreInfo({
                        model: {
                            peer: model,
                            pushModel: this.model.pushModel,
                        },
                        index: i,
                        colSpan: this.tableHeaders.length - 1,
                    }),
                ];
            }, this));
    },
    renderRows() {
        _(this.children.rows).each((row) => {
            row.render().appendTo(this.$('.peer-nodes'));
        }, this);
        this.children.tableDock.update();
    },
    updateAndRenderRows() {
        _(this.children.rows).each((row) => { row.remove(); }, this);
        this.children.rows = this.rowsFromCollection();
        this.renderRows();
    },
    render() {
        const $html = $(this.compiledTemplate({}));
        $html.find('.item-table-head-placeholder').replaceWith(this.children.head.render().el);
        this.$el.html($html);

        this.renderRows();
        return this;
    },
    template: `
        <table class="table table-chrome table-striped table-row-expanding table-listing">
        <thead class="item-table-head-placeholder"></thead>
        <tbody class="peer-nodes"></tbody>
        </table>
    `,
});
