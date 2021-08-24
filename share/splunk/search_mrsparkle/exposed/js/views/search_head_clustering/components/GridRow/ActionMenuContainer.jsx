import React, { Component } from 'react';
import PropTypes from 'prop-types';
import ActionMenu from './ActionMenu';

class ActionMenuContainer extends Component {
    constructor(props, context) {
        super(props, context);
        this.model = this.context.model;
    }

    render() {
        return (
            <ActionMenu
                model={this.model}
            />
        );
    }
}

ActionMenuContainer.contextTypes = {
    model: PropTypes.object, // eslint-disable-line react/forbid-prop-types
};

export default ActionMenuContainer;