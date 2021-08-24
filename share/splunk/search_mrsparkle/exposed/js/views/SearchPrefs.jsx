// import assignIn from 'lodash/assignIn';
import { _ } from '@splunk/ui-utils/i18n';
import React, { Component } from 'react';
import PropTypes from 'prop-types';
import querystring from 'querystring';
import { sprintf } from '@splunk/ui-utils/format';
import { defaultFetchInit, handleResponse, handleError } from '@splunk/splunk-utils/fetch';
import { createRESTURL } from '@splunk/splunk-utils/url';
import TimeRangeDropdown from '@splunk/react-time-range/Dropdown';
import SplunkwebConnector from '@splunk/react-time-range/SplunkwebConnector';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Heading from '@splunk/react-ui/Heading';
import Link from '@splunk/react-ui/Link';
import Message from '@splunk/react-ui/Message';
import Number from '@splunk/react-ui/Number';
import P from '@splunk/react-ui/Paragraph';
import route from 'uri/route';

class SearchPrefs extends Component {
    static propTypes = {
        userPrefs: PropTypes.shape({
            entry: PropTypes.shape({
                content: PropTypes.shape({
                    attributes: PropTypes.shape({
                        default_earliest_time: PropTypes.string.isRequired,
                        default_latest_time: PropTypes.string.isRequired,
                    }),
                }),
            }),
        }).isRequired,
        application: PropTypes.shape({
            get: PropTypes.func.isRequired,
        }).isRequired,
        concurrencySettings: PropTypes.shape({
            getMaxSearchesPerc: PropTypes.func.isRequired,
            getAutoSummaryPerc: PropTypes.func.isRequired,
        }).isRequired,
        searchConcurrency: PropTypes.shape({
            getMaxHistScheduledSearches: PropTypes.func.isRequired,
            getMaxAutoSummarySearches: PropTypes.func.isRequired,
        }).isRequired,
    };

    static defaultProps = {
    };

    constructor(props, context) {
        super(props, context);
        this.state = {
            earliest: props.userPrefs.entry.content.attributes.default_earliest_time,
            latest: props.userPrefs.entry.content.attributes.default_latest_time,
            parseEarliest: undefined,
            parseLatest: undefined,
            timeRangeChanged: false,
            isWorkingTimeRange: false,
            errorMessageTimeRange: this.getErrorMessageTimeRange(),
            maxSearchesPerc: props.concurrencySettings.getMaxSearchesPerc(),
            autoSummaryPerc: props.concurrencySettings.getAutoSummaryPerc(),
            concurrencyChanged: false,
            isWorkingConcurrency: false,
            errorMessageConcurrencySettings: this.getErrorMessageConcurrencySettings(),
            maxHistScheduledSearches: props.searchConcurrency.getMaxHistScheduledSearches(),
            maxAutoSummarySearches: props.searchConcurrency.getMaxAutoSummarySearches(),
            errorMessageSearchConcurrency: this.getErrorMessageSearchConcurrency(),
        };
    }

    /**
     * Returns an error message, if one is necessary, for default time range.
     */
    getErrorMessageTimeRange() {
        if (this.props.userPrefs.entry.content.attributes.default_earliest_time &&
            this.props.userPrefs.entry.content.attributes.default_latest_time) {
            return '';
        }
        return _('Trouble fetching default search time range.');
    }

    /**
     * Returns an error message, if one is necessary, for Search Concurrency settings.
     */
    getErrorMessageConcurrencySettings() {
        if (this.props.concurrencySettings.getMaxSearchesPerc() === 'unknown' ||
            this.props.concurrencySettings.getAutoSummaryPerc() === 'unknown') {
            return _('Trouble fetching relative search concurrency limits.');
        }
        return '';
    }

