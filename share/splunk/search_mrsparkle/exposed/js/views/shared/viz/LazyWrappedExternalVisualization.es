import _ from 'underscore';
import $ from 'jquery';
import console from 'util/console';
import requirejs from 'requirejs';
import LazyViz from 'views/shared/viz/LazyViz';
import WrappedExternalVisualization from 'views/shared/viz/WrappedExternalVisualization';

const ExternalVisualizationWrapper = LazyViz.extend({
    className: `${LazyViz.prototype.className || ''} lazy-custom-visualization`,
    vizName: null,
    appName: null,

    loadModule() {
        const deferred = $.Deferred(); // eslint-disable-line new-cap
        const deps = [
            this.jsPath,
            this.cssPath,
        ];
        requirejs(deps, (...args) => {
            // The LazyViz expects the first argument to be the view constructor itself,
            // followed by any additional dependencies.
            deferred.resolve(WrappedExternalVisualization, ...args);
        }, (err) => {
            console.error('Error dynamically loading module: ', err);
            deferred.reject(err);
        });
        return deferred;
    },

    _getWrappedViewOptions(vizConstructor, ...args) {
        // eslint-disable-next-line no-underscore-dangle
        return _.extend({}, LazyViz.prototype._getWrappedViewOptions.call(this, vizConstructor, ...args), {
            vizName: this.vizName,
            appName: this.appName,
            vizConstructor,
        });
    },
});

export default ExternalVisualizationWrapper;
