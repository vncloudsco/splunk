import React from 'react';
import RadioBar from '@splunk/react-ui/RadioBar';
import ReactAdapterBase from 'views/ReactAdapterBase';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    initialize(...args) {
        ReactAdapterBase.prototype.initialize.apply(this, ...args);
        this.handleChange = this.handleChange.bind(this);
    },
    renderMenuItems() {
        return this.options.items.map(
            item => <RadioBar.Option label={item.label} value={item.value} key={item.value} />);
    },
    handleChange(e, { value }) {
        this.model.set(this.options.modelAttribute, value);
    },
    getValue() {
        let selectedValue = this.model.get(this.options.modelAttribute);
        if (!selectedValue && this.options.items && this.options.items.length > 0) {
            selectedValue = this.options.items[0].value;
            this.model.set(this.options.modelAttribute, selectedValue);
        }
        return selectedValue;
    },
    focusTheme(el) {
        if (el) {
            el.children[0].focus();
        }
    },
    getComponent() {
        return (
            <RadioBar elementRef={this.focusTheme} defaultValue={this.getValue()} onChange={this.handleChange}>
                {this.renderMenuItems()}
            </RadioBar>
        );
    },
});