    /**
     * Returns an error message, if one is necessary, for Effective Search Concurrency.
     */
    getErrorMessageSearchConcurrency() {
        if (this.props.searchConcurrency.getMaxHistScheduledSearches() === 'unknown' ||
            this.props.searchConcurrency.getMaxAutoSummarySearches() === 'unknown') {
            return _('Trouble fetching effective search concurrency values.');
        }
        return '';
    }

    /**
     * Returns the correct label for working or not working state.
     * @param {Boolean} value
     */
    getButtonLabel = (isWorking) => {
        if (isWorking) {
            return _('Saving...');
        }
        return _('Save');
    };

    /**
     * Validates the value, and sets it to minVal if it's not a number.
     * @param {Number} value
     * @param {Number} minVal
     */
    validateValue = (value, minVal) => {
        let val = value;
        if (typeof val === 'undefined' || val === null || val === '' || val < minVal) {
            val = minVal;
        }
        return val;
    }

    /**
     * Handles default search time range change
     * @param {Event} e
     * @param {String} earliest
     * @param {String} latest
     */
    handleTimeRangeChange = (e, { earliest, latest }) => {
        this.setState({
            earliest: earliest,  // eslint-disable-line object-shorthand
            latest: latest,  // eslint-disable-line object-shorthand
            timeRangeChanged: true,
        });
    };

    /**
     * Handles relative concurrency limit for scheduled searches change
     * @param {Event} e
     * @param {String} value
     */
    handleRelativeConcurrencyScheduledChange = (e, { value }) => {
        const val = this.validateValue(value, 1);
        this.setState({
            maxSearchesPerc: val,
            concurrencyChanged: true,
        });
    };

    /**
     * Handles relative concurrency limit for summarization searches change
     * @param {Event} e
     * @param {String} value
     */
    handleRelativeConcurrencySummarizationChange = (e, { value }) => {
        const val = this.validateValue(value, 0);
        this.setState({
            autoSummaryPerc: val,
            concurrencyChanged: true,
        });
    };

    /**
     * Post to the provided URL with the given data.
     * @param {String} url
     * @param {object} data
     * @param {String} defaultError
     */
    fetchPost = (url, data, defaultError) => (
        fetch(createRESTURL(url), {
            ...defaultFetchInit,
            method: 'POST',
            body: querystring.encode(data),
        })
        .then(handleResponse(200))
        .catch(handleError(defaultError))
    );

    /**
     * Get from the provided URL with the given data.
     * @param {String} url
     * @param {object} data
     * @param {String} defaultError
     */
    fetchGet = (url, data, defaultError) => (
        fetch(createRESTURL(`${url}${querystring.encode(data)}`), {
            ...defaultFetchInit,
            method: 'GET',
        })
        .then(handleResponse(200))
        .catch(handleError(defaultError))
    );

    /**
     * Save the default search time range.
     */
    saveTimeRange = () => {
        const data = {
            default_earliest_time: this.state.earliest,
            default_latest_time: this.state.latest,
            output_mode: 'json',
        };
        const defaultError = _('Unable to save default search time range.');
        this.fetchPost('data/user-prefs/general', data, defaultError)
        .then(() => {
            this.setState({
                isWorkingTimeRange: false,
                errorMessageTimeRange: '',
                timeRangeChanged: false,
            });
        })
        .catch((res) => {
            this.setState({
                isWorkingTimeRange: false,
                errorMessageTimeRange: sprintf('%s %s', defaultError, res.message),
                timeRangeChanged: false,
            });
        });
    };

    /**
     * Fetch the effective concurrency limits.
     */
    fetchEffectiveSearchConcurrency = () => {
        const data = { output_mode: 'json' };
        const defaultError = _('Unable to fetch effective search concurrency.');
        this.fetchGet('server/status/limits/search-concurrency?', data, defaultError)
        .then((response) => {
            this.setState({
                isWorkingConcurrency: false,
                errorMessageConcurrencySettings: '',
                errorMessageSearchConcurrency: '',
                concurrencyChanged: false,
                maxHistScheduledSearches: response.entry[0].content.max_hist_scheduled_searches,
                maxAutoSummarySearches: response.entry[0].content.max_auto_summary_searches,
            });
        })
        .catch((res) => {
            this.setState({
                isWorkingConcurrency: false,
                errorMessageConcurrencySettings: '',
                errorMessageSearchConcurrency: sprintf('%s %s', defaultError, res.message),
                concurrencyChanged: false,
            });
        });
    };

