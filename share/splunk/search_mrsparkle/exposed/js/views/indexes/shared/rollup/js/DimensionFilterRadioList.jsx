import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import RadioList from '@splunk/react-ui/RadioList';
import $ from 'jquery';
import _ from 'underscore';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    className: 'dimension-filter-radio-list',
    /**
     * @constructor
     * @memberOf views
     * @name DimensionFilterRadioList
     * @extends {views.extend}
     * @description Radio list for selecting included/excluded
     *
     * @param {Object} options
     * @param {Object} options.model The model supplied to this class
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.store = {};
        this.handleChange = this.handleChange.bind(this);
        this.setAriaAttributes();
    },

    setAriaAttributes() {
        this.$el.attr({
            role: 'radiogroup',
            'aria-label': _('Dimension filter').t(),
        });
    },

    handleChange(e, { value }) {
        const tabs = $.extend(true, [], this.model.rollup.get('tabs'));
        tabs[0].listType = value;
        this.model.rollup.set({ tabs }, { silent: true });
        this.render();
    },

    renderRadioList() {
        const tabs = this.model.rollup.get('tabs');
        const listType = tabs ? tabs[0].listType : 'excluded';
        return (
            <RadioList
                value={listType}
                onChange={this.handleChange}
                appearance="horizontal"
            >
                <RadioList.Option value={'excluded'}>{_('Excluded Dimensions:').t()}</RadioList.Option>
                <RadioList.Option value={'included'}>{_('Included Dimensions:').t()}</RadioList.Option>
            </RadioList>
        );
    },

    getComponent() {
        return (
            <BackboneProvider store={this.store} model={this.model}>
                {this.renderRadioList()}
            </BackboneProvider>
        );
    },
});
