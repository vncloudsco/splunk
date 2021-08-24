import _ from 'underscore';
import PropTypes from 'prop-types';
import React from 'react';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import RadioBar from '@splunk/react-ui/RadioBar';
import OpenInNewTab from 'dashboard/components/shared/OpenInNewTab';
import SearchEditor from 'dashboard/components/shared/SearchEditor';
import Link from '@splunk/react-ui/Link';
import FormMessage from 'dashboard/components/shared/FormMessage';
import StaticContent from '@splunk/react-ui/StaticContent';
import { createTestHook } from 'util/test_support';
import SearchTimeEditor from './SearchTimeEditor';

const SearchActionEditor = ({
    options,
    activeOption,
    onOptionChange,
    search,
    searchError,
    onSearchChange,
    isFetchingPresets,
    presets,
    locale,
    parseEarliest,
    parseLatest,
    onRequestParseEarliest,
    onRequestParseLatest,
    extraTimeRangeOptions,
    activeTimeRangeOption,
    onTimeRangeOptionChange,
    activeTimeRange,
    onTimeRangeChange,
    activeTimeRangeToken,
    onTimeRangeTokenChange,
    earliestTokenError,
    latestTokenError,
    target,
    onTargetChange,
    learnMoreLinkForTokens,
    timeRangePickerDocsURL,
}) => {
    const radioBarOptions = options.map(option => (
        <RadioBar.Option
            key={option.value}
            label={option.label}
            value={option.value}
        />
    ));
    const hasError = !!searchError;
    const label = _('Search String').t();
    const errorMessage = hasError ? `${label} ${searchError}` : '';

    const searchActionDetail = activeOption === 'custom' ?
        (<div>
            <ControlGroup
                label=""
                controlsLayout="none"
                {...createTestHook(null, 'LearnMoreLink')}
            >
                <StaticContent inline>
                    {_('You can include predefined drilldown tokens in a custom search.').t()}
                    {' '}
                    <Link
                        to={learnMoreLinkForTokens}
                        openInNewContext
                    >{_('Learn more').t()}</Link>
                </StaticContent>
            </ControlGroup>
            <FormMessage active={hasError} type="error" message={errorMessage} />
            <ControlGroup
                label={label}
                error={hasError}
                {...createTestHook(null, 'SearchIdeWrapper')}
            >
                <SearchEditor
                    value={search}
                    onChange={onSearchChange}
                />
            </ControlGroup>
            <SearchTimeEditor
                isFetchingPresets={isFetchingPresets}
                presets={presets}
                locale={locale}
                parseEarliest={parseEarliest}
                parseLatest={parseLatest}
                onRequestParseEarliest={onRequestParseEarliest}
                onRequestParseLatest={onRequestParseLatest}
                extraOptions={extraTimeRangeOptions}
                activeOption={activeTimeRangeOption}
                onOptionChange={onTimeRangeOptionChange}
                activeTimeRange={activeTimeRange}
                onTimeRangeChange={onTimeRangeChange}
                activeTimeRangeToken={activeTimeRangeToken}
                onTimeRangeTokenChange={onTimeRangeTokenChange}
                earliestTokenError={earliestTokenError}
                latestTokenError={latestTokenError}
                timeRangePickerDocsURL={timeRangePickerDocsURL}
            />
            <OpenInNewTab
                value={target}
                onClick={onTargetChange}
            />
        </div>) :
        (<ControlGroup label="" {...createTestHook(null, 'DefaultSearchDescription')}>
            {_('A search generates automatically using values from the clicked element.').t()}
        </ControlGroup>);

    return (
        <div {...createTestHook(module.id)}>
            <ControlGroup label={''} {...createTestHook(null, 'LinkToSearchSelector')}>
                <RadioBar value={activeOption} onChange={onOptionChange}>
                    {radioBarOptions}
                </RadioBar>
            </ControlGroup>
            {searchActionDetail}
        </div>
    );
};

SearchActionEditor.propTypes = {
    options: PropTypes.arrayOf(PropTypes.object).isRequired,
    activeOption: PropTypes.string.isRequired,
    onOptionChange: PropTypes.func.isRequired,
    search: PropTypes.string.isRequired,
    searchError: PropTypes.string.isRequired,
    onSearchChange: PropTypes.func.isRequired,
    isFetchingPresets: PropTypes.bool.isRequired,
    presets: PropTypes.arrayOf(PropTypes.object).isRequired,
    locale: PropTypes.string.isRequired,
    parseEarliest: PropTypes.shape({
        error: PropTypes.string,
        iso: PropTypes.string,
        time: PropTypes.string,
    }),
    parseLatest: PropTypes.shape({
        error: PropTypes.string,
        iso: PropTypes.string,
        time: PropTypes.string,
    }),
    onRequestParseEarliest: PropTypes.func.isRequired,
    onRequestParseLatest: PropTypes.func.isRequired,
    extraTimeRangeOptions: PropTypes.arrayOf(PropTypes.object).isRequired,
    activeTimeRangeOption: PropTypes.string.isRequired,
    onTimeRangeOptionChange: PropTypes.func.isRequired,
    activeTimeRange: PropTypes.shape({
        earliest: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
        latest: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    }).isRequired,
    onTimeRangeChange: PropTypes.func.isRequired,
    activeTimeRangeToken: PropTypes.shape({
        earliest: PropTypes.string,
        latest: PropTypes.string,
    }).isRequired,
    onTimeRangeTokenChange: PropTypes.func.isRequired,
    earliestTokenError: PropTypes.string,
    latestTokenError: PropTypes.string,
    target: PropTypes.string.isRequired,
    onTargetChange: PropTypes.func.isRequired,
    learnMoreLinkForTokens: PropTypes.string.isRequired,
    timeRangePickerDocsURL: PropTypes.string,
};

SearchActionEditor.defaultProps = {
    activeTimeRangeToken: '',
    earliestTokenError: '',
    latestTokenError: '',
    parseEarliest: null,
    parseLatest: null,
    timeRangePickerDocsURL: null,
};

export default SearchActionEditor;
