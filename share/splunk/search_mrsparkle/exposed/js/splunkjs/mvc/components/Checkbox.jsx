import React from 'react';
import PropTypes from 'prop-types';
import Switch from '@splunk/react-ui/Switch';
import { createTestHook } from 'util/test_support';

const Checkbox = ({
    value,
    disabled,
    onChange,
}) => (
    <Switch
        {...createTestHook(module.id)}
        value={value}
        selected={value}
        disabled={disabled}
        onClick={() => {
            onChange(!value);
        }}
    />
);

Checkbox.propTypes = {
    value: PropTypes.bool,
    disabled: PropTypes.bool,
    onChange: PropTypes.func.isRequired,
};

Checkbox.defaultProps = {
    value: false,
    disabled: false,
};

export default Checkbox;
