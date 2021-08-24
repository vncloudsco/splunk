import React from 'react';
import PropTypes from 'prop-types';
import Backbone from 'backbone';
import { values } from 'underscore';
import Table from '@splunk/react-ui/Table';
import Link from '@splunk/react-ui/Link';
import { _ } from '@splunk/ui-utils/i18n';
import Message from '@splunk/react-ui/Message';
import DeleteFederationModal from './DeleteFederationModal';

import './DataFabric.pcss';

class FederationsTable extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            sortKey: 'name',
            sortDir: 'asc',
            open: false,
        };
    }

    handleSort = (e, { sortKey }) => {
        this.setState((state) => {
            const prevSortKey = state.sortKey;
            const prevSortDir = prevSortKey === sortKey ? state.sortDir : 'none';
            const nextSortDir = prevSortDir === 'asc' ? 'desc' : 'asc';
            return {
                sortKey,
                sortDir: nextSortDir,
            };
        });
    };

    openDeleteModal = (federation) => {
        this.setState({ open: true, deleteFederation: federation });
    };

    handleRequestClose = ({ update }) => {
        this.setState({ open: false });
        if (update) {
            this.props.refreshDfs();
        }
    };

    generateRows = (federations, fshRoles) => {
        const rowValues = federations.map(federation => federation.generateContent());
        return fshRoles.addRolesToTable(rowValues);
    };

    render() {
        const columns = [
            { sortKey: 'name', label: _('Name'), key: 'name' },
            { sortKey: 'type', label: _('Type'), key: 'type' },
            { sortKey: 'ip', label: _('IP Address'), key: 'ip' },
            { sortKey: 'username', label: _('User Account'), key: 'username' },
            { label: _('Roles'), key: 'roles' },
            { label: _('Actions'), key: 'actions' },
        ];
        const { sortKey, sortDir } = this.state;
        const rows = this.generateRows(this.props.federations, this.props.fshRoles);
        const providersWithoutRoles = [];

        const providersTable = (
            <Table stripeRows key="providers-table">
                <Table.Head>
                    {columns.map(headData => (
                        <Table.HeadCell
                            key={headData.key}
                            onSort={headData.sortKey && this.handleSort}
                            sortKey={headData.sortKey && headData.sortKey}
                            sortDir={headData.sortKey && headData.sortKey === sortKey ? sortDir : 'none'}
                        >
                            {headData.label}
                        </Table.HeadCell>
                    ))}
                </Table.Head>
                <Table.Body style={{ backgroundColor: 'white' }}>
                    {values(rows).sort((rowA, rowB) => {
                        if (sortDir === 'asc') {
                            return rowA[sortKey] > rowB[sortKey] ? 1 : -1;
                        }
                        if (sortDir === 'desc') {
                            return rowB[sortKey] > rowA[sortKey] ? 1 : -1;
                        }
                        return 0;
                    }).map((row) => {
                        const { name, type, ip, username, federation, roles } = row;
                        if (!roles.length) {
                            providersWithoutRoles.push(name);
                        }
                        return (
                            <Table.Row key={`${name}-row`}>
                                <Table.Cell key={name} style={{ maxWidth: '200px' }}>{name}</Table.Cell>
                                <Table.Cell key={type}>
                                    {type === 'splunk' ? _('Remote Splunk Enterprise') : type}
                                </Table.Cell>
                                <Table.Cell key={ip}>{ip}</Table.Cell>
                                <Table.Cell key={username}>{username}</Table.Cell>
                                <Table.Cell key={`${name}-roles`}>{roles.join(', ')}</Table.Cell>
                                <Table.Cell key={`${name}-action`}>
                                    <Link
                                        style={{ marginRight: '1em' }}
                                        key={`${name}-edit-action`}
                                        data-test="edit-link"
                                        onClick={() => this.props.edit(federation)}
                                    >
                                        {_('Edit')}
                                    </Link>
                                    <Link
                                        key={`${name}-delete-action`}
                                        data-test="delete-link"
                                        onClick={() => this.openDeleteModal(federation)}
                                    >
                                        {_('Delete')}
                                    </Link>
                                </Table.Cell>
                            </Table.Row>
                        );
                    })}
                </Table.Body>
            </Table>
        );

        return [
            <DeleteFederationModal
                key="delete-provider-modal"
                open={this.state.open}
                closeModal={this.handleRequestClose}
                federation={this.state.deleteFederation}
                fshRoles={this.props.fshRoles}
            />,
            providersWithoutRoles.length > 0 && <Message type="warning" key="no-roles-warning">
                {providersWithoutRoles.length === 1
                    ? `${_('The following federated provider is missing a role:')} ${providersWithoutRoles[0]}`
                    : `${_('The following providers are missing a role: ')} 
                    ${providersWithoutRoles.join(', ')}`
                }
            </Message>,
            providersTable,
        ];
    }
}

FederationsTable.propTypes = {
    federations: PropTypes.arrayOf(PropTypes.instanceOf(Backbone.Model)).isRequired,
    edit: PropTypes.func.isRequired,
    fshRoles: PropTypes.instanceOf(Backbone.Collection).isRequired,
    refreshDfs: PropTypes.func.isRequired,
};

export default FederationsTable;
