import $ from 'jquery';
import { ALL_AGGREGATIONS } from './Aggregations';
import { getTimeInSeconds, pluralAbbrMap, abbrMap, abbrValueMap } from './TimeConfigUtils';

export const IGNORED_DIMENSIONS = [
    'rollup_span',
    'rollup_aggregate',
    'rollup_source_index',
    'extracted_host',
    'extracted_source',
    'extracted_sourcetype',
];

export const summaryValuesMap = {
    m: [1, 2, 3, 4, 5, 6, 10, 12, 20, 30, 60],
    h: [1, 2, 3, 4, 6, 8, 12, 24],
    d: [1],
};

export const summaryValueForTypeExists = (type, value) => {
    if (!summaryValuesMap[type] || !$.isNumeric(value)) {
        return false;
    }
    return summaryValuesMap[type].indexOf(Number(value)) >= 0;
};

export const getDuplicateSummaryError = (summaries) => {
    for (let i = 0; i < summaries.length; i += 1) {
        const testSummary = summaries[i];
        const testIndex = testSummary.targetIndex;
        if (testIndex === undefined) {
            // eslint-disable-next-line no-continue
            continue;
        }
        const testTimeInSeconds = getTimeInSeconds(testSummary);
        for (let j = i + 1; j < summaries.length; j += 1) {
            const currSummary = summaries[j];
            const currIndex = currSummary.targetIndex;
            const currTimeInSeconds = getTimeInSeconds(currSummary);
            if (testIndex === currIndex && testTimeInSeconds === currTimeInSeconds) {
                return true;
            }
        }
    }
    return false;
};

// eslint-disable-next-line no-confusing-arrow
const getTimeStrByAbbreviation = (abbr, plural) => plural ? pluralAbbrMap[abbr] : abbrMap[abbr];

const summarySortAscending = (summaries) => {
    const summariesCopy = $.extend(true, [], summaries);
    return summariesCopy.sort((a, b) => {
        if (!abbrValueMap[a.timeType]) {
            throw new Error(`Unknown rollup time value: ${a.timeType}`);
        }
        if (!abbrValueMap[b.timeType]) {
            throw new Error(`Unknown rollup time value: ${b.timeType}`);
        }
        const aTotal = abbrValueMap[a.timeType] * Number(a.timeValue);
        const bTotal = abbrValueMap[b.timeType] * Number(b.timeValue);
        return aTotal <= bTotal ? -1 : 1;
    });
};

export const getTimes = (summaries) => {
    if (!summaries) {
        return [];
    }
    const sortedSummaries = summarySortAscending(summaries);
    return sortedSummaries.map((summary) => {
        const timeStr = getTimeStrByAbbreviation(summary.timeType, summary.timeValue > 1);
        return `${summary.timeValue} ${timeStr}`;
    });
};

const getAggregationProps = (aggregation) => {
    const aggregationRegex = new RegExp('[^0-9]+');
    const valueRegex = new RegExp('[0-9]+');
    const hasValue = valueRegex.test(aggregation);
    return hasValue
        ? [aggregation.match(aggregationRegex)[0], aggregation.match(valueRegex)[0]]
        : [aggregation];
};

const getExceptionTabsFromRollupPolicy = (rollupPolicy) => {
    const tabs = [];
    Object.keys(rollupPolicy).forEach((key) => {
        if (key.indexOf('aggregation.') >= 0) {
            const metricName = key.split('aggregation.')[1];
            const aggregationProps = getAggregationProps(rollupPolicy[key]);
            const aggregationValue = aggregationProps.length > 1
                ? Number(aggregationProps[1])
                : undefined;
            tabs.push({
                exceptionMetric: metricName,
                aggregation: aggregationProps[0],
                label: `${metricName} Exception Rule`,
                tabBarLabel: metricName,
                aggregationItems: ALL_AGGREGATIONS,
                aggregationValue,
                validMetric: true,
                validAgg: true,
                validAggValue: true,
            });
        }
    });
    return tabs;
};

const summariesAttrFromRollupPolicy = (rollupPolicy) => {
    const summaries = rollupPolicy.summaries;
    if (!summaries) {
        return [];
    }
    return summaries.map((summary, i) => {
        const span = summary.span;
        return {
            id: i + 1,
            targetIndex: summary.rollupIndex,
            timeType: span.slice(-1),
            timeValue: span.slice(0, -1),
        };
    });
};

const convertSummariesObjectToArray = summaries => Object.keys(summaries).map(key => summaries[key]);

export const getUIPropsFromRollupPolicy = (rollupPolicy) => {
    const uiProps = {
        hasViewCapability: rollupPolicy.hasViewCapability,
        hasEditCapability: rollupPolicy.hasEditCapability,
        minSpanAllowed: rollupPolicy.minSpanAllowed,
        disabled: rollupPolicy.disabled,
    };
    if (rollupPolicy.summaries) {
        // eslint-disable-next-line no-param-reassign
        rollupPolicy.summaries = convertSummariesObjectToArray(rollupPolicy.summaries);
    }
    const generalPolicyTab = { tabBarLabel: 'General Policy' };
    if (rollupPolicy.summaries && rollupPolicy.summaries.length) {
        const summaries = summariesAttrFromRollupPolicy(rollupPolicy);
        generalPolicyTab.summaries = summaries;
        uiProps.rollupTimes = getTimes(summaries);
    } else {
        generalPolicyTab.summaries = [];
        uiProps.rollupTimes = [];
    }
    generalPolicyTab.aggregation = rollupPolicy.defaultAggregation || 'avg';
    generalPolicyTab.listType = rollupPolicy.dimensionListType || 'excluded';
    generalPolicyTab.selectedItems = rollupPolicy.dimensionList
        ? rollupPolicy.dimensionList.split(',')
        : [];

    const exceptionTabs = getExceptionTabsFromRollupPolicy(rollupPolicy);
    uiProps.tabs = [generalPolicyTab].concat(exceptionTabs);
    return uiProps;
};
