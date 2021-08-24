/* eslint brace-style: ["error", "stroustrup"] */

/**
 * The DataFormatter library.  A helper library to split a dataset into multiple datasets for "small multiples"
 * visualization.
 */

import debugModule from 'debug';
import $ from 'jquery';
import _ from 'underscore';
import { DEBUG } from 'util/env';

const debug = DEBUG ? debugModule('viz.utils.DataFormatter') : $.noop;

const RESERVED_FIELD_NAMES = {
    geom: 1,
};

/**
 * Get the data source format mode, including "columns", "rows", "results" and "false".
 *
 * @param {Object} dataset
 * @returns {String} mode - The dataset format mode
 */
function getMode(dataset) {
    if (dataset.columns) {
        return 'columns';
    }
    else if (dataset.rows) {
        return 'rows';
    }
    else if (dataset.results) {
        return 'results';
    }
    return false;
}

/**
 * Get the base-dataset by mode.
 *
 * @param {String} mode - The dataset format mode.  [columns | rows | results]
 * @returns {Object} dataset - The base dataset
 *
 * Examples:
 *
 * If mode = columns, then base-dataset is:
 *  {
 *      split_meta: {},
 *      fields: [],
 *      columns: []
 *  }
 *
 * If mode = rows, then base-dataset is:
 *  {
 *      split_meta: {},
 *      fields: [],
 *      rows: [],
 *  }
 *
 * If mode = results, then base-dataset is:
 *  {
 *      split_meta: {}
 *      fields: [],
 *      results: []
 *  }
 *
 *  Otherwise, the base-dataset is:
 *  {
 *  }
 */
function getBaseDataset(mode) {
    if (['columns', 'rows', 'results'].indexOf(mode) === -1) {
        return {};
    }

    const dataset = {
        split_meta: {},
        fields: [],
    };

    if (['columns', 'rows'].indexOf(mode) !== -1) {
        dataset[mode] = [];
    }
    else {
        dataset.results = [];
    }

    return dataset;
}

function getId(dataset) {
    if (dataset.split_meta && dataset.split_meta.id) {
        return dataset.split_meta.id;
    }
    return 'viz';
}

function getName(dataset, name) {
    const splitMetaName = name || '';
    if (dataset.split_meta && dataset.split_meta.name) {
        return [dataset.split_meta.name, splitMetaName].join('|');
    }
    return splitMetaName;
}

function getValue(dataset, value) {
    const splitMetaValue = value || '';
    if (dataset.split_meta && dataset.split_meta.value) {
        return [dataset.split_meta.value, splitMetaValue].join('|');
    }
    return splitMetaValue;
}

/**
 * Get record element names by field name.
 *
 * @params {Object} dataset - The dataset for visualization
 * @params {Object} dataset.fields - The dataset fields
 * @params {Object} dataset.[mode] - The dataset format, which its mode can be [columns | rows | results].
 * @params {String} fieldName - The field elements in the dataset fields
 * @returns {Object} values - The element names of given field name
 */
function getElementsByFieldName(dataset, fieldName) {
    let elements = [];
    const mode = getMode(dataset);

    if (mode === 'columns') {
        _.each(dataset.fields, (field, fieldIndex) => {
            if (field.name && field.name === fieldName) {
                elements = _.chain(dataset[mode][fieldIndex])
                    .sortBy(name => name)
                    .uniq(true)
                    .value();
            }
        });
    }
    else if (mode === 'rows') {
        _.each(dataset.fields, (field, fieldIndex) => {
            if (field.name && field.name === fieldName) {
                const elementsMap = {};
                _.each(dataset[mode], (record) => {
                    const element = record[fieldIndex];

                    if (!elementsMap[element]) {
                        elementsMap[element] = 0;
                    }

                    elementsMap[element] += 1;
                });

                elements = _.chain(elementsMap)
                    .map((count, name) => name)
                    .sortBy(name => name)
                    .value();
            }
        });
    }
    else if (mode === 'results') {
        _.each(dataset.fields, (field) => {
            if (field.name && field.name === fieldName) {
                const elementsMap = {};
                _.each(dataset[mode], (record) => {
                    const element = record[field.name];

                    if (!elementsMap[element]) {
                        elementsMap[element] = 0;
                    }

                    elementsMap[element] += 1;
                });

                elements = _.chain(elementsMap)
                    .map((count, name) => name)
                    .sortBy(name => name)
                    .value();
            }
        });
    }

    return elements;
}

/**
 * Get the field names
 * @param {Object} fields - The dataset fields
 * @param {Boolean} hidden - Show the hidden field names or not. (default: false)
 * @param {Boolean} splitByField - Return splitby_field if necessary instead of name. (default: true)
 * @returns {Object} fields - The field names.
 */
function getFieldNames(fields, { hidden = false, splitByField = true } = {}) {
    if (!fields) {
        return [];
    }
    const splitFields = [];
    const splitByFields = {};

    fields.forEach((field) => {
        if (splitByField && field.splitby_field) {
            if (!splitByFields[field.splitby_field]) {
                splitFields.push(field.splitby_field);
                splitByFields[field.splitby_field] = true;
            }
        }
        else if (hidden || !/^_/.test(field.name)) {
            splitFields.push(field.name);
        }
    });

    return splitFields;
}

