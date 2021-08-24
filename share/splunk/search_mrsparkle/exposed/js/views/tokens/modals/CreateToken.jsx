import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { _ } from '@splunk/ui-utils/i18n';
import { sprintf } from '@splunk/ui-utils/format';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import Message from '@splunk/react-ui/Message';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Text from '@splunk/react-ui/Text';

import { getDefaultButtonLabel, getPrimaryButtonLabel, isValidName, isValidAudience, isValidTokenTime } from '../Utils';
import DateTimePicker from '../components/DateTimePicker';

const TOKEN_HELP = _('Token appears here after creation and is no longer accessible after you close this window.');

class CreateToken extends Component {
    static propTypes = {
        open: PropTypes.bool.isRequired,
        objectNameSingular: PropTypes.string.isRequired,
        handleRequestClose: PropTypes.func.isRequired,
        setShouldRefreshOnClose: PropTypes.func.isRequired,
        callCreateToken: PropTypes.func.isRequired,
        username: PropTypes.string.isRequired,
        permissions: PropTypes.shape({
            editAll: PropTypes.bool,
        }).isRequired,
    }

    constructor(props, context) {
        super(props, context);
        this.state = {
            /** Boolean indicating whether the page is working (saving, deleting, ...). Used to disable button. */
            isWorking: false,
            /** String containing the error message, if any */
            errorMessage: '',
            /** String containing the name of the user to create the token for. */
            name: this.props.username,
            tokenReady: false,
            /** String containing descriptor for the tokens usecase. */
            audience: '',
            expiresOn: '',
            notBefore: '',
        };
    }

    handleSave = () => {
        this.setState({
            isWorking: true,
        });
        if (!isValidName(this.state.name) || !isValidAudience(this.state.audience) ||
            !isValidTokenTime(this.state.expiresOn) || !isValidTokenTime(this.state.notBefore)) {
            this.setState({
                isWorking: false,
                errorMessage: _('Error in highlighted fields.'),
            });
        } else {
            const data = {
                name: this.state.name,
                audience: this.state.audience,
                expires_on: this.state.expiresOn,
                not_before: this.state.notBefore,
                output_mode: 'json',
            };

            this.props.callCreateToken(data)
                .then((response) => {
                    this.handleSuccess(response);
                })
                .catch((response) => {
                    this.setState({
                        isWorking: false,
                        errorMessage: response.message,
                    });
                });
        }
    }

    handleSuccess = (response) => {
        if (response.entry[0] && response.entry[0].content && response.entry[0].content.token) {
            this.props.setShouldRefreshOnClose();
            this.setState({
                errorMessage: '',
                isWorking: false,
                tokenReady: true,
                token: response.entry[0].content.token,
            });
        } else {
            this.setState({
                errorMessage: _('Unable to create token.'),
            });
        }
    };

    handleClose = () => {
        this.setState({
            isWorking: false,
            errorMessage: '',
        });
        this.props.handleRequestClose();
    };

    handleNameTextChange = (e, { value }) => {
        this.setState({
            name: value,
        });
    };

    handleAudienceTextChange = (e, { value }) => {
        this.setState({
            audience: value,
        });
    };

    handleExpiresOnChange = (value) => {
        this.setState({
            expiresOn: value,
        });
    };

    handleNotBeforeChange = (value) => {
        this.setState({
            notBefore: value,
        });
    }

    render() {
        /** Need to manually set focus to cancel button when token is ready
         * since primary button will be removed on success.
         */
        if (this.state.tokenReady && this.cancelButton) {
            this.cancelButton.focus();
        }
        return (
            <Modal
                onRequestClose={this.handleClose}
                open={this.props.open}
                style={{ width: '500px' }}
                data-test-name={'create-modal'}
            >
                <Modal.Header
                    title={sprintf(_('New %s'), this.props.objectNameSingular)}
                    onRequestClose={this.handleClose}
                />
                <Modal.Body>
                    <Message type={'info'}>
                        {_('You can only create tokens for SAML users if you enable either ' +
                           'attribute query requests or authentication extensions.')}
                    </Message>
                    {this.state.errorMessage && (
                        <Message type="error">{this.state.errorMessage}</Message>
                    )}
                    <ControlGroup
                        label={_('User *')}
                        tooltip={!this.props.permissions.editAll && _('You cannot edit tokens for other users.')}
                        help={(this.state.errorMessage && !isValidName(this.state.name)) ?
                                _('User is a required field and must contain fewer than 1024 characters.') :
                                _('User who will receive this token.')}
                        data-test-name={'name-group'}
                        error={this.state.errorMessage && !isValidName(this.state.name)}
                    >
                        <Text
                            data-test-name={'name-text'}
                            disabled={!this.props.permissions.editAll || this.state.tokenReady}
                            canClear
                            value={this.state.name}
                            error={this.state.errorMessage && !isValidName(this.state.name)}
                            onChange={this.handleNameTextChange}
                            autoFocus
                        />
                    </ControlGroup>
                    <ControlGroup
                        label={_('Audience *')}
                        help={(this.state.errorMessage && !isValidAudience(this.state.audience)) ?
                            _('Audience is a required field and must contain fewer than 256 characters.') :
                            _('Purpose of the token.')}
                        data-test-name={'audience-group'}
                        error={this.state.errorMessage && !isValidAudience(this.state.audience)}
                    >
                        <Text
                            data-test-name={'audience-text'}
                            disabled={this.state.tokenReady}
                            canClear
                            value={this.state.audience}
                            error={this.state.errorMessage && !isValidAudience(this.state.audience)}
                            onChange={this.handleAudienceTextChange}
                        />
                    </ControlGroup>
                    <DateTimePicker
                        label={_('Expiration')}
                        data-test-name={'expires-on-group'}
                        value={this.state.expiresOn}
                        onChange={this.handleExpiresOnChange}
                        error={this.state.errorMessage && !isValidTokenTime(this.state.expiresOn)}
                        disabled={this.state.tokenReady}
                    />
                    <DateTimePicker
                        label={_('Not Before')}
                        data-test-name={'not-before-group'}
                        value={this.state.notBefore}
                        onChange={this.handleNotBeforeChange}
                        error={this.state.errorMessage && !isValidTokenTime(this.state.notBefore)}
                        disabled={this.state.tokenReady}
                        tooltip={_('Token cannot be used before this time.')}
                    />
                    <ControlGroup
                        label={_('Token')}
                        help={TOKEN_HELP}
                        data-test-name={'token-group'}
                    >
                        <Text
                            data-test-name={'token-text'}
                            value={this.state.token}
                            multiline
                            rowsMin={2}
                            disabled={!this.state.tokenReady}
                        />
                    </ControlGroup>
                </Modal.Body>
                <Modal.Footer>
                    <Button
                        data-test-name={'cancel-btn'}
                        onClick={this.handleClose}
                        label={getDefaultButtonLabel(this.state.tokenReady)}
                        ref={(button) => { this.cancelButton = button; }}
                    />
                    {!this.state.tokenReady && (
                        <Button
                            appearance="primary"
                            data-test-name={'save-btn'}
                            disabled={this.state.isWorking}
                            onClick={this.handleSave}
                            label={getPrimaryButtonLabel(this.state.isWorking)}
                        />
                    )}
                </Modal.Footer>
            </Modal>
        );
    }
}

export default CreateToken;

