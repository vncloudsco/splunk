import React, { Component } from 'react';
import PropTypes from 'prop-types';
import _ from 'underscore';
import moment from '@splunk/moment';
import Validation from 'util/validation';
import querystring from 'querystring';
import { sprintf } from '@splunk/ui-utils/format';
import { createRESTURL } from '@splunk/splunk-utils/url';
import { defaultFetchInit, handleResponse, handleError } from '@splunk/splunk-utils/fetch';
import * as DDAUtils from 'views/shared/indexes/cloud/DynamicDataArchiveUtils';
import RestoreDialog from './RestoreDialog';

class RestoreDialogContainer extends Component {
    constructor(props, context) {
        super(props, context);
        this.state = {
            open: true,
            start_time: moment().format('YYYY-MM-DD'),
            end_time: moment().format('YYYY-MM-DD'),
            desc: '',
            emailAddresses: '',
            validEmail: true,
            processing: false,
            restoreConfirm: false,
            flushConfirm: false,
            restoreSize: null,
            retrieveMsg: {},
        };
    }
    componentDidMount = () => {
        this.fetchHistory();
    }
    callIndexRestore = data =>
        fetch(createRESTURL('index_restore_sh'), {
            ...defaultFetchInit,
            method: 'POST',
            body: querystring.encode(data),
        })
        .then(handleResponse(200))
        .catch(handleError(_('Unable to process restore history.').t()));

    callRestoreHistory = data =>
        fetch(createRESTURL('restore_history_sh'), {
            ...defaultFetchInit,
            method: 'POST',
            body: querystring.encode(data),
        })
        .then(handleResponse(200))
        .catch(handleError(_('Unable to fetch restore history.').t()));

