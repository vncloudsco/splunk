/**
 * @author jsolis
 * @date 6/5/17
 */
import _ from 'underscore';
import React from 'react';
import BaseView from 'views/Base';
import Switch from '@splunk/react-ui/Switch';
import ReactAdapterBase from 'views/ReactAdapterBase';

export default ReactAdapterBase.extend({
    moduleId: module.id,

    initialize(options = {}) {
        this.options = options;

        const defaults = {
            appearance: 'toggle',
            value: this.options.modelAttribute,
            size: 'small',
            selected: false,
        };

        _.defaults(this.options, defaults);

        BaseView.prototype.initialize.call(this, options);

        this.listenTo(this.model, `change:${this.options.modelAttribute}`, this.debouncedRender);
    },

    // Helper Functions
    getModelValue() {
        if (!_.isUndefined(this.model.get(this.options.modelAttribute))) {
            return this.model.get(this.options.modelAttribute);
        }
        return this.options.selected;
    },

    setModelValue(value) {
        this.model.set(this.options.modelAttribute, value);
    },

    // Event Handlers
    handleClick() {
        if (this.getModelValue()) {
            // this call to set the value on the model will trigger the event handler
            // which will then call render again
            // React will notice that its state has not changed and will not update the DOM
            this.setModelValue(false);
        } else {
            this.setModelValue(true);
        }
    },

    // Rendering
    getComponent() {
        const props = {
            value: this.options.value,
            appearance: this.options.appearance,
            size: this.options.size,
            onClick: this.handleClick.bind(this),
            selected: this.getModelValue(),
        };
        return React.createElement(Switch, props);
    },

});