import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { sprintf } from '@splunk/ui-utils/format';
import ScriptSecureArguments from './ScriptSecureArguments';

class ScriptSecureArgumentsContainer extends Component {
    constructor(props, context) {
        super(props, context);
        this.model = props.model;
        this.scrollContainer = props.scrollContainer;
    }

    handleScriptSecureArgumentsChange = (items) => {
        const scriptSecureArgs = [];
        items.forEach((item) => {
            if (item.hasChanged && !(item.isNew && !item.value)) {
                scriptSecureArgs.push(sprintf('%(key)s:%(value)s', { key: item.key, value: item.value }));
            }
        });
        this.model.saml.set('ui.scriptSecureArguments', scriptSecureArgs);
    }

    handleScriptFunctionChange = (values) => {
        this.model.saml.set('ui.scriptFunctions', values);
    }

    render() {
        return (
            <ScriptSecureArguments
                scriptSecureArguments={this.model.saml.get('ui.scriptSecureArguments') || {}}
                scriptFunctions={this.model.saml.get('ui.scriptFunctions') || []}
                disabled={this.model.saml.attributes.scriptDisabled}
                onScriptSecureArgumentsChange={this.handleScriptSecureArgumentsChange}
                onScriptFunctionChange={this.handleScriptFunctionChange}
                scrollContainer={this.scrollContainer}
            />
        );
    }
}

ScriptSecureArgumentsContainer.propTypes = {
    model: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    scrollContainer: PropTypes.element.isRequired,
};

export default ScriptSecureArgumentsContainer;
