import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { _ } from '@splunk/ui-utils/i18n';
import { extend } from 'lodash';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Switch from '@splunk/react-ui/Switch';

class ManualDetentionSwitch extends Component {
    constructor(props, context) {
        super(props, context);
        this.state = {
            manual_detention: props.model.entry.content.get('manual_detention') === 'on',
        };
    }

    handleClick = (e, { value }) => {
        const newState = extend({}, this.state, {
            [value]: !this.state[value],
        });
        this.setState(newState, () => {
            this.props.model.entry.content.set({
                manual_detention: this.state.manual_detention === true ? 'on' : 'off',
            });
        });
        this.props.handleSwitchToggle(this.props.model.entry.content.get('manual_detention'));
    };

    render() {
        return (
            <ControlGroup
                label={_('Manual Detention')}
            >
                <Switch
                    value="manual_detention"
                    onClick={this.handleClick}
                    selected={this.state.manual_detention}
                    appearance="toggle"
                />
            </ControlGroup>
        );
    }
}

ManualDetentionSwitch.propTypes = {
    handleSwitchToggle: PropTypes.func.isRequired,
    model: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
};

export default ManualDetentionSwitch;

