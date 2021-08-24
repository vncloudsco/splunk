import _ from 'underscore';
import PropTypes from 'prop-types';
import React from 'react';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Text from '@splunk/react-ui/Text';
import FormMessage from 'dashboard/components/shared/FormMessage';
import { createTestHook } from 'util/test_support';

const propTypes = {
    activeTimeRangeToken: PropTypes.object.isRequired,
    onTimeRangeTokenChange: PropTypes.func.isRequired,
    earliestTokenError: PropTypes.string,
    latestTokenError: PropTypes.string,
};

const defaultProps = {
    earliestTokenError: '',
    latestTokenError: '',
};

class TimeRangeTokenEditor extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            earliest: props.activeTimeRangeToken.earliest,
            latest: props.activeTimeRangeToken.latest,
        };

        this.onTokenChange = this.onTokenChange.bind(this);
    }

    componentWillReceiveProps(nextProps) {
        if (nextProps.activeTimeRangeToken.earliest) {
            this.setState({
                earliest: nextProps.activeTimeRangeToken.earliest,
            });
        }
        if (nextProps.activeTimeRangeToken.latest) {
            this.setState({
                latest: nextProps.activeTimeRangeToken.latest,
            });
        }
    }

    onTokenChange(newToken) {
        const newState = Object.assign({}, this.state, newToken);
        this.props.onTimeRangeTokenChange(null, { value: newState });
        this.setState(newState);
    }

    render() {
        const earliestLabel = _('Earliest Token').t();
        const latestLabel = _('Latest Token').t();
        const { earliestTokenError, latestTokenError } = this.props;
        const hasEarliestError = !!earliestTokenError;
        const hasLatestError = !!latestTokenError;
        const earliestMessage = hasEarliestError ? `${earliestLabel} ${earliestTokenError}` : '';
        const latestMessage = hasLatestError ? `${latestLabel} ${latestTokenError}` : '';

        return (
            <div {..._.omit(this.props, _.keys(propTypes))} {...createTestHook(module.id)}>
                <FormMessage
                    active={hasEarliestError}
                    type="error"
                    message={earliestMessage}
                    {...createTestHook(null, 'earliestTimeTokenError')}
                />
                <ControlGroup
                    label={earliestLabel}
                    error={hasEarliestError}
                    {...createTestHook(null, 'earliestTimeToken')}
                >
                    <Text
                        value={this.state.earliest}
                        onChange={(e, { value }) => {
                            this.onTokenChange({ earliest: value });
                        }}
                        error={hasEarliestError}
                    />
                </ControlGroup>
                <FormMessage
                    active={hasLatestError}
                    type="error"
                    message={latestMessage}
                    {...createTestHook(null, 'latestTimeTokenError')}
                />
                <ControlGroup
                    label={latestLabel}
                    error={hasLatestError}
                    {...createTestHook(null, 'latestTimeToken')}
                >
                    <Text
                        value={this.state.latest}
                        onChange={(e, { value }) => {
                            this.onTokenChange({ latest: value });
                        }}
                        error={hasEarliestError}
                    />
                </ControlGroup>
            </div>
        );
    }
}

TimeRangeTokenEditor.propTypes = propTypes;
TimeRangeTokenEditor.defaultProps = defaultProps;

export default TimeRangeTokenEditor;
