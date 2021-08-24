import _ from 'underscore';

export const ALL_AGGREGATIONS = [
    {
        value: 'avg',
        label: _('Avg').t(),
    }, {
        value: 'count',
        label: _('Count').t(),
    }, {
        value: 'max',
        label: _('Max').t(),
    }, {
        value: 'median',
        label: _('Median').t(),
    }, {
        value: 'min',
        label: _('Min').t(),
    }, {
        value: 'perc',
        label: _('Percentile').t(),
    }, {
        value: 'sum',
        label: _('Sum').t(),
    },
];

export const aggregationLabelMap = {
    avg: 'Average',
    count: 'Count',
    max: 'Max',
    median: 'Median',
    min: 'Min',
    perc: 'Percentile',
    sum: 'Sum',
};
