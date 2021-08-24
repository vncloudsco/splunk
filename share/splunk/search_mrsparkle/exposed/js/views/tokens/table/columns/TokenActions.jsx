import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { _ } from '@splunk/ui-utils/i18n';
import { sprintf } from '@splunk/ui-utils/format';
import Link from '@splunk/react-ui/Link';
import DeleteTokenModal from 'views/tokens/modals/DeleteToken';
import TokenStatusModal from 'views/tokens/modals/TokenStatus';
import { getDeleteTokenUrl, getChangeStatusURL, getStatusButtonLabel,
    canPerformAction } from 'views/tokens/Utils';

/**
 * Actions column component.
 */
class TokenActions extends Component {
    /**
     * See base-lister/src/Main.jsx for propTypes definition.
     */
    static propTypes = {
        object: PropTypes.shape({
            name: PropTypes.string.isRequired,
            content: PropTypes.shape({
                claims: PropTypes.shape({
                    sub: PropTypes.string.isRequired,
                }),
                status: PropTypes.string.isRequired,
            }),
        }).isRequired,
        nameAttribute: PropTypes.string.isRequired,
        handleRefreshListing: PropTypes.func.isRequired,
        handleDeleteChange: PropTypes.func.isRequired,
        callDeleteToken: PropTypes.func.isRequired,
        callChangeStatus: PropTypes.func.isRequired,
        permissions: PropTypes.shape({
            editAll: PropTypes.bool.isRequired,
            editOwn: PropTypes.bool.isRequired,
            editOwnListAll: PropTypes.bool.isRequired,
        }).isRequired,
        username: PropTypes.string.isRequired,
        objectNameSingular: PropTypes.string.isRequired,
        isEnabled: PropTypes.func.isRequired,
    };

    static defaultProps = {
        nameAttribute: 'name',
    };

    constructor(props, context) {
        super(props, context);
        this.state = {
            /** Boolean that controls the open/close of delete modal */
            deleteOpen: false,
            /** Boolean indicating whether the page is working (saving, deleting, ...). Used to disable button. */
            isWorking: false,
            /** String containing the error message, if any */
            errorMessage: '',
            /** Name of the token */
            title: this.props.object[this.props.nameAttribute] || '',
            /** Owner of the token */
            tokenOwner: this.props.object.content.claims.sub,
            /** Boolean that controls the open/close of status modal */
            statusOpen: false,
        };
    }

    /**
     * Set deleteOpen to true on the state to track delete modal is open.
     */
    openDeleteModal = () => {
        this.setState({
            deleteOpen: true,
        });
    }

    /**
     * Call the Delete Token endpoint and process the promise returned.
     */
    handleDelete = () => {
        this.setState({ isWorking: true });
        this.props.callDeleteToken(getDeleteTokenUrl(this.state.tokenOwner, this.state.title))
            .then(() => {
                // Tokens can only be deleted one at a time, which is why we call
                // the method below with the argument 1. This should be changed if
                // multidelete is to be supported
                this.props.handleDeleteChange(1);
                this.props.handleRefreshListing();
            }, response => this.setState({ isWorking: false, errorMessage: response.message }));
    }

    /**
     * Set isDeleteOpen to false on the state to track delete modal is closed.
     */
    handleDeleteClose = () => {
        this.setState({
            deleteOpen: false,
            errorMessage: '',
        });
    }

    /**
     * Set statusOpen to true on the state to track change status modal is open.
     */
    openStatusModal = () => {
        this.setState({
            statusOpen: true,
        });
    }

    /**
     * Handler for change status modal
     */
    handleChangeStatus = () => {
        this.setState({ isWorking: true });
        this.props.callChangeStatus(
            getChangeStatusURL(
                this.props.object.content.claims.sub,
                this.props.object.name,
                this.props.isEnabled(this.props.object) ? 'disabled' : 'enabled',
            ))
            .then(() => {
                this.props.handleRefreshListing();
            }, response => this.setState({ isWorking: false, errorMessage: response.message }));
    };

    /**
     * Set isStatusOpen to false on the state to track status modal is closed.
     */
    handleStatusClose = () => {
        this.setState({
            isWorking: false,
            statusOpen: false,
            errorMessage: '',
        });
    };

    /**
     * Renders the element.
     * @returns {XML} Markup of the Actions column.
     */
    render() {
        return (
            canPerformAction(this.props.permissions, this.props.object.content.claims.sub,
                this.props.username) &&
                <div
                    style={{
                        display: 'flex',
                        flexDirection: 'row',
                    }}
                >
                    <Link
                        data-test-name={'delete'}
                        key={'delete'}
                        onClick={this.openDeleteModal}
                        style={{ padding: '4px 5px' }}
                    >
                        {_('Delete ')}
                    </Link>
                    <DeleteTokenModal
                        open={this.state.deleteOpen}
                        isWorking={this.state.isWorking}
                        errorMessage={this.state.errorMessage}
                        handleDelete={this.handleDelete}
                        handleClose={this.handleDeleteClose}
                        tokenId={this.state.title}
                        tokenOwner={this.props.object.content.claims.sub}
                    />
                    <Link
                        data-test-name={'changeStatus'}
                        key={'changeStatus'}
                        onClick={this.openStatusModal}
                        style={{ padding: '4px 5px' }}
                    >
                        {this.props.isEnabled(this.props.object) ? _('Disable') : _('Enable')}
                    </Link>
                    <TokenStatusModal
                        open={this.state.statusOpen}
                        isWorking={this.state.isWorking}
                        errorMessage={this.state.errorMessage}
                        modalTitle={sprintf(
                            _('%(enableOrDisable)s %(tokenSingular)s'),
                            {
                                enableOrDisable: this.props.isEnabled(this.props.object) ? _('Disable') : _('Enable'),
                                tokenSingular: this.props.objectNameSingular,
                            },
                        )}
                        handleClose={this.handleStatusClose}
                        changeStatusButtonLabel={
                            getStatusButtonLabel(this.state.isWorking, this.props.object.content.status)
                        }
                        handleChangeStatus={this.handleChangeStatus}
                        tooltipContent={this.state.title}
                        tokenId={this.state.title}
                        tokenOwner={this.props.object.content.claims.sub}
                        enableOrDisable={this.props.isEnabled(this.props.object) ? _('disable') : _('enable')}
                    />
                </div>
        );
    }
}

export default TokenActions;
