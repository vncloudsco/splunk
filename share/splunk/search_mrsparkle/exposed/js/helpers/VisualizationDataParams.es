import _ from 'underscore';
import { isInteger } from 'util/math_utils';
import { normalizeBoolean } from 'util/general_utils';

// eslint-disable-next-line no-restricted-properties
const { PI, round, log, max, min, pow, sin, atan, exp } = Math;

const PRIMARY_DATA_SOURCE = 'primary';
const DATA_SOURCES = 'data_sources';
const OUTPUT_MODE = 'output_mode';
const MAP_FILTER = 'mapping_filter';
const MAP_FILTER_CENTER = 'mapping_filter.center';
const MAP_FILTER_ZOOM = 'mapping_filter.zoom';

const dataSourceSetting = (dataSource, setting) => (
    `data_sources.${dataSource}.${setting}`
);

const dataSourceParam = (dataSource, param) => (
    dataSourceSetting(dataSource, `params.${param}`)
);

const getDataSourceSetting = (vizConfig, dataSource, setting) => (
    vizConfig[dataSourceSetting(dataSource, setting)]
);

const getDataSourceParam = (vizConfig, dataSource, param) => (
    vizConfig[dataSourceParam(dataSource, param)]
);

export const normalizeValueInList = (...list) => value => (
    list.indexOf(value) > -1 ? value : null
);

export const normalizeIntegerValue = value => (
    isInteger(value) ? value : null
);

const DATA_PARAMS = [
    { name: 'output_mode', normalize: normalizeValueInList('json_cols', 'json_rows', 'json') },
    { name: 'sort_key', output: 'sortKey' },
    { name: 'sort_direction', output: 'sortDirection', normalize: normalizeValueInList('asc', 'desc') },
    { name: 'count', normalize: normalizeIntegerValue },
    { name: 'offset', normalize: normalizeIntegerValue },
    { name: 'search' },
];

/**
 * Replace tokens in the given data_params setting of a visualization. Tokens are specified in the form
 * $token_name$ or $token_name:<default_value>$
 *
 * @param value {String} the token template string
 * @param variables {Object}
 * @throws an error if the token template refers to variables that are not contained in the variables parameter and
 *         do not have a default value.
 * @returns {String} the fully resolved setting value
 */
export function replaceTokens(value, variables) {
    const variablePattern = /\$([^$]+)\$/g;

    if (value) {
        return value.replace(variablePattern, (match, token) => {
            const [variableName, ...altVariables] = token.split(':');
            if (!_.has(variables, variableName)) {
                if (altVariables.length > 1) {
                    const matchVariable = altVariables.slice(0, -1).find(v => variables[v]);
                    if (matchVariable) {
                        return variables[matchVariable];
                    }
                }
                const defaultValue = altVariables.slice(-1)[0];
                if (defaultValue != null) {
                    return defaultValue;
                }
                throw new Error(`Missing variable ${variableName}`);
            }
            return variables[variableName];
        });
    }

    return null;
}

/**
 * Project the given geo coordinates at the given zoom level
 * according to the EPSG:3857 coordinate reference system
 *
 * @param lat {number}
 * @param lng {number}
 * @param zoom {number}
 * @returns {{x: number, y: number}}
 */
export const latLngToPoint = ({ lat, lng }, zoom) => {
    const scale = 256 * pow(2, zoom);
    const d = PI / 180;
    const a = 0.5 / (PI);
    const maxLat = 85.0511287798; // Maximum latitude (spherical mercator)
    const s = sin(max(min(maxLat, lat), -maxLat) * d);
    return {
        x: scale * ((a * lng * d) + 0.5),
        y: scale * (((-a) * ((log((1 + s) / (1 - s))) / 2)) + 0.5),
    };
};

/**
 * Translate the given Point (x,y) at the given zoom level to geo coordinates
 * according to the EPSG:3857 coordinate reference system
 *
 * @param x {number}
 * @param y {number}
 * @param zoom {number}
 * @returns {{lat: number, lng: number}}
 */
export const pointToLatLng = ({ x, y }, zoom) => {
    const scale = 256 * pow(2, zoom);
    const d = 180 / PI;
    const a = 0.5 / (PI);
    return {
        lat: ((2 * atan(exp(((y / scale) - 0.5) / (-a)))) - (PI / 2)) * d,
        lng: ((((x / scale) - 0.5) / a) * d),
    };
};

/**
 * Trim the map bounds
 *
 * @param north {number}
 * @param east {number}
 * @param south {number}
 * @param west {number}
 * @returns {{south: number, north: number, east: number, west: number}}
 */
export const normalizeMapBounds = ({ north, east, south, west }) => {
    const clipLeft = lng => lng + (lng < -180 ? 360 : 0);
    const clipRight = lng => lng - (lng > 180 ? 360 : 0);
    const clip = lng => clipRight(clipLeft(lng));
    const e = (east - west) < 360 ? clip(east % 360) : 180;
    const w = (east - west) < 360 ? clip(west % 360) : -180;
    return {
        south: max(-90, min(90, south)),
        north: max(max(-90, min(90, south)), min(90, north)),
        east: e < w && e <= -w ? 360 : e,
        west: e < w && w > -w ? w - 360 : w,
    };
};

