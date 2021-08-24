/**
 * A lazy view wrapper designed exclusively for use with subclasses of views/shared/viz/Base.js
 *
 * Handles the proxying of state manipulation methods like setScaleDictionary and setDisplayMode.
 */

define([
            'views/shared/LazyView'
        ],
        function(
            LazyView
        ) {

    return LazyView.extend({

        initialize: function () {
            LazyView.prototype.initialize.apply(this, arguments);
            this._scaleDictionary = {};
            this._displayMode = null;
        },

        setScaleDictionary: function(scaleDictionary) {
            this._scaleDictionary = scaleDictionary;
            if (this.children.wrappedView) {
                this.children.wrappedView.setScaleDictionary(scaleDictionary);
            }
        },

        setDisplayMode: function(displayMode) {
            this._displayMode = displayMode;
            if (this.children.wrappedView) {
                this.children.wrappedView.setDisplayMode(displayMode);
            }
        },

        _onWrappedViewLoaded: function() {
            LazyView.prototype._onWrappedViewLoaded.apply(this, arguments);
            this.children.wrappedView.setScaleDictionary(this._scaleDictionary);
            if (this._displayMode !== null) {
                this.children.wrappedView.setDisplayMode(this._displayMode);
            }
        }
    });

});