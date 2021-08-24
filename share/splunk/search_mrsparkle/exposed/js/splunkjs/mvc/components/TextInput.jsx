import React, { Component } from 'react';
import PropTypes from 'prop-types';
import Text from '@splunk/react-ui/Text';
import { createTestHook } from 'util/test_support';

export default class TextInput extends Component {
    constructor(props) {
        super(props);

        this.state = {
            value: props.value,
        };

        this.submitChange = this.submitChange.bind(this);
    }

    componentWillReceiveProps({ value }) {
        if (value !== this.state.value) {
            this.updateValue(value);
        }
    }

    updateValue(value) {
        this.setState({ value });
    }

    submitChange() {
        // This is to emulate the behavior of previous implementation of TextInput.
        // It only submit change when on blur or press enter key.
        this.props.onChange(this.state.value);
    }

    render() {
        const {
            type,
            disabled,
        } = this.props;

        return (
            <Text
                value={this.state.value}
                disabled={disabled}
                type={type}
                onChange={(e, { value: v }) => {
                    this.updateValue(v);
                }}
                onBlur={this.submitChange}
                onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                        this.submitChange();
                    }
                }}
                {...createTestHook(module.id)}
            />
        );
    }
}

TextInput.propTypes = {
    onChange: PropTypes.func.isRequired,
    value: PropTypes.string,
    type: PropTypes.string,
    disabled: PropTypes.bool,
};

TextInput.defaultProps = {
    value: '',
    type: 'text',
    disabled: false,
};

