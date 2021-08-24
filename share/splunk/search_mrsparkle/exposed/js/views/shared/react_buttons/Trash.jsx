import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import Trash from '@splunk/react-icons/Trash';
import ButtonSimple from '@splunk/react-ui/ButtonSimple';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @constructor
     * @memberOf views
     * @name Trash
     * @extends {views.ReactAdapterBase}
     * @description Backbone wrapper for react Trash icon
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
                    <Trash size="1em" />
                </ButtonSimple>
            </BackboneProvider>
        );
    },
});
