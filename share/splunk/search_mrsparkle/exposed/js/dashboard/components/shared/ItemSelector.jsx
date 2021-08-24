import _ from 'underscore';
import PropTypes from 'prop-types';
import React from 'react';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Select from '@splunk/react-ui/Select';
import splunkUtil from 'splunk.util';
import FormMessage from 'dashboard/components/shared/FormMessage';
import { createTestHook } from 'util/test_support';

const sprintf = splunkUtil.sprintf;

const ItemSelector = ({
    label,
    items,
    activeItem,
    isLoading,
    filter,
    onChange,
    error,
    warning,
    hideNoMatchError,
    ...otherProps
}) => {
    // activeItem should either match one of items or be empty string.
    const noMatchedItem = activeItem && (items.length > 0) && !items.find(item => item.value === activeItem);
    const noMatchedItemMessage = sprintf(
        _('Selected %s %s, it does not match any %s in the list.').t(),
        label.toLowerCase(),
        activeItem,
        label.toLowerCase(),
    );
    const hasError = !!(error || (!hideNoMatchError && noMatchedItem));
    let errorMessage;
    if (error) {
        errorMessage = `${label} ${error}`;
    } else if (noMatchedItem) {
        errorMessage = noMatchedItemMessage;
    } else {
        errorMessage = '';
    }

    const hasWarning = !!warning;
    const warningMessage = warning ? `${label} ${warning}` : '';

    return (
        <div {...createTestHook(module.id)} {...otherProps}>
            <FormMessage active={hasError} type="error" message={errorMessage} />
            <FormMessage active={hasWarning} type="warning" message={warningMessage} />
            <ControlGroup label={label} error={hasError}>
                <Select
                    error={hasError}
                    value={activeItem}
                    onChange={onChange}
                    inline
                    animateLoading
                    isLoadingOptions={isLoading}
                    placeholder={isLoading ? _('Loading...').t() : _('Select...').t()}
                    filter={filter}
                >
                    {items.map(item =>
                        <Select.Option
                            key={item.value}
                            label={item.label}
                            value={item.value}
                            description={item.description}
                        />,
                    )}
                </Select>
            </ControlGroup>
        </div>
    );
};

ItemSelector.propTypes = {
    label: PropTypes.string.isRequired,
    items: PropTypes.arrayOf(PropTypes.shape({
        label: PropTypes.string.isRequired,
        value: PropTypes.string.isRequired,
    }).isRequired).isRequired,
    activeItem: PropTypes.string.isRequired,
    isLoading: PropTypes.bool,
    filter: PropTypes.bool,
    onChange: PropTypes.func.isRequired,
    error: PropTypes.string,
    warning: PropTypes.string,
    hideNoMatchError: PropTypes.bool,
};

ItemSelector.defaultProps = {
    isLoading: false,
    filter: false,
    error: '',
    warning: '',
    hideNoMatchError: false,
};

export default ItemSelector;
