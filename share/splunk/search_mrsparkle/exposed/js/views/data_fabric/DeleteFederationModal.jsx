import React from 'react';
import Backbone from 'backbone';
import { after } from 'underscore';
import PropTypes from 'prop-types';
import querystring from 'querystring';
import Button from '@splunk/react-ui/Button';
import { createRESTURL } from '@splunk/splunk-utils/url';
import { _ } from '@splunk/ui-utils/i18n';
import { defaultFetchInit, handleResponse, handleError } from '@splunk/splunk-utils/fetch';
import { sprintf } from '@splunk/ui-utils/format';
import Modal from '@splunk/react-ui/Modal';
import Message from '@splunk/react-ui/Message';

class DeleteFederation extends React.Component {
    constructor(props) {
        super(props);

        this.state = { err: null };
    }

    sendPasswordRequest = (url, method, responseCode = 200) => {
        const data = { output_mode: 'json' };
        return fetch(createRESTURL(`storage/fshpasswords/${url}?${querystring.encode(data)}`), {
            ...defaultFetchInit,
            method,
        })
            .then(handleResponse(responseCode))
            .catch(handleError());
    };

    deleteFunc = () => {
        const { federation, fshRoles } = this.props;
        const name = federation.entry.get('name');
        const closeAction = after(1 + fshRoles.length, () => {
            this.setState({ err: null });
            this.props.closeModal({ update: true });
        });

        const username = federation.entry.content.get('splunk.serviceAccount');
        const url = encodeURIComponent(`${name}:${username}`);


        const deleteFshAndRoles = () => {
            federation.destroy().done(closeAction);
            fshRoles.forEach((role) => {
                if (role.removeProvider([name])) {
                    role.save({}, { traditional: true });
                }
                closeAction();
            });
        };

        /* when users retry and the password entry cannot be found,
        directly delete other related federation and roles.
        Otherwise password has to be deleted prior to federation provider,
        because deleting password will disable the corresponding entry in federated.conf */
        if (this.state.err) {
            this.sendPasswordRequest(url, 'GET', 404).then(deleteFshAndRoles);
        } else {
            this.sendPasswordRequest(url, 'DELETE').then(deleteFshAndRoles).catch(() => this.setState({ err: true }));
        }
    };

    render() {
        const { closeModal, federation } = this.props;
        const name = federation && federation.entry.get('name');
        const deleteMsg = (
            <Message type="warning">
                {sprintf(_('Are you sure you want to delete the federated provider: %(name)s?'), { name })}
            </Message>
        );
        const errMsg = (
            <Message type="error">{sprintf(_("Could't delete %(name)s. Do you want to retry?"), { name })}</Message>
        );

        return (
            <Modal style={{ width: '600px' }} onRequestClose={closeModal} open={this.props.open}>
                <Modal.Header title={_('Delete Federated Provider')} onRequestClose={closeModal} />
                <Modal.Body>{this.state.err ? errMsg : deleteMsg}</Modal.Body>
                <Modal.Footer>
                    <Button
                        data-test="cancel-delete-btn"
                        appearance="secondary"
                        onClick={closeModal}
                        label={_('Cancel')}
                    />
                    <Button
                        data-test="retry-delete-btn"
                        appearance="primary"
                        onClick={this.deleteFunc}
                        label={this.state.err ? _('Retry') : _('Delete')}
                    />
                </Modal.Footer>
            </Modal>
        );
    }
}

DeleteFederation.defaultProps = {
    federation: undefined,
};

DeleteFederation.propTypes = {
    open: PropTypes.bool.isRequired,
    closeModal: PropTypes.func.isRequired,
    fshRoles: PropTypes.instanceOf(Backbone.Collection).isRequired,
    federation: PropTypes.instanceOf(Backbone.Model),
};

export default DeleteFederation;
