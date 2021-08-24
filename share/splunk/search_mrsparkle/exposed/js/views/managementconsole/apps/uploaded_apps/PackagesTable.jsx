import _ from 'underscore';
import PropTypes from 'prop-types';
import React, { Component } from 'react';
import Button from '@splunk/react-ui/Button';
import Link from '@splunk/react-ui/Link';
import ColumnLayout from '@splunk/react-ui/ColumnLayout';
import Table from '@splunk/react-ui/Table';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import ActionLink from './ActionLink';
import AppDialog from './AppDialog/AppDialog';
import './PackagesTable.pcss';

const STRINGS = {
    NO_APPS_ALERT: _('You have not uploaded any private apps yet.').t(),
    CONTINUE: _('Continue').t(),
    GENERIC_ERROR: _('Unknown failure: Contact your administrator for details or try again later.').t(),
};

const ACTIONS = {
    INSTALL: 'Install',
    UPDATE: 'Update',
    MORE_INFO: 'More Info',
    VIEW_REPORT: 'View Report',
    DELETE: 'Delete',
};

const ACTION_LINKS = {
    INSTALL: 'install',
    UPDATE: 'update',
    REPORT: 'report',
    DELETE: 'delete',
};

const STATES = {
    NEW: 0,
    RUNNING: 1,
    FAIL: 2,
    SUCCESS: 3,
    STARTED: 4,
};

class PackagesTable extends Component {

    handleAppAction = (e) => {
        e.preventDefault();
        switch (this.props.action) {
            case ACTIONS.INSTALL:
                this.props.onInstallPackage();
                break;
            case ACTIONS.UPDATE:
                this.props.onUpdatePackage();
                break;
            case ACTIONS.DELETE:
                this.props.onDeletePackage();
                break;
            default:
                break;
        }
    }

