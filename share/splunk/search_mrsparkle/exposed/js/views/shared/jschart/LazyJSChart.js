define([
            'underscore',
            'jquery',
            'module',
            'models/config',
            'views/shared/viz/LazyViz'
        ],
        function(
            _,
            $,
            module,
            configModel,
            LazyViz
        ) {

    return LazyViz.extend({

        moduleId: module.id,
        className: (LazyViz.prototype.className || '') + ' lazy-jschart',
        loadingMessage: _('Loading Results...').t(),

        loadModule: function() {
            var dfd = $.Deferred();

            // Rename so r.js doesn't detect the dependency at build time
            var lazyRequire = require;
            lazyRequire(['views/shared/jschart/Master'], function() {
                dfd.resolve.apply(dfd, arguments);
            });

            return dfd;
        }

    },
    {

        getInitialDataParams: function() {
            throw new Error('JSChart.getInitialDataParams should not be called!');
        },

        getDataContract: function () {
            return {
                scales: {
                    yAxis: {
                        type: 'linear'
                    },
                    overlayAxis: {
                        type: 'linear'
                    },
                    xAxis: {
                        type: 'categorical'
                    }
                }
            };
        },

        getConfigForDisplayMode: function(displayMode) {
            if (displayMode === 'simple') {
                return {
                    'display.visualizations.charting.legend.placement': 'none',
                    'display.visualizations.charting.axisTitleX.visibility': 'collapsed',
                    'display.visualizations.charting.axisTitleY.visibility': 'collapsed',
                    'display.visualizations.charting.axisTitleY2.visibility': 'collapsed'
                };
            }
            return {
                'display.visualizations.charting.legend.placement': 'right',
                'display.visualizations.charting.axisTitleX.visibility': 'visible',
                'display.visualizations.charting.axisTitleY.visibility': 'visible',
                'display.visualizations.charting.axisTitleY2.visibility': 'visible'
            };
        }
    });

});
