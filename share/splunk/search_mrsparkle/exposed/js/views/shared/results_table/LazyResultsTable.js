define([
            'underscore',
            'jquery',
            'module',
            'views/shared/viz/LazyViz'
        ],
        function(
            _,
            $,
            module,
            LazyViz
        ) {

    return LazyViz.extend({

        moduleId: module.id,
        className: (LazyViz.prototype.className || '') + ' lazy-results-table',
        loadingMessage: _('Loading Results...').t(),
        expandedRowIndex: null,
        loadModule: function() {
            var dfd = $.Deferred();

            // Rename so r.js doesn't detect the dependency at build time
            var lazyRequire = require;
            lazyRequire(['views/shared/results_table/ResultsTableMaster'], function() {
                dfd.resolve.apply(dfd, arguments);
            });

            return dfd;
        },

        _onWrappedViewLoaded: function() {
            if (this.expandedRowIndex !== null) {
                this.children.wrappedView.expandRow(this.expandedRowIndex);
            }
            LazyViz.prototype._onWrappedViewLoaded.apply(this, arguments);
        },

        expandRow: function(index) {
            this.expandedRowIndex = index;
            if (this.children.wrappedView) {
                this.children.wrappedView.expandRow(index);
            }
        },

        collapseRow: function() {
            this.expandedRowIndex = null;
            if (this.children.wrappedView) {
                this.children.wrappedView.collapseRow();
            }
        }

    },
    {
        getInitialDataParams: function(configJson) {
            throw new Error('LazyResultsTable.getInitialDataParams should not be called!');
        }
    });

});