/**
 * Get the field type of the given field name.
 *
 * @param {Object} fields - The dataset fields
 * @param {String} fieldName - The field name
 * @returns {String} type - The field type. [group_by | split_by | default | false]
 */
function getFieldType(fields, fieldName) {
    let type = false;

    _.every(fields, (field) => {
        if (field.groupby_rank && field.name === fieldName) {
            type = 'group_by';
            return false;
        }
        else if (field.splitby_field && field.splitby_field === fieldName) {
            type = 'split_by';
            return false;
        }
        else if (field.name && field.name === fieldName) {
            type = 'default';
            return false;
        }
        return true;
    });

    return type;
}

/**
 * Get data-sources distribution.
 *
 * @param {Object} fields - The dataset fields
 * @returns {Object} sources - The data sources distribution
 *
 * case 1: groupby_rank:no  data_source:no
 * ========================================
 *
 *  INPUT
 *  {
 *      name: 'median(bytes)'
 *  },
 *  {
 *      name: '_time'
 *  }
 *
 *  OUTPUT
 *  {
 *      'median(bytes)': 1
 *  }
 *
 * case 2: groupby_rank:no  data_source:yes
 * ========================================
 *
 *  INPUT
 *  {
 *      name: 'splunk'
 *  },
 *  {
 *      name: '19.99',
 *      data_source: 'avg(bytes)',
 *      splitby_field: 'price',
 *      splitby_value: '19.99'
 *  }
 *
 *  OUTPUT
 *  {
 *      'avg(bytes)': 1
 *  }
 *
 * case 3: groupby_rank:yes data_source:no
 * ========================================
 *
 *  INPUT
 *  {
 *      name: 'action',
 *      groupby_rank: '0'
 *  },
 *  {
 *      name: 'median(bytes)'
 *  },
 *  {
 *      name: '_time'
 *  }
 *
 *  OUTPUT
 *  {
 *      'median(bytes)': 1
 *  }
 *
 * case 4: groupby_rank:yes data_source:yes
 * ========================================
 *
 *  INPUT
 *  {
 *      name: 'action',
 *      groupby_rank: '0'
 *  },
 *  {
 *      name: 'median(bytes)'
 *  },
 *  {
 *      name: '_time'
 *  },
 *  {
 *      name: '19.99',
 *      data_source: 'avg(bytes)',
 *      splitby_field: 'price',
 *      splitby_value: '19.99'
 *  }
 *
 *  OUTPUT
 *  {
 *      'avg(bytes)': 1
 *  }
 *
 */
function getSources(fields) {
    const names = {};
    const sources = {};

    _.each(fields, (field) => {
        if (field.data_source) {
            if (!sources[field.data_source]) {
                sources[field.data_source] = 0;
            }
            sources[field.data_source] += 1;
        }
        else if (!RESERVED_FIELD_NAMES[field.name] && !field.groupby_rank && !/^_/.test(field.name)) {
            if (!names[field.name]) {
                names[field.name] = 0;
            }
            names[field.name] += 1;
        }
    });

    return _.size(sources) > 0 ? sources : names;
}

/**
 * Get the suggested field names
 * @param {Object} fields - The dataset fields
 * @returns {Object} fields - The suggested field names.
 */
function getSuggestedFieldNames(fields) {
    const names = {};

    _.each(fields, (field) => {
        if (field.groupby_rank && !/^_/.test(field.name)) {
            names[field.name] = 1;
        }
        else if (field.data_source && field.splitby_field && !/^_/.test(field.splitby_field)) {
            names[field.splitby_field] = 1;
        }
    });

    return _.keys(names);
}

/**
 * Get split-field-values distribution.
 *
 * @param {Object} fields - The dataset fields
 * @param {String} splitField - The split-field name
 * @returns {Object} values - split-field-values distribution
 */
function getValuesBySplitField(fields, splitField) {
    const values = {};

    _.each(fields, (field) => {
        if (field.splitby_field && field.splitby_field === splitField) {
            if (!values[field.splitby_value]) {
                values[field.splitby_value] = 0;
            }
            values[field.splitby_value] += 1;
        }
    });

    return values;
}

