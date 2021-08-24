import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import CloseButton from '@splunk/react-ui/CloseButton';
// eslint-disable-next-line no-unused-vars
import css from 'views/indexes/shared/rollup/CloseButton.pcss';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    className: 'rollup-close-button',
    /**
     * @constructor
     * @memberOf views
     * @name CloseButton
     * @extends {views.ReactAdapterBase}
     * @description Backbone wrapper for the React CloseButton component
     *
     * @param {Object} options
     * @param {Object} options.style CSS styling for the close button
     * @param {Function} options.onClick Callback function on click of the button
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.store = {};
    },

    getComponent() {
        const style = this.options.style;
        return (
            <BackboneProvider store={this.store} model={{}}>
                <CloseButton
                    onClick={this.options.onClick}
                    style={style}
                />
            </BackboneProvider>
        );
    },
});
