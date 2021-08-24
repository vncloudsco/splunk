import React from 'react';
import PropTypes from 'prop-types';
import Table from '@splunk/react-ui/Table';
import P from '@splunk/react-ui/Paragraph';
import Text from '@splunk/react-ui/Text';
import Menu from '@splunk/react-ui/Menu';
import 'views/roles/Roles.pcss';
import { _ } from '@splunk/ui-utils/i18n';
import { getMenuLabel } from '../../Utils';

const Capabilities = props => (
    <div>
        <P className="roles-tableHelpText" data-test-name="capabilities-help-text">
            {_('Select specific capabilities for this role.')}
        </P>
        <Table
            stripeRows
            data-test-name="capabilities-table"
            onRequestToggleAllRows={props.handleCapsToggleAll}
            rowSelection={props.rowRolesSelectionState(props.caps)}
        >
            <Table.Head className="roles-modal-thead">
                <Table.HeadCell data-test-name="capabilities-table-head">
                    {_('Capability Name')}
                    <Text
                        inline
                        style={{ marginLeft: '10px' }}
                        placeholder="filter"
                        name="name"
                        onChange={(e, data) => props.handleCapsFiltering(data, 'selectedCaps')}
                        data-test-name="capabilities-table-filter"
                        canClear
                        value={_(props.filterValue)}
                    />
                </Table.HeadCell>
                <Table.HeadDropdownCell
                    data-test-name="capabilities-table-source"
                    label={<div className="roles-menuLabel">{_(getMenuLabel(props.menuSelected))}</div>}
                    width={1}
                >
                    <Menu data-test-name="capabilities-table-menu">
                        <Menu.Item
                            selectable
                            data-test-name="capabilities-table-menu-item-selected"
                            selected={props.menuSelected === 'selected'}
                            onClick={() => props.handleCapsFiltering({ name: 'selected' }, 'selectedCaps')}
                        >
                            {_('Show selected')}
                        </Menu.Item>
                        <Menu.Item
                            selectable
                            data-test-name="capabilities-table-menu-item-unselected"
                            selected={props.menuSelected === 'unselected'}
                            onClick={() => props.handleCapsFiltering({ name: 'unselected' }, 'selectedCaps')}
                        >
                            {_('Show unselected')}
                        </Menu.Item>
                        <Menu.Item
                            selectable
                            data-test-name="capabilities-table-menu-item-native"
                            selected={props.menuSelected === 'native'}
                            onClick={() => props.handleCapsFiltering({ name: 'native' }, 'selectedCaps')}
                        >
                            {_('Show native')}
                        </Menu.Item>
                        <Menu.Item
                            selectable
                            data-test-name="capabilities-table-menu-item-inherited"
                            selected={props.menuSelected === 'inherited'}
                            onClick={() => props.handleCapsFiltering({ name: 'inherited' }, 'selectedCaps')}
                        >
                            {_('Show inherited')}
                        </Menu.Item>
                        <Menu.Item
                            selectable
                            data-test-name="capabilities-table-menu-item-all"
                            selected={props.menuSelected === 'all'}
                            onClick={() => props.handleCapsFiltering({ name: 'all' }, 'selectedCaps')}
                        >
                            {_('Show all')}
                        </Menu.Item>
                    </Menu>
                </Table.HeadDropdownCell>
            </Table.Head>
            <Table.Body data-test-name="capabilities-table-body" >
                {props.caps.map(row => (
                    row.filtered &&
                    <Table.Row
                        key={row.name}
                        data-test-name="capabilities-table-row"
                        onRequestToggle={props.handleCapsToggle}
                        data={row}
                        disabled={row.source === 'inherited' || row.isPreview}
                        selected={row.isPreview || row.selected}
                    >
                        <Table.Cell
                            key={row.name}
                            data-test-name="capabilities-name-cell"
                        >
                            {row.name}
                        </Table.Cell>
                        <Table.Cell
                            key={`${row.name}-${row.source}`}
                            data-test-name="capabilities-source-cell"
                        >
                            {row.isPreview ? _('inherited') : row.source}
                        </Table.Cell>
                    </Table.Row>
                ))}
            </Table.Body>
        </Table>
    </div>
);
Capabilities.propTypes = {
    caps: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    rowRolesSelectionState: PropTypes.func.isRequired,
    menuSelected: PropTypes.string.isRequired,
    handleCapsToggleAll: PropTypes.func.isRequired,
    handleCapsToggle: PropTypes.func.isRequired,
    handleCapsFiltering: PropTypes.func.isRequired,
    filterValue: PropTypes.string.isRequired,
};

export default Capabilities;
