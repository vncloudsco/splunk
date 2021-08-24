import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import Tooltip from '@splunk/react-ui/Tooltip';
// eslint-disable-next-line no-unused-vars
import css from './Tooltip.pcss';

export default ReactAdapterBase.extend({
    className: 'shared-tooltip',
    moduleId: module.id,
    /**
     * @constructor
     * @memberOf views
     * @name Tooltip
     * @extends {views.ReactAdapterBase}
     * @description Backbone wrapper for react Tooltip icon
     *
     * @param {Object} options
     * @param {Object} options.content The content of the toolip message
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
    },

    getComponent() {
        return (
            <BackboneProvider store={{}}>
                <Tooltip
                    content={this.options.content}
                />
            </BackboneProvider>
        );
    },
});
