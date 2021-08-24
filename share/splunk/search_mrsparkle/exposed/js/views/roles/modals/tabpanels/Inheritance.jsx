import React from 'react';
import PropTypes from 'prop-types';
import Menu from '@splunk/react-ui/Menu';
import Table from '@splunk/react-ui/Table';
import P from '@splunk/react-ui/Paragraph';
import Text from '@splunk/react-ui/Text';
import 'views/roles/Roles.pcss';
import { _ } from '@splunk/ui-utils/i18n';
import { getMenuLabel } from '../../Utils';

const Inheritance = props => (
    <div>
        <P className="roles-tableHelpText" data-test-name="inheritance-table-help">
            {_('Specify roles from which this role inherits capabilities and indexes. ' +
                'Inherited capabilities and indexes cannot be disabled. If multiple roles ' +
                'are specified, this role inherits capabilities and indexes from all selected roles.')}
        </P>
        <Table
            stripeRows
            data-test-name="inheritance-table"
            onRequestToggleAllRows={props.handleRolesToggleAll}
            rowSelection={props.rowRolesSelectionState(props.roles)}
        >
            <Table.Head className="roles-modal-thead">
                <Table.HeadCell data-test-name="inheritance-table-head-name">
                    {_('Role name')}
                    <Text
                        inline
                        style={{ marginLeft: '10px' }}
                        placeholder="filter"
                        onChange={(e, data) => props.handleRolesFiltering(data, 'roles')}
                        canClear
                        name="name"
                        data-test-name="inheritance-filter-text"
                        value={_(props.filterValue)}
                    />
                </Table.HeadCell>
                <Table.HeadDropdownCell
                    align="center"
                    data-test-name="inheritance-table-menu"
                    label={<div className="roles-menuLabel">{_(getMenuLabel(props.menuSelected))}</div>}
                    width={1}
                >
                    <Menu>
                        <Menu.Item
                            selectable
                            data-test-name="inheritance-table-menu-item-selected"
                            selected={props.menuSelected === 'selected'}
                            onClick={() => props.handleRolesFiltering({ name: 'selected' }, 'roles')}
                        >
                            {_('Show selected')}
                        </Menu.Item>
                        <Menu.Item
                            selectable
                            data-test-name="inheritance-table-menu-item-unselected"
                            selected={props.menuSelected === 'unselected'}
                            onClick={() => props.handleRolesFiltering({ name: 'unselected' }, 'roles')}
                        >
                            {_('Show unselected')}
                        </Menu.Item>
                        <Menu.Item
                            selectable
                            data-test-name="inheritance-table-menu-item-all"
                            selected={props.menuSelected === 'all'}
                            onClick={() => props.handleRolesFiltering({ name: 'all' }, 'roles')}
                        >
                            {_('Show all')}
                        </Menu.Item>
                    </Menu>
                </Table.HeadDropdownCell>
            </Table.Head>
            <Table.Body data-test-name="inheritance-table-body">
                {props.roles.map(row => (
                    row.filtered &&
                    <Table.Row
                        key={row.name}
                        data-test-name="inheritance-table-row"
                        onRequestToggle={props.handleRolesToggle}
                        data={row}
                        selected={!!row.selected}
                    >
                        <Table.Cell
                            key={row.name}
                            data-test-name="inheritance-table-cell"
                        >
                            {row.name}
                        </Table.Cell>
                        <Table.Cell />
                    </Table.Row>
                ))}
            </Table.Body>
        </Table>
    </div>
);

Inheritance.propTypes = {
    roles: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    rowRolesSelectionState: PropTypes.func.isRequired,
    menuSelected: PropTypes.string.isRequired,
    handleRolesToggleAll: PropTypes.func.isRequired,
    handleRolesFiltering: PropTypes.func.isRequired,
    handleRolesToggle: PropTypes.func.isRequired,
    filterValue: PropTypes.string.isRequired,
};

export default Inheritance;
