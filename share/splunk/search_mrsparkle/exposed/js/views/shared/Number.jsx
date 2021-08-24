import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import Number from '@splunk/react-ui/Number';
// eslint-disable-next-line no-unused-vars
import css from './Number.pcss';

export default ReactAdapterBase.extend({
    className: 'shared-number',
    moduleId: module.id,
    /**
     * @constructor
     * @memberOf views
     * @name Number
     * @extends {views.ReactAdapterBase}
     * @description Backbone wrapper for react Tooltip icon.
     * See http://splunkui.sv.splunk.com/Packages/react-ui/Number for API documentation
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
    },

    getComponent() {
        return (
            <BackboneProvider store={{}}>
                <Number
                    append={this.options.append}
                    defaultValue={this.options.defaultValue}
                    describedBy={this.options.describedBy}
                    disabled={this.options.disabled}
                    elementRef={this.options.elementRef}
                    error={this.options.error}
                    inputId={this.options.inputId}
                    inline={this.options.inline}
                    hideStepButtons={this.options.hideStepButtons}
                    roundTo={this.options.roundTo}
                    labelledBy={this.options.labelledBy}
                    min={this.options.min}
                    max={this.options.max}
                    name={this.options.name}
                    onBlur={this.options.onBlur}
                    onChange={this.options.onChange}
                    onFocus={this.options.onFocus}
                    onKeyDown={this.options.onKeyDown}
                    onKeyUp={this.options.onKeyUp}
                    onSelect={this.options.onSelect}
                    placeholder={this.options.placeholder}
                    prepend={this.options.prepend}
                    size={this.options.size}
                    step={this.options.step}
                    useSyntheticPlaceholder={this.options.useSyntheticPlaceholder}
                />
            </BackboneProvider>
        );
    },
});
