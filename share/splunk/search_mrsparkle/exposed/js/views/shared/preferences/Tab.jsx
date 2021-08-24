import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { omit } from 'lodash';
import Clickable from '@splunk/react-ui/Clickable';
import { createDOMID } from '@splunk/ui-utils/id';
import { createTestHook } from 'util/test_support';
import css from './Tab.pcssm';

class Tab extends Component {
    constructor(props, context) {
        super(props, context);
        this.handleClick = this.handleClick.bind(this);
        this.buttonId = createDOMID('button');
    }

    handleClick() {
        this.props.onClick(this.props.value);
    }

    render() {
        const {
            show,
            icon,
            label,
            ...otherProps
        } = this.props;

        const props = {
            onClick: this.handleClick,
            className: show ? css.buttonSelected : css.button,
            id: this.buttonId,
        };

        return (
            <div
                className={css.tab}
                {...createTestHook(module.id)}
                {...omit(otherProps, 'onClick', 'value')}
            >
                <Clickable {...props}>{icon}</Clickable>
                <label htmlFor={this.buttonId} className={css.label}>{label}</label>
            </div>
        );
    }
}

Tab.propTypes = {
    show: PropTypes.bool.isRequired,
    value: PropTypes.string.isRequired,
    icon: PropTypes.element.isRequired,
    label: PropTypes.string.isRequired,
    onClick: PropTypes.func.isRequired,
};

export default Tab;