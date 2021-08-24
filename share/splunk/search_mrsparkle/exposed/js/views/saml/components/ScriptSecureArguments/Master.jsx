import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import ScriptSecureArgumentsContainer from './ScriptSecureArgumentsContainer';

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
            <BackboneProvider store={{}} >
                <ScriptSecureArgumentsContainer
                    model={this.options.model}
                    scrollContainer={this.options.scrollContainer}
                />
            </BackboneProvider>
        );
    },
});
