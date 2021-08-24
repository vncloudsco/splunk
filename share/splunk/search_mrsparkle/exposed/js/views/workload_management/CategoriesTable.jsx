import _ from 'underscore';
import { createTestHook } from 'util/test_support';
import React from 'react';
import PropTypes from 'prop-types';
import Table from '@splunk/react-ui/Table';
import Button from '@splunk/react-ui/Button';
import Tooltip from '@splunk/react-ui/Tooltip';
import Heading from '@splunk/react-ui/Heading';
import css from './WorkloadManagement.pcssm';

const CategoriesTable = (props) => {
    const {
        categoryCardState,
        handleCategoryRowNameClick,
        categories,
        canEditWorkloadPools,
        handleCategoryUpdateModalOpenEdit,
    } = props;

    return (
        <div {...createTestHook(module.id)} className={'categoryTable'}>
            <Heading level={2}>{_('Categories').t()}</Heading>
            <Table stripeRows>
                <Table.Head>
                    <Table.HeadCell align="center">{_('Category').t()}</Table.HeadCell>
                    <Table.HeadCell align="center">
                        {_('Configured CPU Weight').t()}&nbsp;
                        <Tooltip content="The total CPU weight available to pools in the category." />
                    </Table.HeadCell>
                    <Table.HeadCell align="center">
                        {_('Allocated CPU %').t()}&nbsp;
                        <Tooltip content="The percentage of available CPU allocated to pools in the category." />
                    </Table.HeadCell>
                    <Table.HeadCell align="center">
                        {_('Configured Memory Limit %').t()}&nbsp;
                        <Tooltip content="The maximum percentage of Memory available to pools in the category." />
                    </Table.HeadCell>
                    <Table.HeadCell align="center">
                        {_('Allocated Memory Limit %').t()}&nbsp;
                        <Tooltip content="The percentage of available Memory allocated to pools in the category." />
                    </Table.HeadCell>
                    { canEditWorkloadPools ? <Table.HeadCell align="center">{_('Actions').t()}</Table.HeadCell> : null }

                </Table.Head>
                <Table.Body>
                    {categories.map(row => (
                        <Table.Row
                            key={row.id}
                            style={{ backgroundColor: categoryCardState.selected === row.getName() ?
                                    'lightyellow' : '' }}
                        >
                            <Table.Cell
                                align="center"
                                onClick={handleCategoryRowNameClick}
                                data={row}
                            >
                                {row.getName()}
                            </Table.Cell>
                            <Table.Cell align="center">{row.getCpuWeight()}</Table.Cell>
                            <Table.Cell align="center">{row.getCpuAllocatedPercent()}%</Table.Cell>
                            <Table.Cell align="center">{row.getMemWeight()}%</Table.Cell>
                            <Table.Cell align="center">{row.getMemAllocatedPercent()}%</Table.Cell>
                            { canEditWorkloadPools ?
                                <Table.Cell align="center">
                                    <Button
                                        label={_('Edit').t()}
                                        appearance="pill"
                                        value={row}
                                        onClick={handleCategoryUpdateModalOpenEdit}
                                        size="small"
                                        classNamePrivate={css.link}
                                    />
                                </Table.Cell> : null
                            }
                        </Table.Row>
                    ))}
                </Table.Body>
            </Table>
        </div>
    );
};


CategoriesTable.propTypes = {
    categoryCardState: PropTypes.shape({}).isRequired,
    handleCategoryRowNameClick: PropTypes.func.isRequired,
    categories: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    canEditWorkloadPools: PropTypes.bool.isRequired,
    handleCategoryUpdateModalOpenEdit: PropTypes.func.isRequired,
};

export default CategoriesTable;
