/**
 * TODO: refactor this logic once SPL-133925 is delivered. There should be a flag that explicitly
 * indicates whether drilldown is supported or not.
 * @param {object} content is something like this.model.report.entry.content.toJSON()
 * @returns {boolean}
 */
export const isDrilldownSupported = (content) => {
    const generalType = content['display.general.type'];
    const subType = content[`display.${generalType}.type`];

    const isGauge = subType === 'charting' &&
        (content[`display.${generalType}.${subType}.chart`] === 'radialGauge' ||
        content[`display.${generalType}.${subType}.chart`] === 'fillerGauge' ||
        content[`display.${generalType}.${subType}.chart`] === 'markerGauge');

    if (isGauge) {
        return false;
    }

    return true;
};

/**
 * refer to savedsearches.conf.spec.in for the definition of all display properties.
 * @param {object} content is something like this.model.report.entry.content.toJSON()
 * @returns {string} drilldown property key.
 *
 * NOTE: this is only to get drilldown property key, this method cannot be used to get all display
 * properties, because some properties do not follow this pattern. For example:
 * 'display.events.rowNumbers'.
 */
export const getDrilldownPropertyKey = (content) => {
    const generalType = content['display.general.type'];
    if (generalType === 'statistics') {
        return `display.${generalType}.drilldown`;
    }

    const subType = content[`display.${generalType}.type`];

    if (!subType) {
        throw Error('cannot find drilldown property key');
    }

    return `display.${generalType}.${subType}.drilldown`;
};

/**
 * @param {object} content is report.entry.content.toJSON()
 * @returns {string} drilldown property value.
 */
export const getDrilldownPropertyValue = content => content[getDrilldownPropertyKey(content)];

/**
 * @param content {Object} report.entry.content.toJSON()
 * @returns {Object} something like: { 'display.statistics.drilldown': 'cell' }
 */
export const getEnabledDrilldownAttribute = (content) => {
    if (!isDrilldownSupported(content)) {
        return {};
    }

    const key = getDrilldownPropertyKey(content);

    switch (key) {
        case 'display.events.raw.drilldown':
        case 'display.events.list.drilldown':
            return { [key]: 'full' };
        case 'display.events.table.drilldown':
            return { [key]: '1' };
        case 'display.statistics.drilldown':
            return { [key]: 'cell' };
        default:
            return { [key]: 'all' };
    }
};

/**
 * @param content {Object} report.entry.content.toJSON()
 * @returns {Object} something like: { 'display.statistics.drilldown': 'none' }
 */
export const getDisabledDrilldownAttribute = (content) => {
    if (!isDrilldownSupported(content)) {
        return {};
    }

    const key = getDrilldownPropertyKey(content);

    if (key === 'display.events.table.drilldown') {
        return { [key]: '0' };
    }

    return { [key]: 'none' };
};

export const enabledDrilldownSet = {
    'display.events.list.drilldown': 'full',
    'display.events.raw.drilldown': 'full',
    'display.events.table.drilldown': '1',
    'display.statistics.drilldown': 'all',
    'display.visualizations.charting.drilldown': 'all',
    'display.visualizations.singlevalue.drilldown': 'all',
    'display.visualizations.mapping.drilldown': 'all',
    'display.visualizations.custom.drilldown': 'all',
};

export const disabledDrilldownSet = {
    'display.events.list.drilldown': 'none',
    'display.events.raw.drilldown': 'none',
    'display.events.table.drilldown': '0',
    'display.statistics.drilldown': 'none',
    'display.visualizations.charting.drilldown': 'none',
    'display.visualizations.singlevalue.drilldown': 'none',
    'display.visualizations.mapping.drilldown': 'none',
    'display.visualizations.custom.drilldown': 'none',
};

/**
 * This function is to solve a specific problem:
 * When a dashboard element changes its type, its drilldown definition needs to be transferred too.
 *
 * Example:
 *
 * Here is a table:
 *
 * this.model.report.entry.content = {
 *     'display.general.type': 'statistics',
 *     'display.statistics.drilldown': 'none',
 * };
 *
 * Now the table is changed to a column chart:
 *
 * this.model.report.entry.content = {
 *     'display.general.type': 'visualizations',
 *     'display.visualizations.type': 'charting',
 *     'display.visualizations.charting.chart': 'column',
 * }
 *
 * In this case the { 'display.statistics.drilldown': 'none' } needs to be transferred to
 * { 'display.visualizations.charting.drilldown': 'none' }
 *
 * @param {object} previousReportContent is something like this.model.report.entry.content.toJSON()
 * @param {object} currentReportContent is something like this.model.report.entry.content.toJSON()
 * @return {object} the drilldown key-value pair that can be set on this.model.report.entry.content
 */
export const transferDrilldown = (previousReportContent, currentReportContent) => {
    if (!isDrilldownSupported(previousReportContent) || !isDrilldownSupported(currentReportContent)) {
        // will not transfer drilldown if either previous or current does not support drilldown
        return {};
    }

    const previousDrilldownKey = getDrilldownPropertyKey(previousReportContent);
    const currentDrilldownKey = getDrilldownPropertyKey(currentReportContent);

    const previousDrilldownValue = previousReportContent[previousDrilldownKey];

    let drilldownSet;

    if (enabledDrilldownSet[previousDrilldownKey] === previousDrilldownValue) {
        drilldownSet = enabledDrilldownSet;
    } else if (disabledDrilldownSet[previousDrilldownKey] === previousDrilldownValue) {
        drilldownSet = disabledDrilldownSet;
    } else {
        // cannot recognize the status of drilldown, will do nothing
        return {};
    }

    const currentDrilldownValue = drilldownSet[currentDrilldownKey];

    if (typeof currentDrilldownValue !== 'string') {
        // cannot find the right drilldown status for current viz type, will do nothing
        return {};
    }

    return {
        [currentDrilldownKey]: currentDrilldownValue,
    };
};

/**
 * @param {string} the vizType
 * @returns {boolean} whether if it is a custom vizType
 */
export const isCustomViz = vizType => vizType === 'viz';
