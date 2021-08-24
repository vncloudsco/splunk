import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import ManualDetentionDialog from './ManualDetentionDialog';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @param {Object} options {
     *     model: <Backbone.Model>,
     * }
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
    },

    getComponent() {
        return (
            <BackboneProvider store={{}}>
                <ManualDetentionDialog
                    open={this.options.open}
                    model={this.options.model}
                    memberName={this.options.memberName}
                    controller={this.options.controller}
                    collection={this.options.collection}
                    mgmt_uri={this.options.mgmt_uri}
                />
            </BackboneProvider>
        );
    },
});