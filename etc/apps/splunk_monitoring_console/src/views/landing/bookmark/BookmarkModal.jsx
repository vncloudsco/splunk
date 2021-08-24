import { _ } from '@splunk/ui-utils/i18n';
import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { isEmpty } from 'lodash';
import querystring from 'querystring';
import { createRESTURL } from '@splunk/splunk-utils/url';
import { defaultFetchInit } from '@splunk/splunk-utils/fetch';
import splunkUtil from 'splunk.util';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Modal from '@splunk/react-ui/Modal';
import Message from '@splunk/react-ui/Message';
import Text from '@splunk/react-ui/Text';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import * as Utils from 'splunk_monitoring_console/views/landing/bookmark/Utils';
import './BookmarkModal.pcss';

export const BOOKMARKS_ENDPOINT = 'saved/bookmarks/monitoring_console';
export const MC_APP = 'splunk_monitoring_console';
export const LABEL_WIDTH = 150;

class BookmarkModal extends Component {
    static propTypes = {
        bookmarks: PropTypes.shape({
            fetch: PropTypes.func,
            getBookmarks: PropTypes.func,
            models: PropTypes.arrayOf(PropTypes.shape({})),
            on: PropTypes.func,
        }).isRequired,
        handleClose: PropTypes.func.isRequired,
    };

    constructor(props, context) {
        super(props, context);
        this.state = {
            bookmarks: this.props.bookmarks.getBookmarks(),
            label: '',
            url: '',
            open: false,
            isWorking: false,
            changed: false,
            labelErrorMsg: '',
            labelError: false,
            urlErrorMsg: '',
            urlError: false,
            backendErrorMsg: '',
            backendError: false,
        };
    }

    /**
     * Handler for modal close action.
     */
    handleClose = () => {
        this.setState({
            open: false,
            isWorking: false,
            label: '',
            url: '',
            labelErrorMsg: '',
            labelError: false,
            urlErrorMsg: '',
            urlError: false,
            backendErrorMsg: '',
            backendError: false,
            bookmarks: this.props.bookmarks.getBookmarks(),
        });
        if (this.state.changed) {
            this.props.handleClose();
        }
    };

    /**
     * Handler for the modal open action.
     */
    handleOpen = () => {
        this.setState({
            open: true,
            changed: false,
        });
    };

    /**
     *
     */
     handleTextChange = (e, {name, value}) => {
        const newState = this.state;
        newState[name] = value;
        this.setState(newState);
     }

    /**
     * Validate the url and label.
     * Then either save or display errors to the user.
     */
    handleSubmit = () => {
        const labels = this.state.bookmarks.map(bookmark => {
            return bookmark.label;
        });
        const labelErrorMsg = Utils.validateLabel(this.state.label, labels, true);
        const urlErrorMsg = Utils.validateUrl(this.state.url);
        this.setState({
            labelErrorMsg: labelErrorMsg,
            labelError: !isEmpty(labelErrorMsg),
            urlErrorMsg: urlErrorMsg,
            urlError: !isEmpty(urlErrorMsg),
        });
        if (labelErrorMsg || urlErrorMsg) {
            return;
        }
        this.saveBookmark();
    }

    /**
     * Save the new bookmark.
     */
    saveBookmark = () => {
        this.setState({
            isWorking: true,
            changed: true,
        });

        const data = {
            name: this.state.label,
            url: this.state.url,
            output_mode: 'json',
        };

        fetch(createRESTURL(BOOKMARKS_ENDPOINT, {app: MC_APP}), {
            ...defaultFetchInit,
            method: 'POST',
            body: querystring.encode(data),
        })
        .then((response) => {
            this.props.bookmarks.fetch().done(() => {
                this.handleClose();
            });
        }) // TODO(claral): this silently fails when the user enters an existing name.
        .catch((response) => {
            let msg = _('Encountered errors while updating Bookmarks');
            if (response.responseJSON.messages && response.responseJSON.messages.length > 0) {
                const messageObj = response.responseJSON.messages[0];
                this.setState({
                    isWorking: false,
                    backendErrorMsg: splunkUtil.sprintf(_('%s: %s'), messageObj.type, messageObj.text),
                    backendError: true,
                })
            }
        });
    }

    /**
     * Render bookmark modal.
     */
    render() {
        return (
            <div
                data-test-name='bookmarks-button'
            >
                <Button
                    appearance='primary'
                    disabled={(this.state.bookmarks.length >= 6)}
                    label={_('Add Deployment')}
                    onClick={this.handleOpen}
                />
                <Modal
                    data-test-name='bookmark-modal'
                    onRequestClose={this.state.isWorking ? null : this.handleClose}
                    open={this.state.open}
                    className='bookmark-modal'
                >
                    <Modal.Header
                        title={_('Add Deployment')}
                        onRequestClose={this.state.isWorking ? null : this.handleClose}
                    />
                    <Modal.Body>
                        {this.state.backendError ?
                            <Message
                                fill
                                type='error'
                            >
                                {this.state.backendErrorMsg}
                            </Message> : null
                        }
                        <ControlGroup
                            labelWidth={LABEL_WIDTH}
                            label={_('Label')}
                            data-test='BookmarkLabel'
                            help={this.state.labelErrorMsg}
                            error={this.state.labelError}
                        >
                            <Text
                                disabled={this.state.isWorking}
                                error={this.state.labelError}
                                value={this.state.label}
                                name='label'
                                onChange={this.handleTextChange}
                                autoComplete={false}
                            />
                        </ControlGroup>

                        <ControlGroup
                            labelWidth={LABEL_WIDTH}
                            label={_('URL')}
                            data-test='BookmarkURL'
                            help={this.state.urlErrorMsg}
                            error={this.state.urlError}
                        >
                            <Text
                                disabled={this.state.isWorking}
                                error={this.state.urlError}
                                value={this.state.url}
                                name='url'
                                onChange={this.handleTextChange}
                                autoComplete={false}
                            />
                        </ControlGroup>
                    </Modal.Body>
                    { this.state.wait ?
                        <Modal.Footer>
                            <WaitSpinner size='medium' />
                        </Modal.Footer> :
                        <Modal.Footer>
                            <Button
                                appearance='secondary'
                                data-test-name='cancel-button'
                                onClick={this.handleClose}
                                disabled={this.state.isWorking}
                                label={_('Cancel')}
                            />
                            <Button
                                appearance='primary'
                                data-test-name='save-button'
                                onClick={this.handleSubmit}
                                disabled={this.state.isWorking}
                                label={_('Submit')}
                            />
                        </Modal.Footer>
                    }
                </Modal>
            </div>
        );
    }
}

export default BookmarkModal;
