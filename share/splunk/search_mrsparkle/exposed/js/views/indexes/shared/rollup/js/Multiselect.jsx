import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import Multiselect from '@splunk/react-ui/Multiselect';
import $ from 'jquery';

export default ReactAdapterBase.extend({
    /**
     * @constructor
     * @memberOf views
     * @name Multiselect
     * @extends {views.ReactAdapterBase}
     * @description Backbone wrapper for multiselect
     *
     * @param {Object} options
     * @param {Object} options.model The model supplied to this class
     * @param {String} options.ariaLabel The aria label applied to the multiselect
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.store = {};
        this.handleChange = this.handleChange.bind(this);
        this.handleTabsChange = this.handleTabsChange.bind(this);
        this.listenTo(this.model.content, 'change:tabIndex', this.render);
        this.listenTo(this.model.rollup, 'change:tabs', this.handleTabsChange);
        this.setAriaAttributes();
    },

    setAriaAttributes() {
        this.$el.attr({
            role: 'combobox',
            'aria-label': this.options.ariaLabel,
        });
    },

    handleTabsChange() {
        const tabs = this.model.rollup.get('tabs');
        if (tabs.length) {
            this.render();
        }
    },

    handleChange(e, { values }) {
        const tabs = $.extend(true, [], this.model.rollup.get('tabs'));
        const tabIndex = this.model.content.get('tabIndex');
        const listItems = tabs[tabIndex].listItems;
        tabs[0].selectedItems = [];
        for (let i = 0; i < listItems.length; i += 1) {
            const selected = values.indexOf(listItems[i].value) >= 0;
            listItems[i].default = selected;
            if (selected) {
                tabs[0].selectedItems.push(listItems[i].value);
            }
        }
        this.model.rollup.set('tabs', tabs);
        this.render();
    },

    renderMultiselect() {
        const tabs = this.model.rollup.get('tabs');
        const tabIndex = this.model.content.get('tabIndex');
        if (!tabs[tabIndex]) {
            return null;
        }
        const listItems = tabs[tabIndex].listItems || [];
        const excludedOptionElems = [];
        for (let i = 0; i < listItems.length; i += 1) {
            const value = listItems[i].value;
            const label = listItems[i].label;
            excludedOptionElems.push(
                <Multiselect.Option className="rollup-excluded-option" label={label} value={value} key={i} />,
            );
        }
        const selectedItems = tabs[tabIndex].selectedItems || [];
        const excludedDefaults = listItems
            .filter(item => item.default || (selectedItems.indexOf(item.value) >= 0))
            .map(item => item.value);
        return (
            <Multiselect
                placeholder={'Optional...'}
                values={excludedDefaults}
                onChange={this.handleChange}
            >
                {excludedOptionElems}
            </Multiselect>
        );
    },

    getComponent() {
        return (
            <BackboneProvider store={this.store} model={this.model}>
                {this.renderMultiselect()}
            </BackboneProvider>
        );
    },
});