function groupByFieldName(dataset, fieldName) {
    const mode = getMode(dataset);
    const baseDataset = getBaseDataset(mode);
    const elementList = getElementsByFieldName(dataset, fieldName);
    const splitDatasets = [];
    let count = 0;

    // get the split-field index
    let splitFieldIndex = -1;
    _.each(dataset.fields, (field, fieldIndex) => {
        if (field.name === fieldName) {
            splitFieldIndex = fieldIndex;
        }
    });

    if (splitFieldIndex !== -1) {
        // group: fields
        baseDataset.fields = $.extend(true, [], dataset.fields);
        baseDataset.fields[splitFieldIndex].name = `_${baseDataset.fields[splitFieldIndex].name}`;

        // group: "columns"
        if (mode === 'columns') {
            _.each(dataset[mode][splitFieldIndex], (element, elementIndex) => {
                const splitDatasetsIndex = elementList.indexOf(element);

                if (!splitDatasets[splitDatasetsIndex]) {
                    splitDatasets[splitDatasetsIndex] = $.extend(
                        true,
                        {},
                        baseDataset,
                        {
                            split_meta: {
                                id: [getId(dataset), 'groupby_field', fieldName, 'groupby_value', element].join('|'),
                                index: count,
                                name: getName(dataset, fieldName),
                                value: getValue(dataset, element),
                            },
                        },
                    );

                    count += 1;
                }

                _.each(dataset[mode], (record, recordIndex) => {
                    if (!splitDatasets[splitDatasetsIndex][mode][recordIndex]) {
                        splitDatasets[splitDatasetsIndex][mode][recordIndex] = [];
                    }

                    splitDatasets[splitDatasetsIndex][mode][recordIndex].push(record[elementIndex]);
                });
            });
        }

        // group: "rows"
        else if (mode === 'rows') {
            _.each(dataset[mode], (record) => {
                const element = record[splitFieldIndex];
                const splitDatasetsIndex = elementList.indexOf(element);

                if (!splitDatasets[splitDatasetsIndex]) {
                    splitDatasets[splitDatasetsIndex] = $.extend(
                        true,
                        {},
                        baseDataset,
                        {
                            split_meta: {
                                id: [getId(dataset), 'groupby_field', fieldName, 'groupby_value', element].join('|'),
                                index: count,
                                name: getName(dataset, fieldName),
                                value: getValue(dataset, element),
                            },
                        },
                    );

                    count += 1;
                }

                splitDatasets[splitDatasetsIndex][mode].push(record);
            });
        }

        // group: "results"
        else if (mode === 'results') {
            _.each(dataset[mode], (record) => {
                const element = record[fieldName];
                const splitDatasetsIndex = elementList.indexOf(element);

                if (!splitDatasets[splitDatasetsIndex]) {
                    splitDatasets[splitDatasetsIndex] = $.extend(
                        true,
                        {},
                        baseDataset,
                        {
                            split_meta: {
                                id: [getId(dataset), 'groupby_field', fieldName, 'groupby_value', element].join('|'),
                                index: count,
                                name: getName(dataset, fieldName),
                                value: getValue(dataset, element),
                            },
                        },
                    );

                    count += 1;
                }

                splitDatasets[splitDatasetsIndex][mode].push(record);
            });
        }
    }

    return splitDatasets;
}

function isUniqueIds(datasets) {
    const map = {};
    return _.every(datasets, (dataset) => {
        const id = getId(dataset);
        if (map[id]) {
            return false;
        }
        map[id] = 1;
        return true;
    });
}

