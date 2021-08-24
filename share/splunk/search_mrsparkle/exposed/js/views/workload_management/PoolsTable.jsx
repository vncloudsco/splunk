import _ from 'underscore';
import { createTestHook } from 'util/test_support';
import React from 'react';
import PropTypes from 'prop-types';
import Table from '@splunk/react-ui/Table';
import Success from '@splunk/react-icons/Success';
import Button from '@splunk/react-ui/Button';
import Tooltip from '@splunk/react-ui/Tooltip';
import Heading from '@splunk/react-ui/Heading';
import css from './WorkloadManagement.pcssm';

const PoolsTable = React.memo((props) => {
    const {
        pools,
        canEditWorkloadPools,
        handlePoolUpdateModalOpenEdit,
        handlePoolDeleteModalOpen,
        categoryCardState,
    } = props;

    return (
        <div {...createTestHook(module.id)} className={'poolTable'}>
            <Heading level={2}>
                {`${categoryCardState.selected.charAt(0).toUpperCase()}${categoryCardState.selected.slice(1)} 
                ${_('Pools').t()}`}
            </Heading>
            <Table stripeRows>
                <Table.Head>
                    <Table.HeadCell align="center">{_('Category').t()}</Table.HeadCell>
                    <Table.HeadCell align="center">{_('Workload Pool').t()}</Table.HeadCell>
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
                    <Table.HeadCell align="center">{_('Default Pool').t()}</Table.HeadCell>
                    { canEditWorkloadPools ? <Table.HeadCell align="center">{_('Actions').t()}</Table.HeadCell> : null }

                </Table.Head>
                <Table.Body>
                    {pools.map(row => (
                        <Table.Row key={row.id}>
                            <Table.Cell align="center">{row.getPoolCategory()}</Table.Cell>
                            <Table.Cell align="center">{row.getName()}</Table.Cell>
                            <Table.Cell align="center">{row.getCpuWeight()}</Table.Cell>
                            <Table.Cell align="center">{row.getCpuAllocatedPercent()}%</Table.Cell>
                            <Table.Cell align="center">{row.getMemWeight()}%</Table.Cell>
                            <Table.Cell align="center">{row.getMemAllocatedPercent()}%</Table.Cell>
                            <Table.Cell align="center">
                                {
                                    row.isDefaultPool() ?
                                        <div className={css.successIcon}>
                                            <Success size="1em" />
                                        </div> : null
                                }
                            </Table.Cell>
                            { canEditWorkloadPools ?
                                <Table.Cell align="center">
                                    <Button
                                        label={_('Edit').t()}
                                        appearance="pill"
                                        value={row}
                                        onClick={handlePoolUpdateModalOpenEdit}
                                        size="small"
                                        classNamePrivate={css.link}
                                    />
                                    <Button
                                        label={_('Delete').t()}
                                        appearance="pill"
                                        value={row}
                                        onClick={handlePoolDeleteModalOpen}
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
});


PoolsTable.propTypes = {
    pools: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    canEditWorkloadPools: PropTypes.bool.isRequired,
    handlePoolUpdateModalOpenEdit: PropTypes.func.isRequired,
    handlePoolDeleteModalOpen: PropTypes.func.isRequired,
};

export default PoolsTable;
