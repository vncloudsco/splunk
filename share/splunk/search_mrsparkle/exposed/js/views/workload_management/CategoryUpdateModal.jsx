import _ from 'underscore';
import { createTestHook } from 'util/test_support';
import React from 'react';
import PropTypes from 'prop-types';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Modal from '@splunk/react-ui/Modal';
import Slider from '@splunk/react-ui/Slider';
import Number from '@splunk/react-ui/Number';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import StaticContent from '@splunk/react-ui/StaticContent';
import Message from '@splunk/react-ui/Message';
import css from './WorkloadManagement.pcssm';

const CategoryUpdateModal = (props) => {
    const {
        categoryUpdateModalOpen,
        categoryUpdateModalState,
        handleCategoryUpdateModalClose,
        handleCategoryUpdateModalTextChange,
        handleCategoryUpdateModalSubmit,
    } = props;

    const labelWidth = 150;

    return (
        <div {...createTestHook(module.id)} className="workload-category-update-modal">
            <Modal
                onRequestClose={categoryUpdateModalState.wait ? null : handleCategoryUpdateModalClose}
                open={categoryUpdateModalOpen}
                style={{ width: '500px' }}
            >
                <Modal.Header
                    title={categoryUpdateModalState.title}
                    onRequestClose={categoryUpdateModalState.wait ? null : handleCategoryUpdateModalClose}
                />
                <Modal.Body>
                    {categoryUpdateModalState.backendErrorMsg ?
                        <Message fill type="error">
                            {categoryUpdateModalState.backendErrorMsg}
                        </Message> : null
                    }
                    <ControlGroup
                        labelWidth={labelWidth}
                        label={_('CPU Weight').t()}
                        data-test="CategoryUpdateCPUWeight"
                        tooltip={_('Specify a percentage of the total available CPU weight ' +
                            'for the cpu control group.').t()}
                        help={categoryUpdateModalState.cpuWeightErrorMsg}
                        error={categoryUpdateModalState.cpuWeightError}
                    >
                        <Slider
                            min={categoryUpdateModalState.cpu_weight < 0 ? categoryUpdateModalState.cpu_weight : 0}
                            max={categoryUpdateModalState.cpu_weight > 100 ? categoryUpdateModalState.cpu_weight : 100}
                            step={1}
                            disabled={categoryUpdateModalState.wait}
                            error={categoryUpdateModalState.cpuWeightError}
                            value={categoryUpdateModalState.cpu_weight}
                            name="cpu_weight"
                            onChange={handleCategoryUpdateModalTextChange}
                        />
                        <Number
                            inline
                            min={categoryUpdateModalState.cpu_weight < 0 ? categoryUpdateModalState.cpu_weight : 0}
                            max={categoryUpdateModalState.cpu_weight > 100 ? categoryUpdateModalState.cpu_weight : 100}
                            step={1}
                            value={categoryUpdateModalState.cpu_weight}
                            onChange={handleCategoryUpdateModalTextChange}
                            style={{ flexBasis: 90 }}
                            name="cpu_weight"
                        />
                    </ControlGroup>
                    <StaticContent
                        data-test="static-content-allocated-cpu"
                        className={css.dynamicAllocated}
                    >
                        {_('Allocated CPU:').t()} {categoryUpdateModalState.allocated_cpu}%
                    </StaticContent>
                    <ControlGroup
                        labelWidth={labelWidth}
                        label={_('Memory Limit %').t()}
                        data-test="CategoryUpdateMemoryGroup"
                        tooltip={_('Specify a percentage of the total available Memory weight ' +
                            'for the memory control group.').t()}
                        help={categoryUpdateModalState.memWeightErrorMsg}
                        error={categoryUpdateModalState.memWeightError}
                    >
                        <Slider
                            min={categoryUpdateModalState.mem_weight < 0 ? categoryUpdateModalState.mem_weight : 0}
                            max={categoryUpdateModalState.mem_weight > 100 ? categoryUpdateModalState.mem_weight : 100}
                            step={1}
                            disabled={categoryUpdateModalState.wait}
                            error={categoryUpdateModalState.memWeightError}
                            value={categoryUpdateModalState.mem_weight}
                            name="mem_weight"
                            onChange={handleCategoryUpdateModalTextChange}
                        />
                        <Number
                            inline
                            min={categoryUpdateModalState.mem_weight < 0 ? categoryUpdateModalState.mem_weight : 0}
                            max={categoryUpdateModalState.mem_weight > 100 ? categoryUpdateModalState.mem_weight : 100}
                            step={1}
                            value={categoryUpdateModalState.mem_weight}
                            onChange={handleCategoryUpdateModalTextChange}
                            style={{ flexBasis: 90 }}
                            name="mem_weight"
                        />
                    </ControlGroup>
                    <StaticContent
                        data-test="static-content-allocated-mem"
                        className={css.dynamicAllocated}
                    >
                        {_('Allocated Memory Limit:').t()} {categoryUpdateModalState.allocated_mem}%
                    </StaticContent>
                </Modal.Body>
                { categoryUpdateModalState.wait ?
                    <Modal.Footer>
                        <WaitSpinner size="medium" />
                    </Modal.Footer> :
                    <Modal.Footer>
                        <Button
                            appearance="secondary"
                            onClick={handleCategoryUpdateModalClose}
                            label={_('Cancel').t()}
                        />
                        <Button
                            disabled={
                                categoryUpdateModalState.nameError
                                || categoryUpdateModalState.memWeightError
                                || categoryUpdateModalState.cpuWeightError
                                || !categoryUpdateModalState.changed
                            }
                            appearance="primary"
                            onClick={handleCategoryUpdateModalSubmit}
                            label={_('Submit').t()}
                        />
                    </Modal.Footer>
                }
            </Modal>
        </div>
    );
};

CategoryUpdateModal.propTypes = {
    categoryUpdateModalOpen: PropTypes.bool,
    categoryUpdateModalState: PropTypes.shape({}).isRequired,
    handleCategoryUpdateModalClose: PropTypes.func.isRequired,
    handleCategoryUpdateModalTextChange: PropTypes.func.isRequired,
    handleCategoryUpdateModalSubmit: PropTypes.func.isRequired,
};

CategoryUpdateModal.defaultProps = {
    categoryUpdateModalOpen: false,
};

export default CategoryUpdateModal;
