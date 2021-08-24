import _ from 'underscore';
import $ from 'jquery';

export const abbrMap = {
    m: _('minute').t(),
    h: _('hour').t(),
    d: _('day').t(),
};

export const pluralAbbrMap = {
    m: _('minutes').t(),
    h: _('hours').t(),
    d: _('days').t(),
};

export const abbrValueMap = {
    m: 60,
    h: 60 * 60,
    d: 60 * 60 * 24,
};

export const getTimeErrorForSummary = ({ timeType, timeValue, minSpanAllowed }) => {
    if (
        !$.isNumeric(timeValue) ||
        !$.isNumeric(minSpanAllowed) ||
        !abbrValueMap[timeType] ||
        Number(timeValue) < 0 ||
        Number(minSpanAllowed) < 0 ||
        Number(timeValue) % 1 ||
        Number(minSpanAllowed) % 1
    ) {
        return true;
    }
    const summaryTotal = abbrValueMap[timeType] * Number(timeValue);
    return summaryTotal < Number(minSpanAllowed);
};

export const getAbbreviatedTime = (secondsTime) => {
    if (!$.isNumeric(secondsTime)) {
        return 'Invalid number';
    }
    const numValue = Number(secondsTime);
    if (numValue === 0) {
        return '0s';
    }
    if (numValue % abbrValueMap.d === 0) {
        return `${numValue / abbrValueMap.d}d`;
    }
    if (numValue % abbrValueMap.h === 0) {
        return `${numValue / abbrValueMap.h}h`;
    }
    if (numValue % abbrValueMap.m === 0) {
        return `${numValue / abbrValueMap.m}m`;
    }
    return `${numValue}s`;
};

export const getTimeInSeconds = ({ timeType, timeValue }) => abbrValueMap[timeType] * Number(timeValue);
