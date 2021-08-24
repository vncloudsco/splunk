import React, { Component } from 'react';
import { _ } from '@splunk/ui-utils/i18n';
import Button from '@splunk/react-ui/Button';
import PropTypes from 'prop-types';
import Dropdown from '@splunk/react-ui/Dropdown';
import Menu from '@splunk/react-ui/Menu';
import { createTestHook } from 'util/test_support';

class ActionMenu extends Component {

    constructor(props) {
        super(props);

        ['onCaptainSelect', 'onManualDetention'].forEach(
            (name) => {
                this[name] = this[name].bind(this);
            },
        );
    }

    onCaptainSelect() {
        this.props.model.controller.trigger('openCaptainConfirmationDialog', { targetMember: this.props.model.entity });
    }

    onManualDetention() {
        this.props.model.controller.trigger('openManualDetentionDialog', { targetMember: this.props.model.entity });
    }

    render() {
        let transferCaptain;
        if (this.props.model.entity.entry.content.get('is_captain') === false) {
            transferCaptain = (
                <Menu.Item {...createTestHook(null, 'transferCaptainButton')} onClick={this.onCaptainSelect}>
                    { _('Transfer Captain') }
                </Menu.Item>
            );
        }
        return (
            <Dropdown toggle={<Button label="actions" appearance="pill" isMenu />}>
                <Menu style={{ width: 140 }}>
                    <Menu.Item {...createTestHook(null, 'manualDetentionButton')} onClick={this.onManualDetention}>
                        { _('Manual Detention') }
                    </Menu.Item>
                    { transferCaptain }
                </Menu>
            </Dropdown>
        );
    }
}

ActionMenu.propTypes = {
    model: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
};

export default ActionMenu;