function normalizeDataset(dataset) {
    debug('normalizeDataset', 'dataset', dataset);

    let normalizedDataset;

    //
    // Step 1: Analyze the dataset, and collect the following information:
    //
    //  - keys of groupby_rank
    //  - keys of data_sources
    //  - keys of splitby_field
    //  - keys of splitby_value
    //  - index position of geom
    //
    const map = {
        groupby_rank: {},
        groupby_rank_deleted: {},
        data_source: {},
        splitby_field: {},
        splitby_field_deleted: {},
        splitby_value: {},
    };
    const res = {
        groupby_rank: [],
        groupby_rank_deleted: [],
        data_source: [],
        splitby_field: [],
        splitby_field_deleted: [],
        splitby_value: [],
        field_index_geom: -1,
    };
    _.each(dataset.fields, (field, fieldIndex) => {
        if (field.groupby_rank && field.name) {
            if ((!/^_/.test(field.name) || field.name === '_time')) {
                if (!_.has(map.groupby_rank, field.name)) {
                    map.groupby_rank[field.name] = res.groupby_rank.length;
                    res.groupby_rank.push(field.name);
                }
            }
            else if (!_.has(map.groupby_rank_deleted, field.name)) {
                map.groupby_rank_deleted[field.name] = res.groupby_rank_deleted.length;
                res.groupby_rank_deleted.push(field.name);
            }
        }
        else if (field.data_source && field.splitby_field) {
            if (!/^_/.test(field.splitby_field)) {
                _.each(['data_source', 'splitby_field', 'splitby_value'], (name) => {
                    if (!_.has(map[name], field[name])) {
                        map[name][field[name]] = res[name].length;
                        res[name].push(field[name]);
                    }
                });
            }
            else if (!_.has(map.splitby_field_deleted, field.name)) {
                map.splitby_field_deleted[field.splitby_field] = res.splitby_field_deleted.length;
                res.splitby_field_deleted.push(field.splitby_field);
            }
        }
        else if (field.name === 'geom') {
            res.field_index_geom = fieldIndex;
        }
    });

    //
    // Step 2: Read the result in #1 and perform transformation to stabilize the dataset.
    //

    // case 1: Dataset is unstable. Split on a field with "groupby_rank".
    // => Transform dataset.fields and dataset.[columns|rows|results] to stabilize it.
    if (!_.isEmpty(res.data_source) && _.isEmpty(res.groupby_rank)) {
        const mode = getMode(dataset);
        normalizedDataset = _.omit(dataset, 'fields', mode);

        // "fields"
        const fields = [];

        _.each(res.splitby_field, (name, index) => {
            fields.push({
                name,
                groupby_rank: index + '',   // eslint-disable-line prefer-template
            });
        });

        _.each(res.data_source, (source) => {
            fields.push({
                name: source,
            });
        });

        normalizedDataset.fields = fields;

        // "columns"
        if (mode === 'columns') {
            const columns = [];

            columns.push(res.splitby_value);

            const records = [];
            _.each(dataset.fields, (field, fieldIndex) => {
                if (field.data_source && field.splitby_field && !/^_/.test(field.splitby_field)) {
                    const recordsIndex = map.data_source[field.data_source];

                    if (!records[recordsIndex]) {
                        records[recordsIndex] = [];
                    }

                    records[recordsIndex] = records[recordsIndex].concat(dataset[mode][fieldIndex]);
                }
            });

            normalizedDataset[mode] = columns.concat(records);
        }

        // "rows"
        else if (mode === 'rows') {
            const rows = [];

            _.each(res.splitby_value, (value, valueIndex) => {
                if (!rows[valueIndex]) {
                    rows[valueIndex] = [];
                }
                rows[valueIndex].push(value);

                _.each(dataset.fields, (field, fieldIndex) => {
                    if (field.data_source && field.splitby_value && field.splitby_value === value) {
                        _.each(dataset[mode], (record) => {
                            rows[valueIndex].push(record[fieldIndex]);
                        });
                    }
                });
            });

            normalizedDataset[mode] = rows;
        }

        // "results"
        else if (mode === 'results') {
            const results = [];

            _.each(res.splitby_value, (value, valueIndex) => {
                if (!results[valueIndex]) {
                    results[valueIndex] = {};
                }

                _.each(res.splitby_field, (field) => {
                    results[valueIndex][field] = value;
                });

                _.each(dataset.fields, (field) => {
                    if (field.data_source && field.splitby_value && field.splitby_value === value) {
                        _.each(dataset[mode], (record) => {
                            results[valueIndex][field.data_source] = record[`${field.data_source}: ${value}`];
                        });
                    }
                });
            });

            normalizedDataset[mode] = results;
        }
    }

    // case 2: Dataset is unstable. Split on "aggregation" with non-empty "data_source".
    // => Transform the dataset.fields to stabilize it.
    else if (!_.isEmpty(res.data_source) && !_.isEmpty(res.groupby_rank)) {
        normalizedDataset = _.omit(dataset, 'fields');

        // "fields"
        const fields = [];
        const splitByField = dataset.split_meta.value || '';

        _.each(dataset.fields, (field) => {
            if (field.splitby_value && _.has(map.data_source, field.data_source)
                && field.data_source === splitByField) {
                fields.push(
                    $.extend(
                        {},
                        field,
                        {
                            name: field.splitby_value,
                        },
                    ),
                );
            }
            else {
                fields.push(field);
            }
        });

        normalizedDataset.fields = fields;
    }

    // case 3: Dataset is unstable. Split on a field with "splitby_field".
    // => Transform the dataset.fields to stabilize it.
    else if (_.isEmpty(res.data_source) && !_.isEmpty(res.splitby_field_deleted)) {
        normalizedDataset = _.omit(dataset, 'fields');

        // "fields"
        const fields = [];

        _.each(dataset.fields, (field) => {
            if (field.splitby_field && _.has(map.splitby_field_deleted, field.splitby_field)) {
                fields.push({
                    name: field.data_source,
                });
            }
            else {
                fields.push(field);
            }
        });

        normalizedDataset.fields = fields;
    }

    // case 4: Dataset is stable.
    else {
        normalizedDataset = dataset;
    }

    //
    // Step 3: Geom should be positioned at the end of the field list.
    // => Transform the dataset.fields and dataset[mode] to stabilize it.
    if (res.field_index_geom !== -1 && res.field_index_geom !== normalizedDataset.fields.length - 1) {
        let temp;

        const geomIndex = res.field_index_geom;
        const lastIndex = normalizedDataset.fields.length - 1;
        const mode = getMode(dataset);

        // fields
        temp = normalizedDataset.fields[geomIndex];
        normalizedDataset.fields[geomIndex] = normalizedDataset.fields[lastIndex];
        normalizedDataset.fields[lastIndex] = temp;

        // "columns"
        if (mode === 'columns') {
            temp = normalizedDataset[mode][geomIndex];
            normalizedDataset[mode][geomIndex] = normalizedDataset[mode][lastIndex];
            normalizedDataset[mode][lastIndex] = temp;
        }

        // "rows"
        else if (mode === 'rows') {
            _.each(normalizedDataset[mode], (record, recordIndex) => {
                temp = normalizedDataset[mode][recordIndex][geomIndex];
                normalizedDataset[mode][recordIndex][geomIndex] = normalizedDataset[mode][recordIndex][lastIndex];
                normalizedDataset[mode][recordIndex][lastIndex] = temp;
            });
        }
    }

    //
    // Step 4: Clean up "groupby_rank" split-field.
    //  => Remove deleted field names and values.
    if (!_.isEmpty(res.groupby_rank_deleted)) {
        const mode = getMode(dataset);
        let count = 0;
        const deletedFields = {};

        // fields
        _.each(normalizedDataset.fields, (field, fieldIndex) => {
            if (field.name && field.groupby_rank) {
                if (_.has(map.groupby_rank_deleted, field.name)) {
                    // set falsy on deleted field
                    normalizedDataset.fields[fieldIndex] = undefined;
                    deletedFields[fieldIndex] = field.name.replace(/^_/g, '');
                    count += 1;
                }
                else {
                    // eslint-disable-next-line prefer-template, no-param-reassign
                    field.groupby_rank = (parseInt(field.groupby_rank, 10) - count) + '';
                }
            }
        });
        // compact the arrays with all the falsy are removed
        normalizedDataset.fields = _.compact(normalizedDataset.fields);

        // "columns"
        if (mode === 'columns') {
            // eslint-disable-next-line prefer-template, no-param-reassign
            _.keys(deletedFields).forEach((fieldIndex) => {
                normalizedDataset[mode][fieldIndex] = undefined;
            });
            normalizedDataset[mode] = _.compact(normalizedDataset[mode]);
        }

        // "rows"
        else if (mode === 'rows') {
            _.each(normalizedDataset[mode], (record, recordIndex) => {
                _.each(_.keys(deletedFields), (fieldIndex) => {
                    // eslint-disable-next-line prefer-template, no-param-reassign
                    record[fieldIndex] = undefined;
                });
                normalizedDataset[mode][recordIndex] = _.compact(record);
            });
        }

        // "results"
        else if (mode === 'results') {
            _.each(normalizedDataset[mode], (record) => {
                _.each(_.values(deletedFields), (fieldName) => {
                    // eslint-disable-next-line prefer-template, no-param-reassign
                    delete record[fieldName];
                });
            });
        }
    }

    debug('normalizeDataset', 'normalizedDataset', normalizedDataset);

    return normalizedDataset;
}

