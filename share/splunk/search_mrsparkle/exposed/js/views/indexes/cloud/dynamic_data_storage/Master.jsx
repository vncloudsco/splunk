import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import DynamicDataStorageContainer from './DynamicDataStorageContainer';

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
            <BackboneProvider store={{}} model={this.options.model}>
                <DynamicDataStorageContainer
                    constants={this.options.constants}
                    archiveLicense={this.options.archiveLicense}
                    maxArchiveRetention={this.options.maxRetention}
                />
            </BackboneProvider>
        );
    },
});