import _ from 'underscore';
import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { omit } from 'lodash';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import { createTestHook } from 'util/test_support';

class SimpleDialog extends Component {
    constructor(props, context) {
        super(props, context);
        this.state = {
            open: props.open,
        };
        this.close = this.close.bind(this);
        this.apply = this.apply.bind(this);
    }

    close() {
        this.setState({
            open: false,
        });
        this.props.onClose(this);
    }

    apply() {
        this.props.onApply(this);
    }

    render() {
        const defaultCancelLabel = _('Cancel').t();
        const defaultOkLabel = _('OK').t();
        const {
            title,
            width,
            children,
            cancelLabel,
            okLabel,
            disablePrimaryButton,
            ...otherProps
        } = this.props;
        return (
            <Modal
                onRequestClose={this.close}
                open={this.state.open}
                {...createTestHook(module.id)}
                {...omit(otherProps, 'onApply', 'onClose')}
            >
                <Modal.Header title={title} onRequestClose={this.close} />
                <Modal.Body style={{ width }}>
                    {children}
                </Modal.Body>
                <Modal.Footer>
                    <Button
                        appearance="secondary"
                        onClick={this.close}
                        label={cancelLabel || defaultCancelLabel}
                        {...createTestHook(null, 'cancel')}
                    />
                    {disablePrimaryButton ?
                        null :
                        <Button
                            appearance="primary"
                            onClick={this.apply}
                            label={okLabel || defaultOkLabel}
                            {...createTestHook(null, 'ok')}
                        />}
                </Modal.Footer>
            </Modal>
        );
    }
}

SimpleDialog.propTypes = {
    open: PropTypes.bool,
    title: PropTypes.string.isRequired,
    okLabel: PropTypes.string,
    cancelLabel: PropTypes.string,
    onClose: PropTypes.func.isRequired,
    onApply: PropTypes.func.isRequired,
    children: PropTypes.oneOfType([
        PropTypes.node,
        PropTypes.arrayOf(PropTypes.node),
    ]).isRequired,
    width: PropTypes.number,
    disablePrimaryButton: PropTypes.bool,
};

SimpleDialog.defaultProps = {
    open: true,
    okLabel: _('Save').t(),
    cancelLabel: _('Cancel').t(),
    width: 460,
    disablePrimaryButton: false,
};

export default SimpleDialog;
