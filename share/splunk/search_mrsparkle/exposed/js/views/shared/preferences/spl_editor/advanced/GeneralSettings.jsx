import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { findDOMNode } from 'react-dom';
import $ from 'jquery';
import _ from 'underscore';
import UserModel from 'models/services/authentication/User';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import RadioBar from '@splunk/react-ui/RadioBar';
import Switch from '@splunk/react-ui/Switch';
import { createTestHook } from 'util/test_support';

const SEARCH_ASSISTANT = 'search_assistant';
const LINE_NUMBERS = 'search_line_numbers';
const AUTO_FORMAT = 'search_auto_format';

class GeneralSettings extends Component {
    constructor(props) {
        super(props);
        this.handleChange = this.handleChange.bind(this);
    }

    componentDidMount() {
        // The first item is a RadioBar, needs to focus on its first unselected button.
        const el = findDOMNode(this.firstElem);
        // Selected button has attribute tabindex=-1.
        // Find the first button without tabindex attribute.
        $(el)
            .children(':not([tabindex])')
            .first()
            .focus();
    }

    handleChange(attr, event, { value }) {
        this.props.onAttributeChange(attr, value);
    }

    render() {
        return (
            <div {...createTestHook(module.id)}>
                <ControlGroup
                    label={_('Search assistant').t()}
                    labelWidth={124}
                    help={_(
                        'Full search assistant is useful when first learning to create ' +
                            'searches. Compact provides more succinct assistance.',
                    ).t()}
                    {...createTestHook(null, 'search-assistant-control-group')}
                >
                    <RadioBar
                        ref={(radioBar) => {
                            this.firstElem = radioBar;
                        }}
                        value={this.props.content[SEARCH_ASSISTANT]}
                        onChange={(e, data) => this.handleChange(SEARCH_ASSISTANT, e, data)}
                    >
                        <RadioBar.Option label={_('Full').t()} value={UserModel.SEARCH_ASSISTANT.FULL} />
                        <RadioBar.Option label={_('Compact').t()} value={UserModel.SEARCH_ASSISTANT.COMPACT} />
                        <RadioBar.Option label={_('None').t()} value={UserModel.SEARCH_ASSISTANT.NONE} />
                    </RadioBar>
                </ControlGroup>
                <ControlGroup
                    label={_('Line numbers').t()}
                    labelWidth={124}
                    help={_('Shows numbers next to each line in the search syntax.').t()}
                    {...createTestHook(null, 'line-numbers-control-group')}
                >
                    <Switch
                        value={LINE_NUMBERS}
                        onClick={(e, { selected }) => {
                            this.handleChange(LINE_NUMBERS, e, { value: !selected });
                        }}
                        selected={this.props.content[LINE_NUMBERS]}
                        appearance="toggle"
                        size="small"
                    />
                </ControlGroup>
                <ControlGroup
                    label={_('Search auto-format').t()}
                    labelWidth={124}
                    help={_('Automatically format search syntax to improve readability.').t()}
                    {...createTestHook(null, 'auto-format-control-group')}
                >
                    <Switch
                        value={AUTO_FORMAT}
                        onClick={(e, { selected }) => {
                            this.handleChange(AUTO_FORMAT, e, { value: !selected });
                        }}
                        selected={this.props.content[AUTO_FORMAT]}
                        appearance="toggle"
                        size="small"
                    />
                </ControlGroup>
            </div>
        );
    }
}

GeneralSettings.propTypes = {
    content: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    onAttributeChange: PropTypes.func.isRequired,
};

export default GeneralSettings;
