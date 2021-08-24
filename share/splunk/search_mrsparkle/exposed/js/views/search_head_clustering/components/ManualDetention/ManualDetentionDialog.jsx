/**
 * @author jsolis
 * @date 2/27/18
 *
 * Manual Detention Dialog for Search Head Clustering
 */

import React, { Component } from 'react';
import $ from 'jquery';
import { _ } from '@splunk/ui-utils/i18n';
import { has } from 'lodash';
import Button from '@splunk/react-ui/Button';
import { createDocsURL } from '@splunk/splunk-utils/url';
import Link from '@splunk/react-ui/Link';
import Modal from '@splunk/react-ui/Modal';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import Message from '@splunk/react-ui/Message';
import PropTypes from 'prop-types';
import ManualDetentionSwitch from './Switch';

const docUrl = createDocsURL('learnmore.sh.detention');
const learnMore = (<Link to={docUrl} openInNewContext>{_('Learn more')}</Link>);

class ManualDetentionDialog extends Component {
    constructor(props) {
        super(props);
        this.state = {
            open: has(props, 'open') ? props.open : false,
            memberName: has(props, 'memberName') ? props.memberName : '',
            mgmt_uri: has(props, 'mgmt_uri') ? props.mgmt_uri : '',
            initialSwitchValue: props.model.entry.content.get('manual_detention') === 'on' ? 'off' : 'on',
            newSwitchValue: props.model.entry.content.get('manual_detention') === 'on' ? 'off' : 'on',
            spinner: false,
            submitBtn: true,
            success: '',
            error: '',
        };

        ['onRequestClose', 'onSubmit', 'handleSwitchToggle'].forEach(
            (name) => {
                this[name] = this[name].bind(this);
            },
        );
    }

    onRequestClose() {
        this.setState({ open: false });
    }

    onSubmit() {
        this.setState({
            error: '',
            success: '',
            spinner: true,
        });
        this.props.model.entry.content.set({
            mgmt_uri: this.state.mgmt_uri,
        });
        this.props.model.save().then(null, (response) => {
            if (response.status === 200) {
                this.props.collection.entities.model.captainInstance.pollServiceReady().then(() => {
                    this.props.controller.trigger('refreshEntities');
                    this.setState({
                        spinner: false,
                        success: _('Manual detention request succeeded.'),
                    });
                });
            } else {
                this.setState({
                    spinner: false,
                    error: _('Error setting manual detention.'),
                });
            }
        });
    }

    handleSwitchToggle(toggleSwitchValue) {
        if (this.state.initialSwitchValue !== toggleSwitchValue) {
            this.setState({ submitBtn: false });
        } else {
            this.setState({ submitBtn: true });
        }
    }

    render() {
        let errorMsg = null;
        if (this.state.error) {
            errorMsg = (
                <Message fill type="error">{this.state.error}</Message>
            );
        }
        let succesMsg = null;
        let closeBtn = null;
        let submitBtn = (<Button
            disabled={this.state.submitBtn}
            appearance="primary"
            onClick={this.onSubmit}
            label={_('Submit')}
            id={'submitBtn'}
        />);

        if (this.state.success) {
            $('.content').hide();
            succesMsg = (
                <Message fill type="success">{this.state.success}</Message>
            );
            submitBtn = null;
            closeBtn = (<Button
                onClick={this.onRequestClose}
                label={_('Close')}
            />);
        }

        return (
            <Modal id="ManualDetentionDialogModal" open={this.state.open} style={{ width: '550px' }}>
                <Modal.Header title={_('Manual Detention')} onRequestClose={this.onRequestClose} />

                <Modal.Body>
                    { errorMsg }
                    { succesMsg }

                    <div className="content">
                        <ManualDetentionSwitch
                            model={this.props.model}
                            handleSwitchToggle={this.handleSwitchToggle}
                        />

                        <p>
                            {_(`Are you sure you want to turn ${this.state.newSwitchValue} manual detention for `)}
                            <b>{this.state.memberName}</b>
                        </p>

                        <p>
                            <i className="icon-alert" />
                            {_('Here are some details about what will happen if you choose to continue. ')}
                            {learnMore}
                        </p>
                    </div>
                </Modal.Body>

                <Modal.Footer>
                    { this.state.spinner ? <WaitSpinner style={{ margin: '0px 10px -3px 0px' }} /> : null }
                    { closeBtn }
                    { submitBtn }
                </Modal.Footer>
            </Modal>
        );
    }
}

ManualDetentionDialog.propTypes = {
    mgmt_uri: PropTypes.string.isRequired,
    open: PropTypes.bool.isRequired,
    model: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    controller: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    collection: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    memberName: PropTypes.string.isRequired,
};

export default ManualDetentionDialog;
