import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import _ from 'underscore';
import RestoreDialogContainer from './RestoreDialogContainer';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @param {Object} options {
     *     model: {
     *         entity: <models.indexes.cloud.Index>
     *     }
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.handleClose = this.handleClose.bind(this);
    },

    handleClose() {
        _.delay(() => this.remove(), 300);
    },

    getComponent() {
        let name = '';
        if (_.has(this.model, 'entity') && _.has(this.model.entity, 'entry')) {
            name = this.model.entity.entry.get('name');
        }
        return (
            <RestoreDialogContainer
                name={name}
                onClose={this.handleClose}
            />
        );
    },
});