    fetchHistory = (sortKey = '', sortDir = '') => {
        this.callRestoreHistory(DDAUtils.constructHistoryData(this.props.name, sortKey, sortDir))
            .then((response) => {
                if (response.count > 0) {
                    this.setState({ historyItems: response.items });
                }
            }, error => this.handleMessage('error', error.message));
    }
    handleAttributeChange = (key, value) => {
        this.setState({
            [key]: value,
            retrieveMsg: {},
        });
    }
    handleDescChange = (e, { value }) => {
        // Limit description to 60 characters.
        this.setState({ desc: value.substring(0, 60) });
    }
    handleEmailChange = (e) => {
        if (e && e.target && e.target.value) {
            this.setState({
                emailAddresses: e.target.value,
                validEmail: Validation.isValidEmailList(e.target.value),
            });
        } else {
            this.setState({ validEmail: true });
        }
    }
    handleMessage = (type = 'info', msg, threshold = 0) => {
        this.setState({ retrieveMsg: { type, msg, threshold } });
    }
    handleRestoreConfirmClose = () => {
        this.setState({
            restoreConfirm: !this.state.restoreConfirm,
        });
    }
    handleFlushConfirmClose = () => {
        this.setState({
            flushConfirm: !this.state.flushConfirm,
        });
    }
    addAdditionalMessage = (response) => {
        let msg = response.message;
        if (response.status === 'Warning') {
            msg = sprintf(_('%s. Safe limit for restoration is below %sGB.').t(), msg,
                DDAUtils.convertToGB(response.warning_threshold));
            this.handleMessage(DDAUtils.getMsgType(response.status), msg,
                DDAUtils.convertToGB(response.warning_threshold));
        } else if (response.status === 'Blocked') {
            msg = sprintf(_('%s. Allowable restoration limit is below %sGB.').t(), msg,
                DDAUtils.convertToGB(response.blocked_threshold));
            this.handleMessage(DDAUtils.getMsgType(response.status), msg,
                DDAUtils.convertToGB(response.blocked_threshold));
        } else {
            this.handleMessage(DDAUtils.getMsgType(response.status), sprintf(_('%s.').t(), msg));
        }
    }
    handleFlush = (request) => {
        const data = {
            index_name: request.IndexName,
            action: 'flush',
            description: request.Description,
            email_addresses: request.EmailAddresses,
            start_time: request.StartTime,
            end_time: request.EndTime,
            output_mode: 'json',
        };
        this.setState({
            processing: true,
        });
        this.callIndexRestore(data)
            .then((response) => {
                this.setState({
                    flushConfirm: false,
                    processing: false,
                });
                this.fetchHistory();
                if (response.status === 'Success') {
                    this.handleMessage('success', _('Restored data will be cleared in several minutes.').t());
                } else {
                    this.handleMessage(DDAUtils.getMsgType(response.status), response.message);
                }
            }, (error) => {
                this.setState({
                    flushConfirm: false,
                    processing: false,
                });
                this.handleMessage('error', error.message);
            });
    }
    handleRequestClose = () => {
        this.setState({
            open: false,
        });
        this.props.onClose();
    }
    handleRestoreRequest = () => {
        const data = {
            index_name: this.props.name,
            action: 'restore',
            description: _.isEmpty(this.state.desc) ? 'None' : this.state.desc,
            email_addresses: _.isEmpty(this.state.emailAddresses) ? ' ' : this.state.emailAddresses,
            start_time: DDAUtils.convertDateToSeconds(this.state.start_time),
            end_time: DDAUtils.convertDateToSeconds(this.state.end_time),
            output_mode: 'json',
        };
        this.setState({
            processing: true,
        });
        this.callIndexRestore(data)
            .then((response) => {
                this.setState({
                    restoreConfirm: false,
                    processing: false,
                });
                this.handleMessage(DDAUtils.getMsgType(response.status), response.message);
                this.fetchHistory();
            }, (error) => {
                this.setState({
                    restoreConfirm: false,
                    processing: false,
                });
                this.handleMessage('error', error.message);
            });
    }
    handleCheck = () => {
        const data = {
            index_name: this.props.name,
            action: 'check',
            start_time: DDAUtils.convertDateToSeconds(this.state.start_time),
            description: _.isEmpty(this.state.desc) ? 'None' : this.state.desc,
            email_addresses: _.isEmpty(this.state.emailAddresses) ? ' ' : this.state.emailAddresses,
            end_time: DDAUtils.convertDateToSeconds(this.state.end_time),
            output_mode: 'json',
        };
        this.callIndexRestore(data)
            .then((response) => {
                this.addAdditionalMessage(response);
                this.setState({
                    // total_size is in pure bytes, covert that to GB for readability.
                    restoreSize: DDAUtils.convertToGB(response.total_size),
                });
            }, error => this.handleMessage('error', error.message));
    }
    handleInitialRestore = () => {
        const data = {
            index_name: this.props.name,
            action: 'check',
            start_time: DDAUtils.convertDateToSeconds(this.state.start_time),
            description: _.isEmpty(this.state.desc) ? 'None' : this.state.desc,
            email_addresses: _.isEmpty(this.state.emailAddresses) ? ' ' : this.state.emailAddresses,
            end_time: DDAUtils.convertDateToSeconds(this.state.end_time),
            output_mode: 'json',
        };
        this.callIndexRestore(data)
            .then((response) => {
                this.addAdditionalMessage(response);
                this.setState({
                    // total_size is in pure bytes, covert that to GB for readability.
                    restoreSize: DDAUtils.convertToGB(response.total_size),
                });
                if (DDAUtils.getMsgType(response.status) !== 'error') {
                    this.setState({ restoreConfirm: true });
                }
            }, error => this.handleMessage('error', error.message));
    }
    render() {
        const props = {
            open: this.state.open,
            start_time: this.state.start_time,
            end_time: this.state.end_time,
            name: this.props.name,
            retrieveMsg: this.state.retrieveMsg,
            validEmail: this.state.validEmail,
            onAttributeChange: this.handleAttributeChange,
            onCheck: this.handleCheck,
            onEmailChange: this.handleEmailChange,
            onInitialRestore: this.handleInitialRestore,
            onRequestClose: this.handleRequestClose,
            onRestoreRequest: this.handleRestoreRequest,
            onFlushConfirm: this.handleFlush,
            onRestoreConfirmClose: this.handleRestoreConfirmClose,
            onFlushConfirmClose: this.handleFlushConfirmClose,
            onDescChange: this.handleDescChange,
            onSort: this.fetchHistory,
            restoreConfirm: this.state.restoreConfirm,
            flushConfirm: this.state.flushConfirm,
            processing: this.state.processing,
            restoreSize: this.state.restoreSize,
            historyItems: this.state.historyItems,
        };
        return (
            <div>
                <RestoreDialog {...props} />
            </div>
        );
    }
}

RestoreDialogContainer.propTypes = {
    name: PropTypes.string.isRequired,
    onClose: PropTypes.func.isRequired,
};

export default RestoreDialogContainer;