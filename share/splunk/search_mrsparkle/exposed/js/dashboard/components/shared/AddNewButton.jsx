import _ from 'underscore';
import PropTypes from 'prop-types';
import React from 'react';
import Button from '@splunk/react-ui/Button';
import Plus from '@splunk/react-icons/Plus';
import { createTestHook } from 'util/test_support';

const AddNewButton = ({
    onClick,
    error,
}) =>
    <Button
        icon={<Plus />}
        appearance="pill"
        label={_('Add New').t()}
        onClick={onClick}
        error={error}
        {...createTestHook(module.id)}
    />;

AddNewButton.propTypes = {
    onClick: PropTypes.func.isRequired,
    error: PropTypes.bool,
};

AddNewButton.defaultProps = {
    error: false,
};

export default AddNewButton;
