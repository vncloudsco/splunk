import React from 'react';
import PropTypes from 'prop-types';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import _ from 'underscore';
import P from '@splunk/react-ui/Paragraph';
import Text from '@splunk/react-ui/Text';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import StaticContent from '@splunk/react-ui/StaticContent';
import Date from '@splunk/react-ui/Date';
import { sprintf } from '@splunk/ui-utils/format';
import { createTestHook } from 'util/test_support';
import DisplayRestoreMessage from './DisplayRestoreMessage';
import Confirmation from './Confirmation';
import RestoreHistory from './RestoreHistory';

const RestoreDialog = (props) => {
    const { open, name, retrieveMsg, restoreConfirm, flushConfirm, restoreSize, historyItems } = props;
    const blockRestore = _.isEmpty(retrieveMsg) || retrieveMsg.type === 'error';
    const disableContents = restoreConfirm || flushConfirm;
    const normalMsg = sprintf(_('Are you sure you want to restore %sGB of data?').t(), restoreSize);
    const warningMsg = sprintf(_('Are you sure you want to restore %sGB of data? ' +
        'Retrieving data larger than %sGB might impact search performance.').t(), restoreSize, retrieveMsg.threshold);
    const restoreConfirmMsg = retrieveMsg.type === 'warning' ? warningMsg : normalMsg;
    const startTime = props.start_time;
    const endTime = props.end_time;

    const handleFromChange = (e, { value }) => {
        props.onAttributeChange('start_time', value);
    };

    const handleToChange = (e, { value }) => {
        props.onAttributeChange('end_time', value);
    };

    const pStyle = {
        lineHeight: '30px',
        margin: '0 5px',
    };

    const opaStyle = {
        opacity: restoreConfirm || flushConfirm ? 0.5 : 'inherit',
    };

    return (
        <div>
            <Modal
                onRequestClose={props.onRequestClose}
                open={open}
                style={{ width: '900px' }}
                {...createTestHook(null, 'RestoreArchiveModal')}
            >
                <Modal.Header
                    style={opaStyle}
                    title={_('Restore Archive').t()}
                    onRequestClose={props.onRequestClose}
                />
                <Modal.Body style={opaStyle}>
                    {
                        retrieveMsg.msg && <DisplayRestoreMessage retrieveMsg={retrieveMsg} />
                    }
                    <ControlGroup
                        label={_('Name').t()}
                        controlsLayout="fill"
                        {...createTestHook(null, 'ArchiveNameControl')}
                    >
                        <StaticContent>{name}</StaticContent>
                    </ControlGroup>
                    <ControlGroup
                        label={_('Time Range').t()}
                        help={_(`${startTime} 00:00:00 AM to ${endTime} 00:00:00 AM.`).t()}
                        {...createTestHook(null, 'ArchiveTimerangeControl')}
                    >
                        <Date value={startTime} onChange={handleFromChange} disabled={disableContents} />
                        <P style={pStyle}>{_(' to ').t()}</P>
                        <Date value={endTime} onChange={handleToChange} disabled={disableContents} />
                    </ControlGroup>
                    <ControlGroup
                        label={_('Description').t()}
                        help={_('Describe this retrieve job. Limit to 60 characters.').t()}
                        {...createTestHook(null, 'ArchiveDescriptionControl')}
                    >
                        <Text
                            placeholder={_('None').t()}
                            disabled={disableContents}
                            onChange={props.onDescChange}
                        />
                    </ControlGroup>
                    <ControlGroup
                        label={_('Email').t()}
                        help={_('Comma-seperated list of email addresses to notify when' +
                         ' data restoration completes.').t()}
                        error={!props.validEmail}
                        tooltip={props.validEmail ? '' : _('One or more email addresses are invalid.').t()}
                        {...createTestHook(null, 'ArchiveEmailControl')}
                    >
                        <Text
                            disabled={disableContents}
                            onBlur={props.onEmailChange}
                        />
                    </ControlGroup>
                    <div style={{ textAlign: 'right', width: '600px', marginBottom: '20px' }}>
                        {
                            restoreSize !== null && restoreSize >= 0 &&
                                <StaticContent inline data-test-name="restore-size-wrapper">
                                    { sprintf(_('Total Restore Size: %sGB').t(), restoreSize) }
                                </StaticContent>
                        }
                        <Button
                            label={_('Check Size').t()} appearance="secondary"
                            onClick={props.onCheck}
                            disabled={disableContents}
                            {...createTestHook(null, 'ArchiveCheckSizeBtn')}
                        />
                        <Button
                            label={_('Restore').t()} appearance="primary"
                            onClick={props.onInitialRestore}
                            disabled={disableContents || blockRestore}
                            {...createTestHook(null, 'ArchiveRestoreBtn')}
                        />
                    </div>
                    <RestoreHistory
                        history={historyItems}
                        flushConfirm={flushConfirm}
                        disableContents={disableContents}
                        confirmButtonLabel={_('Clear').t()}
                        onConfirmToggle={props.onFlushConfirmClose}
                        onSort={props.onSort}
                        onFlushConfirm={props.onFlushConfirm}
                        processing={props.processing}
                    />
                </Modal.Body>
            </Modal>
            <Confirmation
                processing={props.processing}
                open={restoreConfirm}
                confirmMsg={restoreConfirmMsg}
                confirmButtonLabel={_('Restore').t()}
                onConfirmCancel={props.onRestoreConfirmClose}
                onConfirm={props.onRestoreRequest}
            />
        </div>
    );
};

RestoreDialog.propTypes = {
    name: PropTypes.string.isRequired,
    start_time: PropTypes.string.isRequired,
    end_time: PropTypes.string.isRequired,
    retrieveMsg: PropTypes.shape({
        type: PropTypes.string,
        msg: PropTypes.string,
    }),
    open: PropTypes.bool,
    validEmail: PropTypes.bool,
    restoreConfirm: PropTypes.bool,
    flushConfirm: PropTypes.bool,
    processing: PropTypes.bool,
    restoreSize: PropTypes.string,
    onRequestClose: PropTypes.func.isRequired,
    onDescChange: PropTypes.func.isRequired,
    onEmailChange: PropTypes.func.isRequired,
    onAttributeChange: PropTypes.func.isRequired,
    onCheck: PropTypes.func.isRequired,
    onInitialRestore: PropTypes.func.isRequired,
    onFlushConfirm: PropTypes.func.isRequired,
    onRestoreConfirmClose: PropTypes.func.isRequired,
    onFlushConfirmClose: PropTypes.func.isRequired,
    onRestoreRequest: PropTypes.func.isRequired,
    onSort: PropTypes.func.isRequired,
    historyItems: PropTypes.arrayOf(
        PropTypes.shape({
            StartTime: PropTypes.number,
            EndTime: PropTypes.number,
            RequestTime: PropTypes.number,
            Description: PropTypes.string,
            State: PropTypes.string,
            DataVolumeInGB: PropTypes.number,
        })),
};

RestoreDialog.defaultProps = {
    open: true,
    validEmail: true,
    retrieveMsg: {},
    restoreConfirm: false,
    flushConfirm: false,
    processing: false,
    restoreSize: null,
    historyItems: [],
};

export default RestoreDialog;