import PropTypes from 'prop-types';
import React from 'react';
import _ from 'underscore';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Switch from '@splunk/react-ui/Switch';
import { createTestHook } from 'util/test_support';

const isSelected = (value) => {
    if (_.isString(value)) {
        return value !== '_self';
    } else if (_.isBoolean(value)) {
        return value;
    }

    return false;
};

const toggleValue = (value) => {
    if (value === '_self') {
        return '_blank';
    } else if (value === '_blank') {
        return '_self';
    } else if (value === true) {
        return false;
    }

    return true;
};

const OpenInNewTab = ({ value, onClick }) =>
    <ControlGroup label="" {...createTestHook(module.id)}>
        <Switch
            value={value}
            selected={isSelected(value)}
            onClick={e => onClick(e, { value: toggleValue(value) })}
        >
            {_('Open in new tab').t()}
        </Switch>
    </ControlGroup>;

OpenInNewTab.propTypes = {
    value: PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.bool,
    ]).isRequired,
    onClick: PropTypes.func.isRequired,
};

export default OpenInNewTab;
