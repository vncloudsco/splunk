import React, { Component } from 'react';
import PropTypes from 'prop-types';
import SearchableSwitch from './SearchableSwitch';

class SearchableSwitchContainer extends Component {
    constructor(props, context) {
        super(props, context);
        this.model = this.context.model;
        this.handleAttributeChange = this.handleAttributeChange.bind(this);
    }

    handleAttributeChange({ searchable, force }) {
        this.model.set('searchable', searchable);
        this.model.set('force', force);
    }

    render() {
        const content = this.model.toJSON();
        return (
            <SearchableSwitch
                content={content}
                onAttributeChange={this.handleAttributeChange}
            />
        );
    }
}

SearchableSwitchContainer.contextTypes = {
    model: PropTypes.object, // eslint-disable-line react/forbid-prop-types
};

export default SearchableSwitchContainer;