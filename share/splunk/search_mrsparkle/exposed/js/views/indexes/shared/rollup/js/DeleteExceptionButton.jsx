import React from 'react';
import $ from 'jquery';
import { _ as i18n } from '@splunk/ui-utils/i18n';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import ButtonSimple from '@splunk/react-ui/ButtonSimple';
import Trash from '@splunk/react-icons/Trash';
// eslint-disable-next-line no-unused-vars
import css from 'views/indexes/shared/rollup/DeleteExceptionButton.pcss';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    className: 'rollup-delete-exception-button',
    /**
     * @constructor
     * @memberOf views
     * @name DeleteExceptionButton
     * @extends {views.ReactAdapterBase}
     * @description Button for deleting an exception rule
     *
     * @param {Object} options
     * @param {Object} options.model The model supplied to this class
     * @param {Object} options.style Style applied to the button component
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.store = {};
        this.deleteExceptionPolicy = this.deleteExceptionPolicy.bind(this);
    },

    deleteExceptionPolicy() {
        const index = this.model.content.get('tabIndex');
        const tabs = $.extend(true, [], this.model.rollup.get('tabs'));
        tabs.splice(index, 1);
        // have to update tab index first
        this.model.content.set({ tabIndex: index - 1 });
        this.model.rollup.set({ tabs });
    },

    getComponent() {
        const style = this.options.style;
        return (
            <BackboneProvider store={this.store} model={this.model}>
                <ButtonSimple
                    className="inner-rollup-delete-exception-button"
                    appearance="pill"
                    onClick={this.deleteExceptionPolicy}
                    style={style}
                >
                    <Trash inline={false} size="13px" screenReaderText={i18n('Delete')} />
                </ButtonSimple>
            </BackboneProvider>
        );
    },
});
