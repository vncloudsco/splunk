import _ from 'underscore';
import React from 'react';
import PropTypes from 'prop-types';
import RadioBar from '@splunk/react-ui/RadioBar';
import { createTestHook } from 'util/test_support';

const LinkList = ({
    value,
    choices,
    disabled,
    onChange,
}) => {
    // This is to be consistent with the old backbone-based implementation.
    // It shows one link with empty label to indicate there's a LinkList exists.
    const c = choices.length > 0 ? choices : [{ label: 'N/A', value: '' }];

    return (
        <RadioBar
            {...createTestHook(module.id)}
            appearance="pill"
            inline
            value={value}
            onChange={(e, data) => {
                onChange(data.value);
            }}
            style={{
                flexWrap: 'wrap',
                width: '100%',
            }}
        >
            {c.map(choice => (
                <RadioBar.Option
                    key={choice.value}
                    value={choice.value}
                    label={_(choice.label || choice.value).t()}
                    disabled={disabled}
                    style={{
                        flexGrow: 0,    // this is to be consistent with the old Splunk Enterprise style
                    }}
                />
            ))}
        </RadioBar>
    );
};

LinkList.propTypes = {
    value: PropTypes.string,
    choices: PropTypes.arrayOf(PropTypes.shape({ label: PropTypes.string, value: PropTypes.string })),
    onChange: PropTypes.func.isRequired,
    disabled: PropTypes.bool,
};

LinkList.defaultProps = {
    value: undefined,
    choices: [],
    disabled: false,
};

export default LinkList;
