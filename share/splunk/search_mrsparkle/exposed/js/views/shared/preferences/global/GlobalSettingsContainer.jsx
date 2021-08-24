import React, { Component } from 'react';
import PropTypes from 'prop-types';
import TimeZonesCollection from 'collections/shared/TimeZones';
import GlobalSettings from './GlobalSettings';

class GlobalSettingsContainer extends Component {
    constructor(props, context) {
        super(props, context);
        this.model = this.context.model;
        this.collection = this.context.collection;
        this.timeZonesCollection = new TimeZonesCollection();
        this.handleAttributeChange = this.handleAttributeChange.bind(this);
    }

    handleAttributeChange(attr, value) {
        this.model.inmem.entry.content.set(attr, value);
    }

    render() {
        const content = this.model.inmem.entry.content.toJSON();
        let apps = [];
        if (this.collection.appsVisible) {
            apps = this.collection.appsVisible.map(model => (
                {
                    label: model.entry.content.get('label'),
                    value: model.entry.get('name'),
                }
            ));
        }
        const timezones = this.timeZonesCollection.map(model => (
            {
                label: model.get('label'),
                value: model.get('id'),
            }
        ));

        return (
            <GlobalSettings
                content={content}
                apps={apps}
                showAppSelection={this.props.showAppSelection}
                timezones={timezones}
                onAttributeChange={this.handleAttributeChange}
            />
        );
    }
}

GlobalSettingsContainer.propTypes = {
    showAppSelection: PropTypes.bool.isRequired,
};

GlobalSettingsContainer.contextTypes = {
    model: PropTypes.object, // eslint-disable-line react/forbid-prop-types
    collection: PropTypes.object, // eslint-disable-line react/forbid-prop-types
};

export default GlobalSettingsContainer;