function splitBySources(dataset) {
    const mode = getMode(dataset);
    const baseDataset = getBaseDataset(mode);
    const splitDatasets = [];
    const sources = getSources(dataset.fields);
    let count = 0;

    // split: "columns"
    if (mode === 'columns') {
        // dataset: "non-aggregated" fields
        _.each(dataset.fields, (field, fieldIndex) => {
            if (field.data_source) {
                if (!sources[field.data_source] && !sources[field.name]) {
                    baseDataset.fields.push(field);
                    baseDataset[mode].push(dataset[mode][fieldIndex]);
                }
            }
            else if (!sources[field.name]) {
                baseDataset.fields.push(field);
                baseDataset[mode].push(dataset[mode][fieldIndex]);
            }
        });

        // dataset: "aggregated" fields
        _.each(_.keys(sources), (source, sourceIndex) => {
            _.each(dataset.fields, (field, fieldIndex) => {
                if (field.data_source) {
                    if (field.data_source === source) {
                        if (!splitDatasets[sourceIndex]) {
                            const newDataset = $.extend(true,
                                {},
                                baseDataset,
                                {
                                    split_meta: {
                                        id: [getId(dataset), 'data_source', source].join('|'),
                                        index: count,
                                        name: getName(dataset, 'data_source'),
                                        value: getValue(dataset, source),
                                    },
                                },
                            );
                            splitDatasets.push(newDataset);
                            count += 1;
                        }

                        splitDatasets[sourceIndex].fields.push(field);
                        splitDatasets[sourceIndex][mode].push(dataset[mode][fieldIndex]);
                    }
                }
                else if (field.name === source) {
                    if (!splitDatasets[sourceIndex]) {
                        const newDataset = $.extend(true,
                            {},
                            baseDataset,
                            {
                                split_meta: {
                                    id: [getId(dataset), 'data_source', source].join('|'),
                                    index: count,
                                    name: getName(dataset, 'data_source'),
                                    value: getValue(dataset, source),
                                },
                            },
                        );
                        splitDatasets.push(newDataset);
                        count += 1;
                    }

                    splitDatasets[sourceIndex].fields.push(field);
                    splitDatasets[sourceIndex][mode].push(dataset[mode][fieldIndex]);
                }
            });
        });
    }

    // split: "rows"
    else if (mode === 'rows') {
        // dataset: "non-aggregated" fields
        _.each(dataset.fields, (field, fieldIndex) => {
            if (field.data_source) {
                if (!sources[field.data_source] && !sources[field.name]) {
                    baseDataset.fields.push(field);

                    _.each(dataset[mode], (record, recordIndex) => {
                        if (!baseDataset[mode][recordIndex]) {
                            baseDataset[mode][recordIndex] = [];
                        }

                        baseDataset[mode][recordIndex].push(record[fieldIndex]);
                    });
                }
            }
            else if (!sources[field.name]) {
                baseDataset.fields.push(field);

                _.each(dataset[mode], (record, recordIndex) => {
                    if (!baseDataset[mode][recordIndex]) {
                        baseDataset[mode][recordIndex] = [];
                    }

                    baseDataset[mode][recordIndex].push(record[fieldIndex]);
                });
            }
        });

        // dataset: "aggregated" fields
        _.each(_.keys(sources), (source, sourceIndex) => {
            _.each(dataset.fields, (field, fieldIndex) => {
                if (field.data_source) {
                    if (field.data_source === source) {
                        if (!splitDatasets[sourceIndex]) {
                            const newDataset = $.extend(true,
                                {},
                                baseDataset,
                                {
                                    split_meta: {
                                        id: [getId(dataset), 'data_source', source].join('|'),
                                        index: count,
                                        name: getName(dataset, 'data_source'),
                                        value: getValue(dataset, source),
                                    },
                                },
                            );
                            splitDatasets.push(newDataset);
                            count += 1;
                        }

                        splitDatasets[sourceIndex].fields.push(field);

                        _.each(dataset[mode], (record, recordIndex) => {
                            if (!splitDatasets[sourceIndex][mode][recordIndex]) {
                                splitDatasets[sourceIndex][mode][recordIndex] = [];
                            }

                            splitDatasets[sourceIndex][mode][recordIndex].push(record[fieldIndex]);
                        });
                    }
                }
                else if (field.name === source) {
                    if (!splitDatasets[sourceIndex]) {
                        const newDataset = $.extend(true,
                            {},
                            baseDataset,
                            {
                                split_meta: {
                                    id: [getId(dataset), 'data_source', source].join('|'),
                                    index: count,
                                    name: getName(dataset, 'data_source'),
                                    value: getValue(dataset, source),
                                },
                            },
                        );
                        splitDatasets.push(newDataset);
                        count += 1;
                    }

                    splitDatasets[sourceIndex].fields.push(field);

                    _.each(dataset[mode], (record, recordIndex) => {
                        if (!splitDatasets[sourceIndex][mode][recordIndex]) {
                            splitDatasets[sourceIndex][mode][recordIndex] = [];
                        }

                        splitDatasets[sourceIndex][mode][recordIndex].push(record[fieldIndex]);
                    });
                }
            });
        });
    }

    // split: "results"
    else if (mode === 'results') {
        // dataset: "non-aggregated" fields
        _.each(dataset.fields, (field) => {
            if (field.data_source) {
                if (!sources[field.data_source] && !sources[field.name]) {
                    baseDataset.fields.push(field);

                    _.each(dataset[mode], (record, recordIndex) => {
                        if (!baseDataset[mode][recordIndex]) {
                            baseDataset[mode][recordIndex] = {};
                        }

                        baseDataset[mode][recordIndex][field.name] = record[field.name];
                    });
                }
            }
            else if (!sources[field.name]) {
                baseDataset.fields.push(field);

                _.each(dataset[mode], (record, recordIndex) => {
                    if (!baseDataset[mode][recordIndex]) {
                        baseDataset[mode][recordIndex] = {};
                    }

                    baseDataset[mode][recordIndex][field.name] = record[field.name];
                });
            }
        });

        // dataset: "aggregated" fields
        _.each(_.keys(sources), (source, sourceIndex) => {
            _.each(dataset.fields, (field) => {
                if (field.data_source) {
                    if (field.data_source === source) {
                        if (!splitDatasets[sourceIndex]) {
                            const newDataset = $.extend(true,
                                {},
                                baseDataset,
                                {
                                    split_meta: {
                                        id: [getId(dataset), 'data_source', source].join('|'),
                                        index: count,
                                        name: getName(dataset, 'data_source'),
                                        value: getValue(dataset, source),
                                    },
                                },
                            );
                            splitDatasets.push(newDataset);
                            count += 1;
                        }

                        splitDatasets[sourceIndex].fields.push(field);

                        _.each(dataset[mode], (record, recordIndex) => {
                            if (!splitDatasets[sourceIndex][mode][recordIndex]) {
                                splitDatasets[sourceIndex][mode][recordIndex] = {};
                            }

                            splitDatasets[sourceIndex][mode][recordIndex][field.name] = record[field.name];
                        });
                    }
                }
                else if (field.name === source) {
                    if (!splitDatasets[sourceIndex]) {
                        const newDataset = $.extend(true,
                            {},
                            baseDataset,
                            {
                                split_meta: {
                                    id: [getId(dataset), 'data_source', source].join('|'),
                                    index: count,
                                    name: getName(dataset, 'data_source'),
                                    value: getValue(dataset, source),
                                },
                            },
                        );
                        splitDatasets.push(newDataset);
                        count += 1;
                    }

                    splitDatasets[sourceIndex].fields.push(field);

                    _.each(dataset[mode], (record, recordIndex) => {
                        if (!splitDatasets[sourceIndex][mode][recordIndex]) {
                            splitDatasets[sourceIndex][mode][recordIndex] = {};
                        }

                        splitDatasets[sourceIndex][mode][recordIndex][field.name] = record[field.name];
                    });
                }
            });
        });
    }

    return splitDatasets;
}