    /**
     * Save the relative concurrency limits for scheduled and/or summarization searches.
     */
    saveRelativeConcurrency = () => {
        const data = {
            max_searches_perc: this.state.maxSearchesPerc,
            auto_summary_perc: this.state.autoSummaryPerc,
            output_mode: 'json',
        };
        const defaultError = _('Unable to save search concurrency changes.');

        this.fetchPost('search/concurrency-settings/scheduler', data, defaultError)
        .then(() => {
            // on good response update the search concurrency calculated data.
            // Only if this fetch goes through should the state be updated.
            this.fetchEffectiveSearchConcurrency();
        })
        .catch((res) => {
            this.setState({
                isWorkingConcurrency: false,
                errorMessageConcurrencySettings: sprintf('%s %s', defaultError, res.message),
                errorMessageSearchConcurrency: '',
                concurrencyChanged: false,
            });
        });
    };

    /**
     * Save the default search time range and/or the relative concurrency limits.
     */
    handleSave = () => {
        this.setState({
            isWorkingTimeRange: this.state.timeRangeChanged,
            isWorkingConcurrency: this.state.concurrencyChanged,
        });
        if (this.state.timeRangeChanged) {
            this.saveTimeRange();
        }
        if (this.state.concurrencyChanged) {
            this.saveRelativeConcurrency();
        }
    };

    /**
     * Create a documentation link.
     * @param {String} location - doc string to link to.
     */
    makeDocLink(location) {
        return route.docHelp(
            this.props.application.get('root'),
            this.props.application.get('locale'),
            location,
        );
    }

