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
            className: (LazyViz.prototype.className || '') + ' lazy-single-value',
            loadingMessage: _('Loading Results...').t(),
            loadModule: function() {
                var dfd = $.Deferred();

                // Rename so r.js doesn't detect the dependency at build time
                var lazyRequire = require;
                lazyRequire(['views/shared/singlevalue/Master'], function() {
                    dfd.resolve.apply(dfd, arguments);
                });

                return dfd;
            }

        },
        {
            getInitialDataParams: function() {
                throw new Error('LazySingleValue.getInitialDataParams should not be called!');
            }
        });

    });
