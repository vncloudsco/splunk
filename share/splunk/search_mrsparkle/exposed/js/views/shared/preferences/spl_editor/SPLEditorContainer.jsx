import React, { Component } from 'react';
import PropTypes from 'prop-types';
import SPLEditor from './SPLEditor';

class SPLEditorContainer extends Component {
    constructor(props, context) {
        super(props, context);
        this.model = this.context.model;
        this.handleAttributeChange = this.handleAttributeChange.bind(this);
        this.state = {
            content: this.model.inmem.entry.content.toJSON(),
        };
    }

    handleAttributeChange(attr, value) {
        this.model.inmem.entry.content.set(attr, value);
        const content = this.model.inmem.entry.content.toJSON();
        this.setState({ content });
    }

    render() {
        return (
            <SPLEditor content={this.state.content} onAttributeChange={this.handleAttributeChange} />
        );
    }
}

SPLEditorContainer.contextTypes = {
    model: PropTypes.object, // eslint-disable-line react/forbid-prop-types
};

export default SPLEditorContainer;