function splitByValues(dataset, splitField) {
    const mode = getMode(dataset);
    const baseDataset = getBaseDataset(mode);
    const splitDatasets = [];
    const values = getValuesBySplitField(dataset.fields, splitField);
    let count = 0;

    // split: "columns"
    if (mode === 'columns') {
        // dataset: not "splitby_field"
        _.each(dataset.fields, (field, fieldIndex) => {
            if (!_.contains(_.keys(field), 'splitby_field')) {
                baseDataset.fields.push(field);
                baseDataset[mode].push(dataset[mode][fieldIndex]);
            }
        });

        // dataset: "splitby_field"
        _.each(_.keys(values), (value, valueIndex) => {
            _.each(dataset.fields, (field, fieldIndex) => {
                if (_.contains(_.keys(field), 'splitby_value') && field.splitby_value === value) {
                    if (!splitDatasets[valueIndex]) {
                        const newDataset = $.extend(true,
                            {},
                            baseDataset,
                            {
                                split_meta: {
                                    id: [
                                        getId(dataset),
                                        'splitby_field', field.splitby_field,
                                        'splitby_value', field.splitby_value,
                                    ].join('|'),
                                    index: count,
                                    name: getName(dataset, field.splitby_field),
                                    value: getValue(dataset, field.splitby_value),
                                },
                            },
                        );
                        splitDatasets.push(newDataset);
                        count += 1;
                    }

                    const updatedField = $.extend(true, {}, field);
                    updatedField.splitby_field = `_${updatedField.splitby_field}`;
                    splitDatasets[valueIndex].fields.push(updatedField);

                    splitDatasets[valueIndex][mode].push(dataset[mode][fieldIndex]);
                }
            });
        });
    }

    // split: "rows"
    else if (mode === 'rows') {
        // dataset: not "splitby_field"
        _.each(dataset.fields, (field, fieldIndex) => {
            if (!_.contains(_.keys(field), 'splitby_field')) {
                baseDataset.fields.push(field);

                _.each(dataset[mode], (record, recordIndex) => {
                    if (!baseDataset[mode][recordIndex]) {
                        baseDataset[mode][recordIndex] = [];
                    }

                    baseDataset[mode][recordIndex].push(record[fieldIndex]);
                });
            }
        });

        // dataset: "splitby_field"
        _.each(_.keys(values), (value, valueIndex) => {
            _.each(dataset.fields, (field, fieldIndex) => {
                if (_.contains(_.keys(field), 'splitby_value') && field.splitby_value === value) {
                    if (!splitDatasets[valueIndex]) {
                        const newDataset = $.extend(true,
                            {},
                            baseDataset,
                            {
                                split_meta: {
                                    id: [
                                        getId(dataset),
                                        'splitby_field', field.splitby_field,
                                        'splitby_value', field.splitby_value,
                                    ].join('|'),
                                    index: count,
                                    name: getName(dataset, field.splitby_field),
                                    value: getValue(dataset, field.splitby_value),
                                },
                            },
                        );
                        splitDatasets.push(newDataset);
                        count += 1;
                    }

                    const updatedField = $.extend(true, {}, field);
                    updatedField.splitby_field = `_${updatedField.splitby_field}`;
                    splitDatasets[valueIndex].fields.push(updatedField);

                    _.each(dataset[mode], (record, recordIndex) => {
                        if (!splitDatasets[valueIndex][mode][recordIndex]) {
                            splitDatasets[valueIndex][mode][recordIndex] = [];
                        }

                        splitDatasets[valueIndex][mode][recordIndex].push(record[fieldIndex]);
                    });
                }
            });
        });
    }
    // split: "results"
    else if (mode === 'results') {
        // dataset: not "splitby_field"
        _.each(dataset.fields, (field) => {
            if (!_.contains(_.keys(field), 'splitby_field')) {
                baseDataset.fields.push(field);

                _.each(dataset[mode], (record, recordIndex) => {
                    if (!baseDataset[mode][recordIndex]) {
                        baseDataset[mode][recordIndex] = {};
                    }

                    baseDataset[mode][recordIndex][field.name] = record[field.name];
                });
            }
        });

        // dataset: "splitby_field"
        _.each(_.keys(values), (value, valueIndex) => {
            _.each(dataset.fields, (field) => {
                if (_.contains(_.keys(field), 'splitby_value') && field.splitby_value === value) {
                    if (!splitDatasets[valueIndex]) {
                        const newDataset = $.extend(true,
                            {},
                            baseDataset,
                            {
                                split_meta: {
                                    id: [
                                        getId(dataset),
                                        'splitby_field', field.splitby_field,
                                        'splitby_value', field.splitby_value,
                                    ].join('|'),
                                    index: count,
                                    name: getName(dataset, field.splitby_field),
                                    value: getValue(dataset, field.splitby_value),
                                },
                            },
                        );
                        splitDatasets.push(newDataset);
                        count += 1;
                    }

                    const updatedField = $.extend(true, {}, field);
                    updatedField.splitby_field = `_${updatedField.splitby_field}`;
                    splitDatasets[valueIndex].fields.push(updatedField);

                    _.each(dataset[mode], (record, recordIndex) => {
                        if (!splitDatasets[valueIndex][mode][recordIndex]) {
                            splitDatasets[valueIndex][mode][recordIndex] = {};
                        }

                        splitDatasets[valueIndex][mode][recordIndex][field.name] = record[field.name];
                    });
                }
            });
        });
    }

    return splitDatasets;
}