    /**
     * Render SearchPreferences.
     */
    render() {
        const serverSettingsLink = route.manager(
            this.props.application.get('root'),
            this.props.application.get('locale'),
            'system',
            'systemsettings',
        );

        const timeRangeHelpText = (
            <span>
                {_('This time range is used as the default time range for searches. ')}
                <Link
                    to={this.makeDocLink('learnmore.search.time_range_picker.global.default')}
                    openInNewContext
                >
                    {_('Learn More')}
                </Link>
            </span>
        );
        const relativeConcurrencyScheduledHelpText = (
            <span>
                {_(`The maximum number of searches the scheduler can run, as a percentage of the
                    maximum number of concurrent searches. Default value is 50%. `)}
                <Link
                    to={this.makeDocLink('learnmore.relative.concurrency.scheduled.searches')}
                    openInNewContext
                >
                    {_('Learn More')}
                </Link>
            </span>
        );
        const relativeConcurrencySummarizationHelpText = (
            <span>
                {_(`The maximum number of concurrent searches to be allocated for auto summarization,
                    as a percentage of the concurrent searches that the scheduler can run.
                    Auto summary searches include: searches which generate the data for the Report 
                    Acceleration feature or for Data Model acceleration. Note: user scheduled searches
                    take precedence over auto summary searches. Default value is 50%. `)}
                <Link
                    to={this.makeDocLink('learnmore.relative.concurrency.summarization.searches')}
                    openInNewContext
                >
                    {_('Learn More')}
                </Link>
            </span>
        );
        return (
            <div
                data-test-name="searchprefs"
                style={{
                    paddingLeft: '20px',
                    paddingRight: '20px',
                }}
            >
                <Heading
                    level={1}
                    data-test-name="searchprefs-heading"
                >
                    {_('Search preferences')}
                </Heading>
                <P data-test-name="breadcrumb">
                    <Link
                        to={serverSettingsLink}
                        data-test-name="breadcrumb-link"
                    >
                        {_('Server settings')}
                    </Link>
                    {_(' » Search preferences')}
                </P>
                <div
                    data-test-name="searchprefs-content"
                    style={{
                        background: 'white',
                        width: '960px',
                        margin: '20px auto',
                        padding: '20px',
                    }}
                >
                    {this.state.errorMessageTimeRange && (
                        <Message
                            type="error"
                            data-test-name="time-range-error"
                        >
                            {this.state.errorMessageTimeRange}
                        </Message>
                    )}
                    {this.state.errorMessageConcurrencySettings && (
                        <Message
                            type="error"
                            data-test-name="concurrency-settings-error"
                        >
                            {this.state.errorMessageConcurrencySettings}
                        </Message>
                    )}
                    {this.state.errorMessageSearchConcurrency && (
                        <Message
                            type="error"
                            data-test-name="search-concurrency-error"
                        >
                            {this.state.errorMessageSearchConcurrency}
                        </Message>
                    )}
                    <ControlGroup
                        label={_('Default search time range')}
                        labelPosition="top"
                        help={timeRangeHelpText}
                        controlsLayout="none"
                        data-test-name="searchprefs-time-range-picker"
                    >
                        <SplunkwebConnector>
                            <TimeRangeDropdown
                                onChange={this.handleTimeRangeChange}
                                earliest={this.state.earliest}
                                latest={this.state.latest}
                                labelMaxChars={Infinity}
                                documentationURL={this.makeDocLink('learnmore.search.time_range_picker.global.default')}
                            />
                        </SplunkwebConnector>
                    </ControlGroup>
                    <hr />
                    <ControlGroup
                        label={_('Relative concurrency limit for scheduled searches')}
                        labelPosition="top"
                        help={relativeConcurrencyScheduledHelpText}
                        controlsLayout="none"
                        data-test-name="relative-concurrency-scheduled-searches"
                    >
                        <Number
                            value={this.state.maxSearchesPerc}
                            max={100}
                            min={1}
                            roundTo={0}
                            step={1}
                            onChange={this.handleRelativeConcurrencyScheduledChange}
                            inline
                        />
                    </ControlGroup>
                    <P data-test-name="effective-scheduled-searches">
                        {sprintf(_('This results in an effective concurrency limit for scheduled searches of %s.'),
                            this.state.maxHistScheduledSearches)}
                    </P>
                    <ControlGroup
                        label={_('Relative concurrency limit for summarization searches')}
                        labelPosition="top"
                        help={relativeConcurrencySummarizationHelpText}
                        controlsLayout="none"
                        data-test-name="relative-concurrency-summarization-searches"
                    >
                        <Number
                            value={this.state.autoSummaryPerc}
                            max={100}
                            min={0}
                            roundTo={0}
                            step={1}
                            onChange={this.handleRelativeConcurrencySummarizationChange}
                            inline
                        />
                    </ControlGroup>
                    <P data-test-name="effective-summary-searches">
                        {sprintf(_('This results in an effective concurrency limit for summarization searches of %s.'),
                            this.state.maxAutoSummarySearches)}
                    </P>
                    <hr /> <P
                        data-test-name="searchprefs-non-warning"
                        style={{
                            textAlign: 'left',
                        }}
                    >
                        {_(`Saving changes to the default time range or concurrency
                            limits does not trigger a restart.`)}
                    </P>
                    <div
                        data-test-name="searchprefs-buttons"
                        style={{
                            textAlign: 'right',
                        }}
                    >
                        <Button
                            appearance="primary"
                            data-test-name="save-btn"
                            disabled={this.state.isWorkingTimeRange || this.state.isWorkingConcurrency}
                            label={this.getButtonLabel(this.state.isWorkingTimeRange ||
                                                       this.state.isWorkingConcurrency)}
                            onClick={this.handleSave}
                        />
                    </div>
                </div>
            </div>
        );
    }
}

export default SearchPrefs;
