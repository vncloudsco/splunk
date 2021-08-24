import _ from 'underscore';
import { createTestHook } from 'util/test_support';
import React from 'react';
import PropTypes from 'prop-types';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Modal from '@splunk/react-ui/Modal';
import P from '@splunk/react-ui/Paragraph';
import Text from '@splunk/react-ui/Text';
import Slider from '@splunk/react-ui/Slider';
import Switch from '@splunk/react-ui/Switch';
import Number from '@splunk/react-ui/Number';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import RadioList from '@splunk/react-ui/RadioList';
import StaticContent from '@splunk/react-ui/StaticContent';
import Message from '@splunk/react-ui/Message';
import css from './WorkloadManagement.pcssm';

const PoolUpdateModal = (props) => {
    const {
        poolUpdateModalOpen,
        poolUpdateModalState,
        handlePoolUpdateModalClose,
        handlePoolUpdateModalTextChange,
        handlePoolUpdateModalCheckbox,
        handlePoolUpdateModalSubmit,
    } = props;

    const labelWidth = 150;

    return (
        <div {...createTestHook(module.id)} className="workload-pool-update-modal">
            <Modal
                onRequestClose={poolUpdateModalState.wait ? null : handlePoolUpdateModalClose}
                open={poolUpdateModalOpen}
                style={{ width: '500px' }}
            >
                <Modal.Header
                    title={poolUpdateModalState.title}
                    onRequestClose={poolUpdateModalState.wait ? null : handlePoolUpdateModalClose}
                />
                <Modal.Body>
                    {poolUpdateModalState.backendErrorMsg ?
                        <Message fill type="error">
                            {poolUpdateModalState.backendErrorMsg}
                        </Message> : null
                    }
                    <P />
                    {poolUpdateModalState.edit ?
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('Pool Category').t()}
                            tooltip={_('Category for this workload pool').t()}
                            data-test="PoolCategory"
                        >
                            <StaticContent
                                data-test="static-content-category"
                            >
                                {poolUpdateModalState.category}
                            </StaticContent>
                        </ControlGroup>
                    :
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('Pool Category').t()}
                            data-test="PoolUpdateCategory"
                            tooltip={_('Specify a category for this workload pool').t()}
                            help={poolUpdateModalState.categoryErrorMsg}
                            error={poolUpdateModalState.categoryError}
                        >
                            <RadioList
                                value={poolUpdateModalState.category}
                                onChange={handlePoolUpdateModalTextChange}
                                name="category"
                            >
                                <RadioList.Option value={'search'}>{_('Search').t()}</RadioList.Option>
                                <RadioList.Option value={'ingest'}>{_('Ingest').t()}</RadioList.Option>
                                <RadioList.Option value={'misc'}>{_('Misc').t()}</RadioList.Option>
                                <StaticContent
                                    data-test="static-content-miscHelpTxt"
                                    className={css.miscHelpTxt}
                                >
                                    {_('Note: Misc category applies to modular inputs and scripted inputs only.').t()}
                                </StaticContent>
                            </RadioList>
                        </ControlGroup>
                    }
                    { poolUpdateModalState.edit ? null :
                    <ControlGroup
                        labelWidth={labelWidth}
                        label={_('Name').t()}
                        data-test="PoolUpdateName"
                        tooltip={_('Name of workload pool').t()}
                        help={poolUpdateModalState.nameErrorMsg}
                        error={poolUpdateModalState.nameError}
                    >
                        <Text
                            disabled={poolUpdateModalState.wait}
                            error={poolUpdateModalState.nameError}
                            value={poolUpdateModalState.name}
                            name="name"
                            onChange={handlePoolUpdateModalTextChange}
                            autoComplete={false}
                        />
                    </ControlGroup>
                    }
                    <ControlGroup
                        labelWidth={labelWidth}
                        label={_('CPU Weight').t()}
                        data-test="PoolUpdateCPUWeight"
                        tooltip={_('Specify the fraction of total available CPU for this pool.').t()}
                        help={poolUpdateModalState.cpuWeightErrorMsg}
                        error={poolUpdateModalState.cpuWeightError}
                    >
                        <Slider
                            min={poolUpdateModalState.cpu_weight < 0 ? poolUpdateModalState.cpu_weight : 0}
                            max={poolUpdateModalState.cpu_weight > 100 ? poolUpdateModalState.cpu_weight : 100}
                            step={1}
                            disabled={poolUpdateModalState.wait ||
                            poolUpdateModalState.category === 'ingest' ||
                            poolUpdateModalState.category === 'misc'}
                            error={poolUpdateModalState.cpuWeightError}
                            value={poolUpdateModalState.cpu_weight}
                            name="cpu_weight"
                            onChange={handlePoolUpdateModalTextChange}
                        />
                        <Number
                            inline
                            min={poolUpdateModalState.cpu_weight < 0 ? poolUpdateModalState.cpu_weight : 0}
                            max={poolUpdateModalState.cpu_weight > 100 ? poolUpdateModalState.cpu_weight : 100}
                            step={1}
                            disabled={poolUpdateModalState.wait ||
                            poolUpdateModalState.category === 'ingest' ||
                            poolUpdateModalState.category === 'misc'}
                            value={poolUpdateModalState.cpu_weight}
                            onChange={handlePoolUpdateModalTextChange}
                            style={{ flexBasis: 90 }}
                            name="cpu_weight"
                        />
                    </ControlGroup>
                    <StaticContent
                        data-test="static-content-allocated-cpu"
                        className={css.dynamicAllocated}
                    >
                        {_('Allocated CPU:').t()} {poolUpdateModalState.allocated_cpu}%
                    </StaticContent>
                    <ControlGroup
                        labelWidth={labelWidth}
                        label={_('Memory Limit %').t()}
                        data-test="PoolUpdateMemoryGroup"
                        tooltip={_('Specify a percentage of the total available Memory weight ' +
                            'for the memory control group.').t()}
                        help={poolUpdateModalState.memWeightErrorMsg}
                        error={poolUpdateModalState.memWeightError}
                    >
                        <Slider
                            min={poolUpdateModalState.mem_weight < 0 ? poolUpdateModalState.mem_weight : 0}
                            max={poolUpdateModalState.mem_weight > 100 ? poolUpdateModalState.mem_weight : 100}
                            step={1}
                            disabled={poolUpdateModalState.wait ||
                            poolUpdateModalState.category === 'ingest' ||
                            poolUpdateModalState.category === 'misc'}
                            error={poolUpdateModalState.memWeightError}
                            value={poolUpdateModalState.mem_weight}
                            name="mem_weight"
                            onChange={handlePoolUpdateModalTextChange}
                        />
                        <Number
                            inline
                            min={poolUpdateModalState.mem_weight < 0 ? poolUpdateModalState.mem_weight : 0}
                            max={poolUpdateModalState.mem_weight > 100 ? poolUpdateModalState.mem_weight : 100}
                            step={1}
                            disabled={poolUpdateModalState.wait ||
                            poolUpdateModalState.category === 'ingest' ||
                            poolUpdateModalState.category === 'misc'}
                            value={poolUpdateModalState.mem_weight}
                            onChange={handlePoolUpdateModalTextChange}
                            style={{ flexBasis: 90 }}
                            name="mem_weight"
                        />
                    </ControlGroup>
                    <StaticContent
                        data-test="static-content-allocated-mem"
                        className={css.dynamicAllocated}
                    >
                        {_('Allocated Memory Limit:').t()} {poolUpdateModalState.allocated_mem}%
                    </StaticContent>
                    <ControlGroup
                        labelWidth={labelWidth}
                        label={_('Default Pool').t()}
                        data-test="PoolUpdateDefaultPool"
                        tooltip={_('Turn on to set this workload pool as default pool.').t()}
                    >
                        <Switch
                            disabled={poolUpdateModalState.wait ||
                            poolUpdateModalState.category === 'ingest' ||
                            poolUpdateModalState.category === 'misc'}
                            value="default_category_pool"
                            onClick={handlePoolUpdateModalCheckbox}
                            selected={
                            poolUpdateModalState.category === 'ingest' ||
                            poolUpdateModalState.category === 'misc' ||
                            poolUpdateModalState.default_category_pool}
                            appearance="toggle"
                            size="small"
                        />
                    </ControlGroup>
                </Modal.Body>
                { poolUpdateModalState.wait ?
                    <Modal.Footer>
                        <WaitSpinner size="medium" />
                    </Modal.Footer> :
                    <Modal.Footer>
                        <Button
                            appearance="secondary"
                            onClick={handlePoolUpdateModalClose}
                            label={_('Cancel').t()}
                        />
                        <Button
                            disabled={
                                (poolUpdateModalState.nameError
                                || poolUpdateModalState.memWeightError
                                || poolUpdateModalState.cpuWeightError
                                || !poolUpdateModalState.changed)
                                && (poolUpdateModalState.category === 'search')
                            }
                            appearance="primary"
                            onClick={handlePoolUpdateModalSubmit}
                            label={_('Submit').t()}
                        />
                    </Modal.Footer>
                }
            </Modal>
        </div>
    );
};

PoolUpdateModal.propTypes = {
    poolUpdateModalOpen: PropTypes.bool,
    poolUpdateModalState: PropTypes.shape({}).isRequired,
    handlePoolUpdateModalClose: PropTypes.func.isRequired,
    handlePoolUpdateModalTextChange: PropTypes.func.isRequired,
    handlePoolUpdateModalCheckbox: PropTypes.func.isRequired,
    handlePoolUpdateModalSubmit: PropTypes.func.isRequired,
};

PoolUpdateModal.defaultProps = {
    poolUpdateModalOpen: false,
};

export default PoolUpdateModal;
