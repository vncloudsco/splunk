import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import Select from '@splunk/react-ui/Select';
import css from 'views/indexes/shared/rollup/Select.pcssm';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @constructor
     * @memberOf views
     * @name Select
     * @extends {views.ReactAdapterBase}
     * @description Select control for selecting dimensions
     *
     * @param {Object} options
     * @param {Object} options.model The model supplied to this class
     * @param {Boolean} options.inline Should the component be displayed inline
     * @param {Array} options.items The items included in the control
     * @param {String} options.defaultValue The item to be selected by default
     * @param {String} options.placeholder Placeholder value for the control
     * @param {Function} options.onChange Callback function for when the control's value changes
     * @param {Number} options.menuWidth Width of the select menu
     * @param {Boolean} options.error Whether the component should be rendered with an error
     */
    initialize(options) {
        if (options.inline) {
            this.css = { view: css.inline };
        }
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.store = {};
        this.listenTo(this.model.rollup, 'change:tabs', this.render);
    },

    renderSelect() {
        const items = this.options.items;
        const options = [];
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i];
            options.push(
                <Select.Option
                    value={item.value}
                    label={item.label}
                    description={item.description}
                    key={i}
                />,
            );
        }
        return (
            <Select
                className={this.options.className}
                filter={this.options.filter}
                defaultValue={this.options.defaultValue}
                onChange={this.options.onChange}
                placeholder={this.options.placeholder}
                menuStyle={{ width: this.options.menuWidth || 300 }}
                style={this.options.style}
                error={this.options.error}
            >
                {options}
            </Select>
        );
    },

    getComponent() {
        return (
            <BackboneProvider store={this.store} model={this.model}>
                {this.renderSelect()}
            </BackboneProvider>
        );
    },
});
