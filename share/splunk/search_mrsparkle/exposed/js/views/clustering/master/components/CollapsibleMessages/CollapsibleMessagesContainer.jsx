import React, { Component } from 'react';
import PropTypes from 'prop-types';
import CollapsibleMessages from './CollapsibleMessages';

class CollapsibleMessagesContainer extends Component {
    constructor(props, context) {
        super(props, context);
        this.model = this.context.model;
        this.state = {
            messages: '',
        };
    }

    componentDidMount() {
        this.model.entry.content.on('change:messages', this.handleModelChange, this);
    }

    handleModelChange = () => {
        const messages = this.model.entry.content.get('messages') || '';
        this.setState({
            messages,
        });
    };

    render() {
        return (
            <CollapsibleMessages
                messages={this.state.messages}
            />
        );
    }
}

CollapsibleMessagesContainer.contextTypes = {
    model: PropTypes.object, // eslint-disable-line react/forbid-prop-types
};

export default CollapsibleMessagesContainer;