/**
 * Add variables for the bounds of a map to the set of available variables. Added variables are:
 * $north$, $east$, $south$ and $west$ and represent the latitude/longitude values of the map edges.
 * The bounds are calculated based on the settings retrieved data_params.mapping_filter.center and
 * data_params.mapping_filter.zoom and the given width/height of the map container (in pixels).
 * The bounds are calculated for a web mercator projection (EPSG:3857), which popular map components
 * (such as leaflet and google maps) use.
 *
 * @param dataSource {string}
 * @param variables {*} existing set of variables
 * @param vizConfig {*}
 * @param width {number} container width in pixels
 * @param height {number} container height in pixels
 * @returns {*} an extended set of variables containing the map bounds
 */
export function applyMappingFilter(dataSource, variables, vizConfig, { width, height }) {
    const mapCenterTmpl = getDataSourceSetting(vizConfig, dataSource, MAP_FILTER_CENTER);
    const mapFilterZoomTmpl = getDataSourceSetting(vizConfig, dataSource, MAP_FILTER_ZOOM);
    const [, lat, lng] = replaceTokens(mapCenterTmpl, variables).match(/^\((.+?),(.+?)\)/);
    const zoom = +(normalizeIntegerValue(replaceTokens(mapFilterZoomTmpl, variables)) || 0);
    const center = latLngToPoint({ lat: +lat, lng: +lng }, zoom);
    const hw = (width / 2);
    const hh = (height / 2);
    const { lat: north, lng: west } = pointToLatLng({ x: round(center.x - hw), y: round(center.y - hh) }, zoom);
    const { lat: south, lng: east } = pointToLatLng({ x: round(center.x + hw), y: round(center.y + hh) }, zoom);
    return Object.assign({}, variables, normalizeMapBounds({ north, west, south, east }));
}


/**
 * Generates the initial data fetch parameters for a visualization data source based on
 * the settings in visualizations.conf
 *
 * @param dataSource {string} name of the data source
 * @param vizConfig settings from visualizations.conf
 * @param reportConfig the current report configuration
 * @param globalConfig config settings from web.conf
 * @param runtimeConfig container dimensions (width and height) of the visualization
 * @returns {*} generated data params (without prefix)
 */
export function generateDataSourceParams(dataSource, vizConfig, reportConfig, globalConfig = {}, runtimeConfig = {}) {
    if (vizConfig && dataSourceParam(dataSource, 'output_mode') in vizConfig) {
        const { width, height } = runtimeConfig;
        const result = {};
        let variables = Object.assign({}, globalConfig, reportConfig);

        if (normalizeBoolean(getDataSourceSetting(vizConfig, dataSource, MAP_FILTER), { default: false })) {
            variables = applyMappingFilter(dataSource, variables, vizConfig, { width, height });
        }

        DATA_PARAMS.forEach(({ name, output, normalize = x => x }) => {
            let value = getDataSourceParam(vizConfig, dataSource, name);
            value = replaceTokens(value, variables);
            if (value != null) {
                value = normalize(value);
                if (value) {
                    result[output || name] = value;
                }
            }
        });

        result.show_metadata = 'true';
        return result;
    }

    // Visualization has no configured data params
    return null;
}

/**
 * DEPRECATED: Returns initial fetch params for the primary data source of the given visualization config
 * @see generateDataSourceParams()
 */
export function generateDataParams(vizConfig, reportConfig, globalConfig, runtimeConfig) {
    return generateDataSourceParams(PRIMARY_DATA_SOURCE, vizConfig, reportConfig, globalConfig, runtimeConfig);
}

/**
 * Return a list of data source types supported by the visualization
 *
 * @param vizConfig
 * @returns {Array} array of strings, representing the data source types supported by the visualization
 */
export function getDataSourceTypes(vizConfig) {
    const value = vizConfig[DATA_SOURCES] || PRIMARY_DATA_SOURCE;
    return value.trim().split(/\s*,\s*/g);
}

/**
 * Determines whether the given visualization config supports the given data source type
 * @param vizConfig {*} visualization config
 * @param dataSource {string} data source type
 * @returns {boolean} true if the data source type is supported
 */
export function supportsDataSource(vizConfig, dataSource) {
    return getDataSourceTypes(vizConfig).indexOf(dataSource) > -1;
}

/**
 * Determine if the given visualization needs runtime config (such as DOM container dimensions)
 * in order to figure out the initial fetch params
 *
 * @param vizConfig {*}
 * @returns {boolean} true if the visualization requires runtime config in order to determine the initial fetch params
 */
export const needsRuntimeConfig = vizConfig => (
    vizConfig && getDataSourceTypes(vizConfig).some(dataSource => (
        vizConfig && dataSourceParam(dataSource, OUTPUT_MODE) in vizConfig &&
        normalizeBoolean(getDataSourceSetting(vizConfig, dataSource, MAP_FILTER), { default: false })
    ))
);