    render() {
        const installAppLinkProps = {
            action: ACTIONS.INSTALL,
            actionDialogOpen: this.props.actionDialogOpen,
            onActionDialogOpen: this.props.onInstallPackageOpen,
            deploymentInProgress: this.props.deploymentInProgress,
            disabledDuringDeployment: true,
        };

        const updateAppLinkProps = {
            action: ACTIONS.UPDATE,
            actionDialogOpen: this.props.actionDialogOpen,
            onActionDialogOpen: this.props.onUpdatePackageOpen,
            deploymentInProgress: this.props.deploymentInProgress,
            disabledDuringDeployment: true,
        };

        const deleteAppLinkProps = {
            action: ACTIONS.DELETE,
            actionDialogOpen: this.props.actionDialogOpen,
            onActionDialogOpen: this.props.onDeletePackageOpen,
        };

        const moreInfoProps = {
            action: ACTIONS.MORE_INFO,
            actionDialogOpen: this.props.actionDialogOpen,
            onActionDialogOpen: this.props.onMoreInfoOpen,
        };

        const cancelButtonProps = {
            label: this.props.buttonLabel,
            onClick: this.props.onRequestClose,
        };

        const continueButtonProps = {
            label: STRINGS.CONTINUE,
            onClick: this.handleAppAction,
            appearance: 'primary',
        };

        let appDialogProps = {
            title: this.props.actionDialogTitle,
            open: this.props.actionDialogOpen,
        };

        if (this.props.taskStatus !== STATES.RUNNING) {
            appDialogProps = {
                ...appDialogProps,
                onRequestClose: this.props.onRequestClose,
            };
        }

        const appDialogBodyProps = {
            status: this.props.status,
            responseMessage: this.props.responseMessage || STRINGS.GENERIC_ERROR,
        };

        return (
            <div data-test="UploadedApps-PackagesTable">
                <Table stripeRows>
                    <Table.Head>
                        <Table.HeadCell>{_('App').t()}</Table.HeadCell>
                        <Table.HeadCell>{_('Status').t()}</Table.HeadCell>
                        <Table.HeadCell>{_('Actions').t()}</Table.HeadCell>
                        <Table.HeadCell>{_('Date Submitted').t()}</Table.HeadCell>
                        <Table.HeadCell>{_('Version').t()}</Table.HeadCell>
                    </Table.Head>
                    <Table.Body>
                        {this.props.packages.map(row => (
                            <Table.Row data-row-id={row.id} key={row.id}>
                                <Table.Cell data-test="cell-name">
                                    {
                                        row.getApp() ? row.getApp().label : row.getUploadedFileName()
                                    }
                                </Table.Cell>
                                <Table.Cell data-test="cell-status">
                                    {
                                        row.isVetting() &&
                                        <WaitSpinner />
                                    }
                                    &nbsp;
                                    {
                                        row.failedVetting() ? row.getFailedVettingStatus() : row.getStatus()
                                    }
                                    &nbsp;&nbsp;&nbsp;
                                    {
                                        this.props.canEdit && (row.getVettingErrors() || row.failedVetting()) &&
                                        <ActionLink
                                            {...moreInfoProps}
                                            package={row}
                                        />
                                    }
                                </Table.Cell>
                                <Table.Cell data-test="cell-actions">
                                    {
                                        this.props.canEdit && row.getLink(ACTION_LINKS.INSTALL) &&
                                        <ActionLink
                                            {...installAppLinkProps}
                                            package={row}
                                        />
                                    }
                                    {
                                        this.props.canEdit && row.getLink(ACTION_LINKS.UPDATE) &&
                                        <ActionLink
                                            {...updateAppLinkProps}
                                            package={row}
                                        />
                                    }
                                    {
                                        this.props.canEdit && row.getLink(ACTION_LINKS.DELETE) &&
                                        <ActionLink
                                            {...deleteAppLinkProps}
                                            package={row}
                                        />
                                    }
                                    {
                                        this.props.canEdit && row.getLink(ACTION_LINKS.REPORT) &&
                                        !row.getVettingErrors() &&
                                        <Link
                                            to={row.getFullLink(ACTION_LINKS.REPORT)}
                                            openInNewContext
                                            data-test="UploadedApps-ActionLink-ViewReport"
                                        >
                                            { ACTIONS.VIEW_REPORT }
                                        </Link>
                                    }
                                </Table.Cell>
                                <Table.Cell data-test="cell-submitted">{row.getSubmittedAt()}</Table.Cell>
                                <Table.Cell data-test="cell-version">{row.getVersion()}</Table.Cell>
                            </Table.Row>
                        ))}
                    </Table.Body>
                </Table>
                <AppDialog {...appDialogProps} >
                    <AppDialog.Body {...appDialogBodyProps}>
                        {
                            this.props.taskStatus === STATES.RUNNING &&
                            <ColumnLayout>
                                <ColumnLayout.Row>
                                    <ColumnLayout.Column span={5} />
                                    <ColumnLayout.Column span={7}>
                                        <WaitSpinner size="medium" />
                                    </ColumnLayout.Column>
                                </ColumnLayout.Row>
                            </ColumnLayout>
                        }
                    </AppDialog.Body>
                    <AppDialog.Footer>
                        {
                            (this.props.taskStatus !== STATES.RUNNING || this.props.taskStatus === STATES.STARTED) &&
                            <Button
                                disabled={this.props.taskStatus === STATES.STARTED}
                                {...cancelButtonProps}
                                data-test="UploadedApps-CancelCloseButton"
                            />
                        }
                        {
                            (this.props.taskStatus === STATES.NEW || this.props.taskStatus === STATES.STARTED) &&
                            <Button
                                disabled={this.props.taskStatus === STATES.STARTED}
                                {...continueButtonProps}
                                data-test="UploadedApps-ContinueButton"
                            />
                        }
                    </AppDialog.Footer>
                </AppDialog>
                {this.props.packages.length === 0 &&
                <div className="table-flashmessages">
                    <div className="alert alert-info">
                        <i className="icon-alert" />
                        {STRINGS.NO_APPS_ALERT}
                    </div>
                </div>
                }
            </div>
        );
    }
}

PackagesTable.propTypes = {
    packages: PropTypes.arrayOf(PropTypes.shape({})),
    deploymentInProgress: PropTypes.bool,
    action: PropTypes.string,
    actionDialogOpen: PropTypes.bool,
    actionDialogTitle: PropTypes.string,
    responseMessage: PropTypes.oneOfType([PropTypes.string, PropTypes.array]),
    buttonLabel: PropTypes.string,
    taskStatus: PropTypes.number,
    status: PropTypes.string,
    onInstallPackageOpen: PropTypes.func.isRequired,
    onInstallPackage: PropTypes.func.isRequired,
    onRequestClose: PropTypes.func.isRequired,
    canEdit: PropTypes.bool,
    onUpdatePackageOpen: PropTypes.func.isRequired,
    onUpdatePackage: PropTypes.func.isRequired,
    onDeletePackageOpen: PropTypes.func.isRequired,
    onDeletePackage: PropTypes.func.isRequired,
    onMoreInfoOpen: PropTypes.func.isRequired,
};

PackagesTable.defaultProps = {
    packages: undefined,
    deploymentInProgress: false,
    action: undefined,
    actionDialogOpen: false,
    actionDialogTitle: undefined,
    responseMessage: '',
    buttonLabel: undefined,
    taskStatus: undefined,
    status: undefined,
    canEdit: false,
};

export default PackagesTable;
