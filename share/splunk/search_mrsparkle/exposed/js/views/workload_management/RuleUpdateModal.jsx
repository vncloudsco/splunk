import _ from 'underscore';
import { createTestHook } from 'util/test_support';
import React from 'react';
import PropTypes from 'prop-types';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Modal from '@splunk/react-ui/Modal';
import P from '@splunk/react-ui/Paragraph';
import Text from '@splunk/react-ui/Text';
import Select from '@splunk/react-ui/Select';
import Date from '@splunk/react-ui/Date';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import Multiselect from '@splunk/react-ui/Multiselect';
import Message from '@splunk/react-ui/Message';

const RuleUpdateModal = (props) => {
    const {
        ruleUpdateModalOpen,
        ruleUpdateModalState,
        handleRuleUpdateModalClose,
        handleRuleUpdateModalTextChange,
        handleRuleUpdateModalMultiSelectChange,
        handleRuleUpdateModalSubmit,
    } = props;

    const labelWidth = 180;

    return (
        <div {...createTestHook(module.id)} className="workload-rule-update-modal">
            <Modal
                onRequestClose={handleRuleUpdateModalClose}
                open={ruleUpdateModalOpen}
                style={{ width: '500px' }}
                enablePeek
            >
                <Modal.Body>
                    <Modal.Header
                        title={ruleUpdateModalState.title}
                        onRequestClose={handleRuleUpdateModalClose}
                    />
                    {ruleUpdateModalState.backendErrorMsg ?
                        <Message fill type="error">
                            {ruleUpdateModalState.backendErrorMsg}
                        </Message> : null
                    }
                    <P />
                    { ruleUpdateModalState.edit ?
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('Order').t()}
                            data-test="RuleUpdateOrder"
                            tooltip={_('Order of workload rule').t()}
                            help={ruleUpdateModalState.orderErrorMsg}
                            error={ruleUpdateModalState.orderError}
                        >
                            <Text
                                disabled={ruleUpdateModalState.wait}
                                error={ruleUpdateModalState.orderError}
                                value={ruleUpdateModalState.order}
                                name="order"
                                onChange={handleRuleUpdateModalTextChange}
                                autoComplete={false}
                            />
                        </ControlGroup> :
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('Name').t()}
                            data-test="RuleUpdateName"
                            tooltip={_('Name of workload rule').t()}
                            help={ruleUpdateModalState.nameErrorMsg}
                            error={ruleUpdateModalState.nameError}
                        >
                            <Text
                                disabled={ruleUpdateModalState.wait}
                                error={ruleUpdateModalState.nameError}
                                value={ruleUpdateModalState.name}
                                name="name"
                                onChange={handleRuleUpdateModalTextChange}
                                autoComplete={false}
                            />
                        </ControlGroup>
                    }
                    <ControlGroup
                        labelWidth={labelWidth}
                        label={_('Predicate (Condition)').t()}
                        data-test="RuleUpdatePredicate"
                        tooltip={_('Specify a condition for this rule. ' +
                            'The format is <type>=<value> with optional AND, OR, NOT, (). ' +
                            'Valid <type> include "app", "role", "user", "index", "search_type", ' +
                            '"search_mode", "search_time_range", and "runtime".').t()}
                        error={ruleUpdateModalState.predicateError}
                        help={ruleUpdateModalState.predicateErrorMsg || _('e.g. index=security AND role=admin').t()}
                    >
                        <Text
                            multiline
                            rows={4}
                            disabled={ruleUpdateModalState.wait}
                            value={ruleUpdateModalState.predicate}
                            name="predicate"
                            onChange={handleRuleUpdateModalTextChange}
                            autoComplete={false}
                        />
                    </ControlGroup>
                    <ControlGroup
                        labelWidth={labelWidth}
                        label={_('Schedule').t()}
                        data-test="RuleUpdateSchedule"
                        tooltip={_('Set the time interval during which this rule is valid.').t()}
                    >
                        <Select
                            disabled={ruleUpdateModalState.wait}
                            value={ruleUpdateModalState.schedule}
                            name="schedule"
                            onChange={handleRuleUpdateModalTextChange}
                        >
                            <Select.Option
                                key={'always_on'}
                                label={_('Always On').t()}
                                value={''}
                            />
                            <Select.Option
                                key={'time_range'}
                                label={_('Time Range').t()}
                                value={'time_range'}
                            />
                            <Select.Option
                                key={'every_day'}
                                label={_('Every Day').t()}
                                value={'every_day'}
                            />
                            <Select.Option
                                key={'every_week'}
                                label={_('Every Week').t()}
                                value={'every_week'}
                            />
                            <Select.Option
                                key={'every_month'}
                                label={_('Every Month').t()}
                                value={'every_month'}
                            />
                        </Select>
                    </ControlGroup>

                    {ruleUpdateModalState.schedule === 'time_range' && (
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('From').t()}
                            data-test="RuleUpdateTimeStart"
                        >
                            <Date
                                inline
                                disabled={ruleUpdateModalState.wait}
                                name={'start_date'}
                                value={ruleUpdateModalState.start_date}
                                onChange={handleRuleUpdateModalTextChange}
                                data-test="calendar"
                            />
                            <Select
                                disabled={ruleUpdateModalState.wait}
                                value={ruleUpdateModalState.start_time}
                                name="start_time"
                                onChange={handleRuleUpdateModalTextChange}
                            >
                                {ruleUpdateModalState.timeItems.map(row => (
                                    <Select.Option
                                        key={`'time_range_start_time' ${row}`}
                                        label={row}
                                        value={row}
                                    />
                                ))}
                            </Select>
                        </ControlGroup>
                    )}
                    {ruleUpdateModalState.schedule === 'time_range' && (
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('To').t()}
                            data-test="RuleUpdateTimeEnd"
                        >
                            <Date
                                inline
                                disabled={ruleUpdateModalState.wait}
                                name={'end_date'}
                                value={ruleUpdateModalState.end_date}
                                onChange={handleRuleUpdateModalTextChange}
                                data-test="calendar"
                            />
                            <Select
                                disabled={ruleUpdateModalState.wait}
                                value={ruleUpdateModalState.end_time}
                                name="end_time"
                                onChange={handleRuleUpdateModalTextChange}
                            >
                                {ruleUpdateModalState.timeItems.map(row => (
                                    <Select.Option
                                        key={`'time_range_end_time' ${row}`}
                                        label={row}
                                        value={row}
                                    />
                                ))}
                            </Select>
                        </ControlGroup>
                    )}
                    {ruleUpdateModalState.schedule === 'every_day' && (
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('From').t()}
                            data-test="RuleUpdateEveryDayTimeStart"
                        >
                            <Select
                                disabled={ruleUpdateModalState.wait}
                                value={ruleUpdateModalState.start_time}
                                name="start_time"
                                onChange={handleRuleUpdateModalTextChange}
                            >
                                {ruleUpdateModalState.timeItems.map(row => (
                                    <Select.Option
                                        key={`'every_day_start_time' ${row}`}
                                        label={row}
                                        value={row}
                                    />
                                ))}
                            </Select>
                        </ControlGroup>
                    )}
                    {ruleUpdateModalState.schedule === 'every_day' && (
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('To').t()}
                            data-test="RuleUpdateEveryDayTimeEnd"
                        >
                            <Select
                                disabled={ruleUpdateModalState.wait}
                                value={ruleUpdateModalState.end_time}
                                name="end_time"
                                onChange={handleRuleUpdateModalTextChange}
                            >
                                {ruleUpdateModalState.timeItems.map(row => (
                                    <Select.Option
                                        key={`'every_day_end_time' ${row}`}
                                        label={row}
                                        value={row}
                                    />
                                ))}
                            </Select>
                        </ControlGroup>
                    )}
                    {ruleUpdateModalState.schedule === 'every_week' && (
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('On').t()}
                            data-test="RuleUpdateEveryWeekOn"
                        >
                            <Multiselect
                                inline
                                compact
                                name="every_week_days"
                                defaultValues={ruleUpdateModalState.every_week_days}
                                onChange={handleRuleUpdateModalMultiSelectChange}
                            >
                                <Multiselect.Option label="Sunday" value="0" name="0" />
                                <Multiselect.Option label="Monday" value="1" name="1" />
                                <Multiselect.Option label="Tuesday" value="2" name="2" />
                                <Multiselect.Option label="Wednesday" value="3" name="3" />
                                <Multiselect.Option label="Thursday" value="4" name="4" />
                                <Multiselect.Option label="Friday" value="5" name="5" />
                                <Multiselect.Option label="Saturday" value="6" name="6" />
                            </Multiselect>
                        </ControlGroup>
                    )}
                    {ruleUpdateModalState.schedule === 'every_week' && (
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('From').t()}
                            data-test="RuleUpdateEveryWeekTimeStart"
                        >
                            <Select
                                disabled={ruleUpdateModalState.wait}
                                value={ruleUpdateModalState.start_time}
                                name="start_time"
                                onChange={handleRuleUpdateModalTextChange}
                            >
                                {ruleUpdateModalState.timeItems.map(row => (
                                    <Select.Option
                                        key={`'every_week_start_time' ${row}`}
                                        label={row}
                                        value={row}
                                    />
                                ))}
                            </Select>
                        </ControlGroup>
                    )}
                    {ruleUpdateModalState.schedule === 'every_week' && (
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('To').t()}
                            data-test="RuleUpdateEveryWeekTimeEnd"
                        >
                            <Select
                                disabled={ruleUpdateModalState.wait}
                                value={ruleUpdateModalState.end_time}
                                name="end_time"
                                onChange={handleRuleUpdateModalTextChange}
                            >
                                {ruleUpdateModalState.timeItems.map(row => (
                                    <Select.Option
                                        key={`'every_week_end_time' ${row}`}
                                        label={row}
                                        value={row}
                                    />
                                ))}
                            </Select>
                        </ControlGroup>
                    )}

                    {ruleUpdateModalState.schedule === 'every_month' && (
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('On day').t()}
                            data-test="RuleUpdateEveryMonthOnDay"
                        >
                            <Multiselect
                                inline
                                compact
                                name="every_month_days"
                                defaultValues={ruleUpdateModalState.every_month_days}
                                onChange={handleRuleUpdateModalMultiSelectChange}
                            >
                                {_.range(1, 32).map(row => (
                                    <Multiselect.Option
                                        key={row}
                                        label={row.toString()}
                                        value={row.toString()}
                                        name={row.toString()}
                                    />
                                ))}
                            </Multiselect>
                        </ControlGroup>
                    )}
                    {ruleUpdateModalState.schedule === 'every_month' && (
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('From').t()}
                            data-test="RuleUpdateEveryMonthTimeStart"
                        >
                            <Select
                                disabled={ruleUpdateModalState.wait}
                                value={ruleUpdateModalState.start_time}
                                name="start_time"
                                onChange={handleRuleUpdateModalTextChange}
                            >
                                {ruleUpdateModalState.timeItems.map(row => (
                                    <Select.Option
                                        key={`'every_month_start_time' ${row}`}
                                        label={row}
                                        value={row}
                                    />
                                ))}
                            </Select>
                        </ControlGroup>
                    )}
                    {ruleUpdateModalState.schedule === 'every_month' && (
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('To').t()}
                            data-test="RuleUpdateEveryMonthTimeEnd"
                        >
                            <Select
                                disabled={ruleUpdateModalState.wait}
                                value={ruleUpdateModalState.end_time}
                                name="end_time"
                                onChange={handleRuleUpdateModalTextChange}
                            >
                                {ruleUpdateModalState.timeItems.map(row => (
                                    <Select.Option
                                        key={`'every_month_end_time' ${row}`}
                                        label={row}
                                        value={row}
                                    />
                                ))}
                            </Select>
                        </ControlGroup>
                    )}

                    <ControlGroup
                        labelWidth={labelWidth}
                        label={_('Action').t()}
                        data-test="RuleUpdateWLAction"
                        tooltip={_('Move, Abort and Message actions only apply to in-progress searches. ' +
                            'Include "runtime" condition to enable these actions. ' +
                            'e.g. index=_internal AND runtime>1m').t()}
                        error={ruleUpdateModalState.actionError}
                        help={ruleUpdateModalState.actionErrorMsg}
                    >
                        <Select
                            disabled={ruleUpdateModalState.wait}
                            value={ruleUpdateModalState.action || ''}
                            name="action"
                            onChange={handleRuleUpdateModalTextChange}
                        >
                            {ruleUpdateModalState.getRuleActions.map(action => (
                                <Select.Option
                                    key={action.id}
                                    label={action.label}
                                    value={action.value}
                                />
                            ))}
                        </Select>
                    </ControlGroup>

                    {(ruleUpdateModalState.action === 'move' || _.isEmpty(ruleUpdateModalState.action)) && (
                        <ControlGroup
                            labelWidth={labelWidth}
                            label={_('Workload Pool').t()}
                            data-test="RuleUpdateWLPool"
                            tooltip={_('The workload pool that matches to this rule.').t()}
                            error={ruleUpdateModalState.poolError}
                            help={ruleUpdateModalState.poolErrorMsg}
                        >
                            <Select
                                disabled={ruleUpdateModalState.wait}
                                value={ruleUpdateModalState.workload_pool}
                                name="workload_pool"
                                onChange={handleRuleUpdateModalTextChange}
                            >
                                {ruleUpdateModalState.available_pools.map(option => (
                                    <Select.Option
                                        key={option.id}
                                        label={option.getName()}
                                        value={option.getName()}
                                    />
                                ))}
                            </Select>
                        </ControlGroup>
                    )}
                </Modal.Body>
                { ruleUpdateModalState.wait ?
                    <Modal.Footer>
                        <WaitSpinner size="medium" />
                    </Modal.Footer> :
                    <Modal.Footer>
                        <Button
                            appearance="secondary"
                            onClick={handleRuleUpdateModalClose}
                            label={_('Cancel').t()}
                        />
                        <Button
                            disabled={
                                ruleUpdateModalState.nameError
                                || ruleUpdateModalState.orderError
                                || !ruleUpdateModalState.changed
                            }
                            appearance="primary"
                            onClick={handleRuleUpdateModalSubmit}
                            label={_('Submit').t()}
                        />
                    </Modal.Footer>
                }
            </Modal>
        </div>
    );
};

RuleUpdateModal.propTypes = {
    ruleUpdateModalOpen: PropTypes.bool,
    ruleUpdateModalState: PropTypes.shape({}).isRequired,
    handleRuleUpdateModalClose: PropTypes.func.isRequired,
    handleRuleUpdateModalTextChange: PropTypes.func.isRequired,
    handleRuleUpdateModalMultiSelectChange: PropTypes.func.isRequired,
    handleRuleUpdateModalSubmit: PropTypes.func.isRequired,
};

RuleUpdateModal.defaultProps = {
    ruleUpdateModalOpen: false,
};

export default RuleUpdateModal;
