import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import Message from '@splunk/react-ui/Message';
// eslint-disable-next-line no-unused-vars
import css from './Message.pcss';

export default ReactAdapterBase.extend({
    className: 'shared-message',
    moduleId: module.id,
    /**
     * @constructor
     * @memberOf views
     * @name Tooltip
     * @extends {views.ReactAdapterBase}
     * @description Backbone wrapper for react Tooltip icon
     * See http://splunkui.sv.splunk.com/Packages/react-ui/Message for API documentation
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
    },

    getComponent() {
        return (
            <BackboneProvider store={{}}>
                <Message
                    type={this.options.type}
                    fill={this.options.fill}
                >
                    {this.options.children}
                </Message>
            </BackboneProvider>
        );
    },
});
