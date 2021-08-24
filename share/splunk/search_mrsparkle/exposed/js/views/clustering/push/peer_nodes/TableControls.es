import $ from 'jquery';
import _ from 'underscore';
import BaseView from 'views/Base';
import Paginator from 'views/shared/CollectionPaginator';
import SyntheticSelectControl from 'views/shared/controls/SyntheticSelectControl';

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

        // Select the number of results per page
        // SyntheticSelectControl.js is based on Control.js, which has setValue() and getValue() methods
        // that could help us set or get "x per page" property.
        // When setting the 'value', the 'value' is from 'data-value' attribute of the <a> tag in html
        // pageCount.model.set("count", nRowPerPage) also works, because 'count' is the 'real'
        // parameter which is encoded in url and sent to the server to decide 'x per page'.
        this.children.pageCount = new SyntheticSelectControl({
            menuWidth: 'narrow',
            className: 'btn-group',
            items: [
                { value: 10, label: _('10 per page').t() },
                { value: 20, label: _('20 per page').t() },
                { value: 50, label: _('50 per page').t() },
                { value: 100, label: _('100 per page').t() },
            ],
            model: this.collection.peers.fetchData,
            modelAttribute: 'count',
            toggleClassName: 'btn-pill',
        });

        this.children.paginator = new Paginator({
            collection: this.collection.peers,
        });
    },
    render() {
        const $html = $(this.compiledTemplate({}));
        $html.find('.select-page-count').append(this.children.pageCount.render().el);
        $html.find('.paginator-container').append(this.children.paginator.render().el);
        this.$el.html($html);

        return this;
    },
    template: `
        <div class="table-controls">
            <div class="select-page-count pull-right"></div>
            <div class="clearfix"></div>
            <div class="paginator-container"></div>
        </div>
    `,
});