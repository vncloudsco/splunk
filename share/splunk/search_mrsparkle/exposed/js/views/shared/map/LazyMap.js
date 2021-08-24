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
        className: (LazyViz.prototype.className || '') + ' lazy-map',
        loadingMessage: _('Loading Map...').t(),
        loadModule: function() {
            var dfd = $.Deferred();

            // Rename so r.js doesn't detect the dependency at build time
            var lazyRequire = require;
            lazyRequire(['views/shared/map/Master'], function() {
                dfd.resolve.apply(dfd, arguments);
            });

            return dfd;
        },

        initialize: function() {
            LazyViz.prototype.initialize.apply(this, arguments);
            this.$el.height(this.options.height || 400);
            this._scaleDictionary = null;
        },

        setScaleDictionary: function(scaleDictionary) {
            this._scaleDictionary = scaleDictionary;
            if (this.children.wrappedView) {
                this.children.wrappedView.setScaleDictionary(scaleDictionary);
            }
        },

        _onWrappedViewLoaded: function() {
            LazyViz.prototype._onWrappedViewLoaded.apply(this, arguments);
            if (this._scaleDictionary) {
                this.children.wrappedView.setScaleDictionary(this._scaleDictionary);
            }
        },

        _getWrappedViewOptions: function() {
            return _.extend(
                {},
                LazyViz.prototype._getWrappedViewOptions.apply(this, arguments),
                { height: '100%' }
            );
        }

    }, {
        getDataContract: function() {
            return {
                scales: {
                    color: {
                        type: 'linear'
                    }
                }
            };
        }
    });

});
