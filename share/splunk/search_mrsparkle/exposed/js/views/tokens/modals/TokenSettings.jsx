import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { sprintf } from '@splunk/ui-utils/format';
import { _ } from '@splunk/ui-utils/i18n';
import Modal from '@splunk/react-ui/Modal';
import Button from '@splunk/react-ui/Button';
import Message from '@splunk/react-ui/Message';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Text from '@splunk/react-ui/Text';
import Switch from '@splunk/react-ui/Switch';

import { getToggleTokenAuthURL, isValidTokenTime } from 'views/tokens/Utils';

class TokenSettingsModal extends Component {
    static propTypes = {
        objectNameSingular: PropTypes.string.isRequired,
        handleRequestClose: PropTypes.func.isRequired,
        open: PropTypes.bool.isRequired,
        setTokenSettings: PropTypes.func.isRequired,
        callToggleTokenAuth: PropTypes.func.isRequired,
        tokenAuthEnabled: PropTypes.bool.isRequired,
        defaultExpiration: PropTypes.string.isRequired,
    }

    constructor(props, context) {
        super(props, context);
        this.state = {
            defaultExpiration: this.props.defaultExpiration,
            disabled: !this.props.tokenAuthEnabled,
        };
    }

    handleDefaultExpirationChange = (e, { value }) => {
        this.setState({
            defaultExpiration: value,
        });
    }

    handleDisableClick = () => {
        this.setState({
            disabled: !this.state.disabled,
            defaultExpiration: '',
            errorMessage: '',
        });
    };

    handleClose = () => {
        this.setState({
            isWorking: false,
            errorMessage: '',
        });
        this.props.handleRequestClose();
    };

    handleSave = () => {
        this.setState({
            isWorking: true,
        });
        if (this.state.defaultExpiration && !(isValidTokenTime(this.state.defaultExpiration) ||
                                              this.state.defaultExpiration === 'never')) {
            this.setState({
                isWorking: false,
                errorMessage: _('Error in highlighted fields.'),
            });
        } else {
            this.props.callToggleTokenAuth(getToggleTokenAuthURL(
                this.state.disabled,
                this.state.defaultExpiration ||
                this.props.defaultExpiration)).then(() => {
                    this.setState({
                        isWorking: false,
                        errorMessage: '',
                    });
                    this.props.setTokenSettings(this.state.disabled,
                                            this.state.defaultExpiration ||
                                            this.props.defaultExpiration);
                    this.handleClose();
                }).catch((response) => {
                    this.setState({
                        isWorking: false,
                        errorMessage: response.message,
                    });
                });
        }
    }

    render() {
        return (
            <Modal
                onRequestClose={this.handleClose}
                open={this.props.open}
                style={{ width: '500px' }}
                data-test-name={'token-settings-modal'}
            >
                <Modal.Header
                    title={sprintf(_('%s Settings'), this.props.objectNameSingular)}
                    onRequestClose={this.handleClose}
                />
                <Modal.Body>
                    {this.state.errorMessage && (
                        <Message type="error">{this.state.errorMessage}</Message>
                    )}
                    {this.state.disabled && (
                        <Message type="warning">
                            {_('If Token Authentication is off, all tokens will ' +
                               'be disabled, regardless of their individual status.')}
                        </Message>
                    )}
                    <ControlGroup
                        label={_('Token Authentication')}
                        data-test-name={'token-auth-group'}
                    >
                        <Switch
                            value={'disabled'}
                            onClick={this.handleDisableClick}
                            selected={!this.state.disabled}
                            appearance="toggle"
                            data-test-name={'token-auth-switch'}
                        >
                            {this.state.disabled ? _('Disabled') : _('Enabled')}
                        </Switch>
                    </ControlGroup>
                    <ControlGroup
                        label={_('Default Expiration')}
                        data-test-name={'expiration-group'}
                        error={!!(this.state.errorMessage && !this.state.disabled)}
                        help={_('The default expiration time for tokens you create where ' +
                                'you do not set an expiration individually. Can be either ' +
                                'a relative time (Example: +10m, +20h, +30d) or the word ' +
                                '"never" for no default expiration. Cannot be ' +
                                'greater than +18y.')}
                    >
                        <Text
                            data-test-name={'expiration-text'}
                            canClear
                            value={this.state.defaultExpiration}
                            error={!!(this.state.errorMessage && !this.state.disabled)}
                            onChange={this.handleDefaultExpirationChange}
                            placeholder={this.props.defaultExpiration}
                            disabled={this.state.disabled}
                        />
                    </ControlGroup>
                </Modal.Body>
                <Modal.Footer>
                    <Button
                        data-test-name={'cancel-btn'}
                        onClick={this.handleClose}
                        label={_('Cancel')}
                        autoFocus
                    />
                    <Button
                        appearance="primary"
                        data-test-name={'save-btn'}
                        disabled={this.state.isWorking}
                        onClick={this.handleSave}
                        label={_('Save')}
                    />
                </Modal.Footer>
            </Modal>
        );
    }
}

export default TokenSettingsModal;
