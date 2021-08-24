import _ from 'underscore';
import PropTypes from 'prop-types';
import React from 'react';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Text from '@splunk/react-ui/Text';
import ComboBox from '@splunk/react-ui/ComboBox';
import AddNewButton from 'dashboard/components/shared/AddNewButton';
import DeleteButton from 'dashboard/components/shared/DeleteButton';
import { createTestHook } from 'util/test_support';

const boxStyles = {
    marginBottom: '10px',
    display: 'flex',
};

const controlTextStyles = {
    flexShrink: '1',
    flexGrow: '0',
    maxWidth: '140px',
};

const delimiterStyles = {
    lineHeight: '26px',
    paddingLeft: '5px',
    paddingRight: '5px',
};

const KeyInput = ({
    item,
    placeholder,
    onChange,
    onClickDelete,
}) =>
    <div style={boxStyles}>
        <Text
            value={item}
            onChange={(e, data) => onChange(data.value)}
            style={controlTextStyles}
            placeholder={placeholder}
        />
        <DeleteButton onClick={onClickDelete} />
    </div>;

KeyInput.propTypes = {
    item: PropTypes.string.isRequired,
    placeholder: PropTypes.string,
    onChange: PropTypes.func.isRequired,
    onClickDelete: PropTypes.func.isRequired,
};

KeyInput.defaultProps = {
    placeholder: _('name').t(),
};

const KeyValueInput = ({
    item,
    candidateTokens,
    keyPlaceholder,
    valuePlaceholder,
    onChange,
    delimiter,
    onClickDelete,
}) => {
    const noOptionsMessage = <div>{_('Enter value').t()}</div>;
    return (
        <div style={boxStyles} data-test="parameter">
            <Text
                value={item.key}
                onChange={(e, data) => onChange({
                    key: data.value,
                    value: item.value,
                })}
                placeholder={keyPlaceholder}
                style={controlTextStyles}
                {...createTestHook(null, 'parameterKey')}
            />
            <div style={delimiterStyles}>{delimiter}</div>
            <ComboBox
                value={item.value}
                onChange={(e, data) => onChange({
                    key: item.key,
                    value: data.value,
                })}
                placeholder={valuePlaceholder}
                noOptionsMessage={noOptionsMessage}
                style={controlTextStyles}
                {...createTestHook(null, 'parameterValue')}
            >
                {_.map(candidateTokens, ({ token, description }) => (
                    <ComboBox.Option
                        key={token}
                        value={token}
                        description={description}
                    />
                ))}
            </ComboBox>
            <DeleteButton onClick={onClickDelete} />
        </div>
    );
};

KeyValueInput.propTypes = {
    item: PropTypes.shape({
        key: PropTypes.string.isRequired,
        value: PropTypes.string,
    }).isRequired,
    candidateTokens: PropTypes.arrayOf(PropTypes.shape({
        token: PropTypes.string.isRequired,
        description: PropTypes.string,
    })).isRequired,
    keyPlaceholder: PropTypes.string,
    valuePlaceholder: PropTypes.string,
    delimiter: PropTypes.string,
    onChange: PropTypes.func.isRequired,
    onClickDelete: PropTypes.func.isRequired,
};

KeyValueInput.defaultProps = {
    delimiter: _('=').t(),
    keyPlaceholder: _('name').t(),
    valuePlaceholder: _('value').t(),
};

const Parameters = ({
    label,
    items,
    candidateTokens,
    keyPlaceholder,
    valuePlaceholder,
    delimiter,
    onChange,
    onlyKey,
    error,
    help,
    tooltip,
}) =>
    <ControlGroup
        error={!!error}
        help={help}
        label={label}
        controlsLayout="none"
        tooltip={tooltip}
        {...createTestHook(module.id, 'parameters')}
    >
        {items.map((item, index) => {
            const updateItem = newItem => onChange([
                ...items.slice(0, index),
                newItem,
                ...items.slice(index + 1),
            ]);
            const deleteItem = () => onChange([
                ...items.slice(0, index),
                ...items.slice(index + 1),
            ]);

            if (onlyKey) {
                return (
                    <KeyInput
                        key={index} // eslint-disable-line react/no-array-index-key
                        item={item}
                        placeholder={keyPlaceholder}
                        onChange={updateItem}
                        onClickDelete={deleteItem}
                    />
                );
            }

            return (
                <KeyValueInput
                    key={index} // eslint-disable-line react/no-array-index-key
                    item={item}
                    candidateTokens={candidateTokens}
                    keyPlaceholder={keyPlaceholder}
                    valuePlaceholder={valuePlaceholder}
                    onChange={updateItem}
                    delimiter={delimiter}
                    onClickDelete={deleteItem}
                />
            );
        })}
        <AddNewButton onClick={() => onChange([...items, onlyKey ? '' : { key: '', value: '' }])} />
    </ControlGroup>;

Parameters.propTypes = {
    label: PropTypes.string.isRequired,
    items: PropTypes.oneOfType([
        PropTypes.arrayOf(PropTypes.shape({
            key: PropTypes.string.isRequired,
            value: PropTypes.string,
        })),
        PropTypes.arrayOf(PropTypes.string),
    ]).isRequired,
    candidateTokens: PropTypes.arrayOf(PropTypes.shape({
        token: PropTypes.string.isRequired,
        description: PropTypes.string,
    })).isRequired,
    keyPlaceholder: PropTypes.string,
    valuePlaceholder: PropTypes.string,
    delimiter: PropTypes.string,
    onChange: PropTypes.func.isRequired,
    onlyKey: PropTypes.bool,
    error: PropTypes.string,
    help: PropTypes.oneOfType([PropTypes.object, PropTypes.string]),
    tooltip: PropTypes.string,
};

Parameters.defaultProps = {
    onlyKey: false,
    keyPlaceholder: '',
    valuePlaceholder: '',
    delimiter: '=',
    error: '',
    help: '',
    tooltip: '',
};

export default Parameters;
