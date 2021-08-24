import _ from 'underscore';
import React, { Component } from 'react';
import PropTypes from 'prop-types';
import Select from '@splunk/react-ui/Select';
import Button from '@splunk/react-ui/Button';
import Clear from '@splunk/react-icons/Clear';
import { keywordLocations, stringToKeywords, testPhrase } from '@splunk/ui-utils/filter';
import { createTestHook } from 'util/test_support';

// The reasons why this is not a stateless component are:
// - if allowCustomValues is true, user can create new value in the search box, but the new value is
//      saved only when that value is selected. So we need to save the new value in this component's
//      state temporarily.
// - although the selected value is communicated back to the parent by the onChange prop, parent is
//      not responsible for re-rendering this component (otherwise we are going back to the old Backbone
//      world where render is manually controlled). So we need to use component state to manage the
//      selected value and it will automatically re-render.
export default class Dropdown extends Component {
    constructor(props) {
        super(props);

        this.state = {
            value: props.value,
            filterKeyword: '',
        };

        this.handleChange = this.handleChange.bind(this);
        this.handleFilterChange = this.handleFilterChange.bind(this);
    }

    componentWillReceiveProps({ value }) {
        if (value !== this.state.value) {
            this.updateValue(value);
        }
    }

    updateValue(value, callback) {
        this.setState({
            value,
            // remember to reset filterKeyword
            filterKeyword: '',
        }, callback);
    }

    handleChange(e, { value }) {
        // Because setState is async, we need to make sure notifying the outside world only after updating the state.
        this.updateValue(value, () => this.props.onChange(value));
    }

    handleFilterChange(e, { keyword }) {
        this.setState({ filterKeyword: keyword });
    }

    createSelectOption() {
        const {
            choices,
            allowCustomValues,
        } = this.props;

        const {
            value,
            filterKeyword,
        } = this.state;

        // handle the case where value doesn't match any choice in the dropdown.
        // for example: choices = [1, 2, 3], value = 4.
        // this happens when user sets a default/initial value when instantiating the dropdown.
        const shouldAppendHiddenValue = value != null && choices.findIndex(choice => choice.value === value) < 0;

        let displayedChoices = shouldAppendHiddenValue ? choices.concat([{ label: value, value }]) : choices;

        const keywords = stringToKeywords(filterKeyword);

        // have to support custom values because the previous implementation does and it became public API.
        if (allowCustomValues && keywords.length > 0) {
            displayedChoices = choices.filter(choice => testPhrase(choice.label, keywords));

            if (displayedChoices.length === 0) {
                // add new option
                displayedChoices.push({
                    label: `${filterKeyword} (new value)`,
                    value: filterKeyword,
                    key: filterKeyword,
                });
            }
        }

        return displayedChoices.map(choice => (
            <Select.Option
                key={choice.value}
                label={_(choice.label || choice.value).t()}
                value={choice.value}
                matchRanges={keywordLocations(choice.label, keywords) || undefined}
            />
        ));
    }

    render() {
        const {
            choices,
            defaultValue,
            disabled,
            allowCustomValues,
            showClearButton,
            minimumResultsForSearch,
            width,
            onReset,
        } = this.props;

        const value = this.state.value;

        const shouldShowClearButton = showClearButton && value !== defaultValue;

        return (
            <div
                style={{ width, display: 'flex' }}
                {...createTestHook(module.id)}
            >
                <Select
                    disabled={disabled}
                    filter={allowCustomValues ? 'controlled' : minimumResultsForSearch < choices.length}
                    value={value}
                    onChange={this.handleChange}
                    onFilterChange={this.handleFilterChange}
                    append={shouldShowClearButton}
                    inline={false}
                    // SPL-158331: minWidth is a temporary solution for OrangeSwirl, will be fixed in SplunkUI
                    style={{ flex: '1 0 0%', minWidth: 0 }}
                >
                    {this.createSelectOption()}
                </Select>
                {shouldShowClearButton ? (
                    <Button
                        icon={<Clear />}
                        prepend
                        inline={false}
                        style={{ width: 'auto', flex: '0 0 auto' }}
                        onClick={onReset}
                        disabled={disabled}
                    />
                ) : null }
            </div>
        );
    }
}

Dropdown.propTypes = {
    choices: PropTypes.arrayOf(PropTypes.object),
    defaultValue: PropTypes.string,
    disabled: PropTypes.bool,
    minimumResultsForSearch: PropTypes.number,
    allowCustomValues: PropTypes.bool,
    showClearButton: PropTypes.bool,
    width: PropTypes.number,
    value: PropTypes.string,
    onChange: PropTypes.func.isRequired,
    onReset: PropTypes.func,
};

Dropdown.defaultProps = {
    choices: [],
    defaultValue: undefined,
    disabled: false,
    minimumResultsForSearch: 8,
    showClearButton: true,
    allowCustomValues: false,
    value: undefined,
    width: 200,
    onReset: () => {},
};