/**
 * Slice the input datasets into multiple datasets based on options.
 *
 * @param {Object[]} datasets - Original datasets from
 * @param {Object} options - The options for the datasets splitting.
 * @param {String[]} options.fields - List of field names to be used for splitting.
 * @param {Boolean} options.is_aggregated - Split by data sources.
 * @returns {Object[]} datasets - Array of split datasets.
 *
 * There are 4 cases for the split.
 *
 * Example:
 *
 * SPL
 * ===
 * source=*
 * | timechart sum(price) as price sum(salePrice) as sale_price count
 *      limit=5 useother=f usenull=f by productName
 *
 * Dataset
 * =======
 *  https://jsonblob.com/57f42ca2e4b0bcac9f7a662b
 *
 *  which has
 *      3 sources:
 *          - price
 *          - sales_price
 *          - count
 *      5 fields:
 *          - Dream Crusher
 *          - Fire Resistance Suit of Provolone
 *          - Mediocre Kingdoms
 *          - SIM Cubicle
 *          - World of Cheese
 *
 * case 1: no split ( 1 chart )
 * ============================
 *
 *  INPUT
 *  options.fields = []
 *  options.is_aggregated = true
 *
 *  OUTPUT
 *  https://jsonblob.com/57f42d4ee4b0bcac9f7a662c
 *
 * case 2: split by sources ( 3 charts )
 * =====================================
 *
 *  INPUT
 *  options.fields = []
 *  options.is_aggregated = false
 *
 *  OUTPUT
 *  https://jsonblob.com/57f42dcde4b0bcac9f7a662f
 *
 * case 3: split by field names ( 5 charts )
 * =========================================
 *
 *  INPUT
 *  options.fields = ['productName']
 *  options.is_aggregated = true
 *
 *  OUTPUT
 *  https://jsonblob.com/57f42e1ee4b0bcac9f7a6630
 *
 * case 4: split by both sources and field names ( 15 charts )
 * ===========================================================
 *
 *  INPUT
 *  options.fields = ['productName']
 *  options.is_aggregated = false
 *
 *  OUTPUT
 *  https://jsonblob.com/57f42e7ce4b0bcac9f7a6631
 *
 */
