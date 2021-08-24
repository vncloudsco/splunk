import React, { Component } from 'react';
import PropTypes from 'prop-types';
import _ from 'underscore';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Switch from '@splunk/react-ui/Switch';
import { createTestHook } from 'util/test_support';

class SearchableSwitch extends Component {
    constructor(props, context) {
        super(props, context);
        this.state = {
            searchable: _.has(props.content, 'searchable') ? props.content.searchable : false,
            force: _.has(props.content, 'force') ? props.content.force : false,
        };
    }

    handleClick = (e, { value }) => {
        const newState = _.extend({}, this.state, {
            [value]: !this.state[value],
        });
        // force flag should be true only when searchable is true
        newState.force = (newState.searchable === true) ? newState.force : false;
        this.setState(newState);
        this.props.onAttributeChange(newState);
    };

    render() {
        return (
            <div {...createTestHook(module.id)}>
                <ControlGroup
                    label={_('Searchable').t()}
                    help={_('Restart search head cluster members with minimal search interruption.').t()}
                    {...createTestHook(null, 'searchable-control-group')}
                >
                    <Switch
                        value="searchable"
                        data-label="searchable-switch"
                        onClick={this.handleClick}
                        selected={this.state.searchable}
                        appearance="toggle"
                    />
                </ControlGroup>
                {
                    this.state.searchable === true ?
                        <ControlGroup
                            label={_('Force').t()}
                            help={_('Restart search head cluster members despite unhealthy search head cluster.').t()}
                            {...createTestHook(null, 'force-control-group')}
                        >
                            <Switch
                                value="force"
                                data-label="force-switch"
                                onClick={this.handleClick}
                                selected={this.state.force}
                                appearance="checkbox"
                            />
                        </ControlGroup> : null
                }
            </div>
        );
    }
}

SearchableSwitch.propTypes = {
    content: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    onAttributeChange: PropTypes.func.isRequired,
};

export default SearchableSwitch;
