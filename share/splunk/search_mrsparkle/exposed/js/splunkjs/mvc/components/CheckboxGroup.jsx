import _ from 'underscore';
import React from 'react';
import PropTypes from 'prop-types';
import Switch from '@splunk/react-ui/Switch';
import { createTestHook } from 'util/test_support';

const CheckboxGroup = ({
    choices,
    disabled,
    value,
    onChange,
}) => {
    const handleClick = (v) => {
        const index = value.indexOf(v);

        let newValue;

        if (index > -1) {
            // un-select the checkbox
            newValue = [...value.slice(0, index), ...value.slice(index + 1)];
        } else {
            // select the checkbox
            // Note: we need to make sure the selected values are in the same order as the choices are.
            newValue = choices
                .map(choice => choice.value)
                .filter(choice => value.indexOf(choice) > -1 || choice === v);
        }

        onChange(newValue);
    };

    // This is to be consistent with the old backbone-based implementation.
    // It shows one checkbox with empty label to indicate there's a CheckboxGroup exists.
    const c = choices.length > 0 ? choices : [{ label: ' ', value: '' }];

    return (
        <div
            {...createTestHook(module.id)}
        >
            {c.map(choice => (
                <Switch
                    key={choice.value}
                    value={choice.value}
                    selected={value.indexOf(choice.value) > -1}
                    disabled={disabled}
                    onClick={() => handleClick(choice.value)}
                >
                    {_(choice.label || choice.value).t()}
                </Switch>
            ))}
        </div>
    );
};

CheckboxGroup.propTypes = {
    value: PropTypes.arrayOf(PropTypes.string),
    choices: PropTypes.arrayOf(PropTypes.object),
    disabled: PropTypes.bool,
    onChange: PropTypes.func.isRequired,
};

CheckboxGroup.defaultProps = {
    value: [],
    choices: [],
    disabled: false,
};

export default CheckboxGroup;
