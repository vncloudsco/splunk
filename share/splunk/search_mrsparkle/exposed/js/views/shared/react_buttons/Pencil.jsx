import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import Pencil from '@splunk/react-icons/Pencil';
import ButtonSimple from '@splunk/react-ui/ButtonSimple';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @constructor
     * @memberOf views
     * @name Pencil
     * @extends {views.ReactAdapterBase}
     * @description Backbone wrapper for react Pencil icon
     *
     * @param {Object} options
     * @param {Object} options.className The class name of the button
     * @param {Object} options.onClick The callback function when the component is clicked
     * @param {Object} options.style The style of the button
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
    },

    getComponent() {
        return (
            <BackboneProvider store={{}}>
                <ButtonSimple
                    className={this.options.className}
                    onClick={() => this.options.onClick()}
                    style={this.options.style}
                >
                    <Pencil size="1em" />
                </ButtonSimple>
            </BackboneProvider>
        );
    },
});
