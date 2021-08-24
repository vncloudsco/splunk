import React, { Component } from 'react';
import PropTypes from 'prop-types';
import _ from 'underscore';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Select from '@splunk/react-ui/Select';
import Switch from '@splunk/react-ui/Switch';
import P from '@splunk/react-ui/Paragraph';
import { createTestHook } from 'util/test_support';

const TIMEZONE = 'tz';
const DEFAULT_APP = 'defaultApp';
const RESTART_BACKGROUND_JOBS = 'restart_background_jobs';

class GlobalSettings extends Component {
    constructor(props) {
        super(props);
        this.state = {
            content: props.content,
        };

        this.handleChange = this.handleChange.bind(this);
    }

    componentDidMount() {
        this.firstElem.focus();
    }

    handleChange(attr, event, { value }) {
        this.props.onAttributeChange(attr, value);
        const updatedContent = Object.assign(
            {}, this.state.content, { [attr]: value });
        this.setState({ content: updatedContent });
    }

    render() {
        const timezonesOptions = this.props.timezones.map(timezone => (
            <Select.Option
                key={timezone.value}
                label={timezone.label}
                value={timezone.value}
            />
        ));

        let defaultAppControl = null;
        let appsOptions = null;
        if (this.props.showAppSelection && this.props.apps.length > 0) {
            appsOptions = this.props.apps.map(app => (
                <Select.Option
                    key={app.value}
                    label={app.label}
                    value={app.value}
                />
            ));
            defaultAppControl = (
                <ControlGroup
                    label={_('Default application').t()}
                    help={_('This setting overrides any default application.').t()}
                    {...createTestHook(null, 'default-app-control-group')}
                >
                    <Select
                        filter
                        data-label="default-app-control"
                        value={this.state.content[DEFAULT_APP]}
                        onChange={(e, data) =>
                            this.handleChange(DEFAULT_APP, e, data)}
                    >
                        {appsOptions}
                    </Select>
                </ControlGroup>);
        }

        /* eslint max-len: ["error", { "ignoreStrings": true }] */
        return (
            <div {...createTestHook(module.id)}>
                <P style={{ marginBottom: '20px' }}>
                    {_('Use these properties to set your timezone, default application, and default search time range picker. You can also specify if background jobs should restart when Splunk software restarts.').t()}
                </P>
                <ControlGroup
                    label={_('Time zone').t()}
                    help={_('Set a time zone for this user.').t()}
                    {...createTestHook(null, 'time-zone-control-group')}
                >
                    <Select
                        filter
                        ref={(select) => { this.firstElem = select; }}
                        value={this.state.content[TIMEZONE]}
                        onChange={(e, data) =>
                            this.handleChange(TIMEZONE, e, data)}
                    >
                        {timezonesOptions}
                    </Select>
                </ControlGroup>
                {defaultAppControl}
                <ControlGroup
                    label={_('Restart background jobs').t()}
                    help={_('Restart background jobs when the Splunk software is restarted.').t()}
                    {...createTestHook(null, 'restart-control-group')}
                >
                    <Switch
                        value={RESTART_BACKGROUND_JOBS}
                        onClick={(e, { selected }) => {
                            this.handleChange(RESTART_BACKGROUND_JOBS, e,
                                { value: !selected });
                        }}
                        selected={this.state.content[RESTART_BACKGROUND_JOBS]
                             || false}
                        appearance="toggle"
                        size="small"
                    />
                </ControlGroup>
            </div>
        );
    }
}

/* eslint-disable react/forbid-prop-types */
GlobalSettings.propTypes = {
    content: PropTypes.object.isRequired,
    timezones: PropTypes.arrayOf(PropTypes.object).isRequired,
    apps: PropTypes.arrayOf(PropTypes.object),
    showAppSelection: PropTypes.bool.isRequired,
    onAttributeChange: PropTypes.func.isRequired,
};

GlobalSettings.defaultProps = {
    apps: [],
};

export default GlobalSettings;
