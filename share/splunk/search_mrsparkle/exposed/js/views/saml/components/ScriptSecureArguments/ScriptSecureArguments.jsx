import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { _ } from '@splunk/ui-utils/i18n';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import FormRows from '@splunk/react-ui/FormRows';
import Text from '@splunk/react-ui/Text';
import Multiselect from '@splunk/react-ui/Multiselect';
import { sprintf } from '@splunk/ui-utils/format';

const spanStyle = {
    display: 'inline-block',
    lineHeight: '32px',
    flex: '0 0 30px',
    textAlign: 'center',
};

const keyStyle = {
    flex: '0 0 150px',
};

const valueStyle = {
    flex: '1 0 0',
};

class ScriptSecureArguments extends Component {
    constructor(props, context) {
        super(props, context);
        const items = [];
        Object.keys(props.scriptSecureArguments).forEach((key) => {
            items.push({
                key,
                value: props.scriptSecureArguments[key],
                isNew: false,
                hasChanged: false,
            });
        });
        this.state = {
            items,
            scriptFunctions: props.scriptFunctions,
        };
        this.props.onScriptSecureArgumentsChange(items);
    }

    handleRequestAdd = () => {
        const items = this.state.items.concat([{ key: '', value: '', isNew: true, hasChanged: true }]);
        this.setState({
            items,
        });
    };

    handleRequestRemove = (e, { index }) => {
        const items = this.state.items;
        if (this.state.items[index].isNew) {
            items.splice(index, 1);
        } else {
            items[index].value = '';
            items[index].hasChanged = true;
        }
        this.setState({ items });
        this.props.onScriptSecureArgumentsChange(items);
    };

    handleValueTextChange = (e, { value, name }) => {
        const index = name.replace('value-', '');
        const items = this.state.items;
        items[index].value = value;
        items[index].hasChanged = true;
        this.setState({
            items,
        });
        this.props.onScriptSecureArgumentsChange(items);
    };

    handleKeyTextChange = (e, { value, name }) => {
        const index = name.replace('key-', '');
        const items = this.state.items;
        items[index].key = value;
        items[index].hasChanged = true;
        this.setState({
            items,
        });
        this.props.onScriptSecureArgumentsChange(items);
    };

    handleScriptFunctionChange = (e, { values }) => {
        this.setState({ scriptFunctions: values });
        this.props.onScriptFunctionChange(values);
    };

    createRows = (items) => {
        let rows = [];
        items.forEach((item, index) => {
            rows = FormRows.addRow(
                <FormRows.Row
                    onRequestRemove={this.handleRequestRemove}
                    index={index}
                    style={{ width: '548px' }}
                >
                    <div style={{ display: 'flex' }}>
                        <Text
                            placeholder="key"
                            inline
                            value={item.key}
                            name={sprintf('key-%(index)s', { index })}
                            disabled={this.props.disabled || !items[index].isNew}
                            style={keyStyle}
                            data-test-name={sprintf('key-text-%(index)s', { index })}
                            describedBy="header-key"
                            onChange={this.handleKeyTextChange}
                        />
                        <span style={spanStyle}>=</span>
                        <Text
                            placeholder="value"
                            inline
                            value={item.value}
                            name={sprintf('value-%(index)s', { index })}
                            style={valueStyle}
                            data-test-name={sprintf('value-text-%(index)s', { index })}
                            describedBy="header-value"
                            disabled={this.props.disabled}
                            onChange={this.handleValueTextChange}
                        />
                    </div>
                </FormRows.Row>,
                rows,
            );
        });
        return rows;
    };

    render() {
        const header = (
            <div>
                <span
                    style={{
                        display: 'inline-block',
                        width: 180,
                    }}
                    id="header-key"
                >
                    Key
                </span>
                <span style={{ display: 'inline-block' }} id="header-value">
                    Value
                </span>
            </div>
        );
        const rows = this.createRows(this.state.items);
        return (
            <div>
                <ControlGroup
                    label={_('Script Functions')}
                    labelWidth={160}
                    disabled={this.props.disabled}
                    data-test-name={'script-functions-control-group'}
                    help={_('Script functions to be enabled for authentication extensions.')}
                >
                    <div style={{ width: '580px' }}>
                        <Multiselect
                            values={this.state.scriptFunctions}
                            onChange={this.handleScriptFunctionChange}
                            disabled={this.props.disabled}
                            scrollContainer={this.props.scrollContainer}
                        >
                            <Multiselect.Option label={_('login')} value="login" />
                            <Multiselect.Option label={_('getUserInfo')} value="getUserInfo" />
                        </Multiselect>
                    </div>
                </ControlGroup>
                <ControlGroup
                    label={_('Script Secure Arguments')}
                    labelWidth={160}
                    disabled={this.props.disabled}
                    data-test-name={'script-secure-args-control-group'}
                    help={_('A list of inputs, expressed as key-value pairs, that will be made available' +
                            'in plaintext to the custom user information retrieval script.')}
                >
                    <FormRows
                        addLabel={_('Add Input')}
                        header={header}
                        onRequestAdd={this.handleRequestAdd}
                        disabled={this.props.disabled}
                    >
                        {rows}
                    </FormRows>
                </ControlGroup>
            </div>
        );
    }

}

ScriptSecureArguments.propTypes = {
    scriptSecureArguments: PropTypes.objectOf(PropTypes.string).isRequired,
    scriptFunctions: PropTypes.arrayOf(PropTypes.string).isRequired,
    onScriptSecureArgumentsChange: PropTypes.func.isRequired,
    onScriptFunctionChange: PropTypes.func.isRequired,
    disabled: PropTypes.bool.isRequired,
    scrollContainer: PropTypes.element.isRequired,
};

export default ScriptSecureArguments;