function getSplitData(datasets, options) {
    debug('getSplitData', 'datasets', datasets, 'options', options);

    const fields = options.fields || [];
    const isAggregated = options.is_aggregated || false;

    let currDatasets;
    let nextDatasets = datasets;

    // case 1: no split
    if (isAggregated && _.isEmpty(fields)) {
        // noop
    }

    // case 2: split "sources" only
    else if (!isAggregated && _.isEmpty(fields)) {
        currDatasets = nextDatasets;
        nextDatasets = [];

        _.each(currDatasets, (dataset) => {
            nextDatasets = nextDatasets.concat(splitBySources(dataset));

            if (_.isEmpty(nextDatasets)) {
                nextDatasets = nextDatasets.concat(dataset);
            }
        }, this);
    }

    // case 3: split "fields" only
    else if (isAggregated && !_.isEmpty(fields)) {
        _.each(fields, (field) => {
            currDatasets = nextDatasets;
            nextDatasets = [];

            _.each(currDatasets, (dataset) => {
                const fieldType = getFieldType(dataset.fields, field);

                if (fieldType === 'split_by') {
                    nextDatasets = nextDatasets.concat(splitByValues(dataset, field));
                }
                else if (fieldType === 'group_by' || fieldType === 'default') {
                    nextDatasets = nextDatasets.concat(groupByFieldName(dataset, field));
                }
            }, this);
        }, this);
    }

    // case 4: split "sources" and "fields"
    else {
        currDatasets = nextDatasets;
        nextDatasets = [];

        // split by sources
        _.each(currDatasets, (dataset) => {
            nextDatasets = nextDatasets.concat(splitBySources(dataset));

            if (_.isEmpty(nextDatasets)) {
                nextDatasets = nextDatasets.concat(dataset);
            }
        }, this);

        // split by fields
        _.each(fields, (field) => {
            currDatasets = nextDatasets;
            nextDatasets = [];

            _.each(currDatasets, (dataset) => {
                const fieldType = getFieldType(dataset.fields, field);

                if (fieldType === 'split_by') {
                    nextDatasets = nextDatasets.concat(splitByValues(dataset, field));
                }
                else if (fieldType === 'group_by' || fieldType === 'default') {
                    nextDatasets = nextDatasets.concat(groupByFieldName(dataset, field));
                }
            }, this);
        }, this);
    }

    return nextDatasets.map(normalizeDataset);
}

export default {
    // main utility function
    getSources,
    getSplitData,
    getSuggestedFieldNames,
    // export internal utility functions to make them testable
    getBaseDataset,
    getElementsByFieldName,
    getFieldNames,
    getFieldType,
    getId,
    getMode,
    getName,
    getValue,
    getValuesBySplitField,
    groupByFieldName,
    isUniqueIds,
    normalizeDataset,
    splitBySources,
    splitByValues,
};
