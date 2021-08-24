import lineChartEditorSchema from 'views/shared/jschart/vizeditorschemas/line_chart';
import areaChartEditorSchema from 'views/shared/jschart/vizeditorschemas/area_chart';
import columnChartEditorSchema from 'views/shared/jschart/vizeditorschemas/column_chart';
import barChartSchema from 'views/shared/jschart/vizeditorschemas/bar_chart';
import pieChartSchema from 'views/shared/jschart/vizeditorschemas/pie_chart';
import scatterChartSchema from 'views/shared/jschart/vizeditorschemas/scatter_chart';
import bubbleChartSchema from 'views/shared/jschart/vizeditorschemas/bubble_chart';
import singleValueSchema from 'views/shared/singlevalue/viz_editor_schema';
import gaugeSchema from 'views/shared/jschart/vizeditorschemas/gauge';
import markerMapSchema from 'views/shared/map/vizeditorschemas/marker_map';
import choroplethMapSchema from 'views/shared/map/vizeditorschemas/choropleth_map';
import resultsTableSchema from 'views/shared/results_table/viz_editor_schema';
import eventsViewerSchema from 'views/shared/eventsviewer/viz_editor_schema';

import chartPivotSchemas from 'views/shared/jschart/pivot_schemas';
import singleValuePivotSchema from 'views/shared/singlevalue/pivot_schema';

import LazyJSChart from 'views/shared/jschart/LazyJSChart';
import LazySingleValue from 'views/shared/singlevalue/LazySingleValue';
import LazyMap from 'views/shared/map/LazyMap';
import LazyResultsTable from 'views/shared/results_table/LazyResultsTable';

const CORE_VIZ_SCHEMAS = {
    line: {
        editorSchema: lineChartEditorSchema,
        pivotSchema: chartPivotSchemas.LINE,
        factory: LazyJSChart,
    },
    area: {
        editorSchema: areaChartEditorSchema,
        pivotSchema: chartPivotSchemas.AREA,
        factory: LazyJSChart,
    },
    column: {
        editorSchema: columnChartEditorSchema,
        pivotSchema: chartPivotSchemas.COLUMN,
        factory: LazyJSChart,
    },
    bar: {
        factory: LazyJSChart,
        pivotSchema: chartPivotSchemas.BAR,
        editorSchema: barChartSchema,
    },
    pie: {
        factory: LazyJSChart,
        editorSchema: pieChartSchema,
        pivotSchema: chartPivotSchemas.PIE,
    },
    scatter: {
        factory: LazyJSChart,
        editorSchema: scatterChartSchema,
        pivotSchema: chartPivotSchemas.SCATTER,
    },
    bubble: {
        factory: LazyJSChart,
        editorSchema: bubbleChartSchema,
        pivotSchema: chartPivotSchemas.BUBBLE,
    },
    singlevalue: {
        factory: LazySingleValue,
        pivotSchema: singleValuePivotSchema,
        editorSchema: singleValueSchema,
    },
    radialGauge: {
        factory: LazyJSChart,
        pivotSchema: chartPivotSchemas.GAUGE,
        editorSchema: gaugeSchema,
    },
    fillerGauge: {
        factory: LazyJSChart,
        pivotSchema: chartPivotSchemas.GAUGE,
        editorSchema: gaugeSchema,
    },
    markerGauge: {
        factory: LazyJSChart,
        editorSchema: gaugeSchema,
        pivotSchema: chartPivotSchemas.GAUGE,
    },
    mapping: {
        factory: LazyMap,
        editorSchema: markerMapSchema,
    },
    choropleth: {
        factory: LazyMap,
        editorSchema: choroplethMapSchema,
    },
    statistics: {
        factory: LazyResultsTable,
        editorSchema: resultsTableSchema,
    },
    events: {
        editorSchema: eventsViewerSchema,
    },
};


export function isCoreVisualization(vizModel) {
    return vizModel.entry.acl.get('app') === 'system' && vizModel.entry.get('name') in CORE_VIZ_SCHEMAS;
}

export function getCoreVizConfig(coreVizId) {
    if (!(coreVizId in CORE_VIZ_SCHEMAS)) {
        throw new Error(`Core visualization ${JSON.stringify(coreVizId)} not found`);
    }
    return CORE_VIZ_SCHEMAS[coreVizId];
}

export function getEditorSchema(coreVizId) {
    return getCoreVizConfig(coreVizId).editorSchema;
}

export function getPivotSchema(coreVizId) {
    return getCoreVizConfig(coreVizId).pivotSchema;
}

export function getFactory(coreVizId) {
    return getCoreVizConfig(coreVizId).factory;
}
