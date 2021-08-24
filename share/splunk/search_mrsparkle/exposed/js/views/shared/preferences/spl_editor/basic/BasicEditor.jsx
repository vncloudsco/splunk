import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { findDOMNode } from 'react-dom';
import $ from 'jquery';
import _ from 'underscore';
import UserModel from 'models/services/authentication/User';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import RadioBar from '@splunk/react-ui/RadioBar';
import { createTestHook } from 'util/test_support';

const SEARCH_ASSISTANT = 'search_assistant';

class BasicEditor extends Component {
    constructor(props) {
        super(props);
        this.handleChange = this.handleChange.bind(this);
    }

    componentDidMount() {
        // The first item is a RadioBar, needs to focus on its first unselected button.
        const el = findDOMNode(this.firstElem);
        // Selected button has attribute tabindex=-1.
        // Find the first button without tabindex attribute.
        $(el).children(':not([tabindex])').first().focus();
    }

    handleChange(attr, event, { value }) {
        this.props.onAttributeChange(attr, value);
    }

    render() {
        let searchAssitant = this.props.content[SEARCH_ASSISTANT];
        // In basic search bar, we don't support compact, set the value to NONE, but don't update it in user model.
        if (searchAssitant === UserModel.SEARCH_ASSISTANT.COMPACT) {
            searchAssitant = UserModel.SEARCH_ASSISTANT.NONE;
        }
        return (
            <div {...createTestHook(module.id)} >
                <hr />
                <ControlGroup
                    label={_('Search assistant').t()}
                    help={_('Full search assistant is useful when first learning to create ' +
                        'searches.').t()}
                    {...createTestHook(null, 'search-assistant-control-group')}
                >
                    <RadioBar
                        ref={(radioBar) => { this.firstElem = radioBar; }}
                        value={searchAssitant}
                        onChange={(e, data) => this.handleChange(SEARCH_ASSISTANT, e, data)}
                    >
                        <RadioBar.Option
                            label={_('Full').t()}
                            value={UserModel.SEARCH_ASSISTANT.FULL}
                        />
                        <RadioBar.Option
                            label={_('None').t()}
                            value={UserModel.SEARCH_ASSISTANT.NONE}
                        />
                    </RadioBar>
                </ControlGroup>
            </div>
        );
    }
}

BasicEditor.propTypes = {
    content: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    onAttributeChange: PropTypes.func.isRequired,
};

export default BasicEditor;