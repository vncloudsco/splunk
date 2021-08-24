/* eslint-disable max-len */
import _ from 'underscore';
import DashboardElementReport from 'models/dashboard/DashboardElementReport';
import {
    CHART,
    SINGLE_VALUE,
    MAP,
    CUSTOM_VIZ,
    EVENT,
    TABLE,
} from 'controllers/dashboard/helpers/vizTypeNames';

export const chartTokens = [
    {
        token: '$click.name$',
        description: _('X-axis field or category name for the clicked location. Not available if the user clicks the chart legend.').t(),
    },
    {
        token: '$click.value$',
        description: _('X-axis field or category value for the clicked location. Not available if the user clicks the chart legend.').t(),
    },
    {
        token: '$click.name2$',
        description: _('Y-axis field or series name for the clicked location. Not available if the user clicks the chart legend.').t(),
    },
    {
        token: '$click.value2$',
        description: _('Y-axis field or series value for the clicked location. Not available if the user clicks the chart legend.').t(),
    },
    {
        token: '$row.<fieldname>$',
        description: _('Access any y-axis field value corresponding to the clicked location x-axis. Not available if the user clicks the chart legend.').t(),
    },
    {
        token: '$row.<x-axis-name>$',
        description: _('Access any x-axis field value corresponding to the clicked location. Not available if the user clicks the chart legend.').t(),
    },
    {
        token: '$earliest$',
        description: _('Earliest time for the clicked chart segment. If not applicable, uses the earliest time for the search.').t(),
    },
    {
        token: '$latest$',
        description: _('Latest time for the clicked chart segment. If not applicable, uses the latest time for the search.').t(),
    },
    {
        token: '$trellis.name$',
        description: _('Trellis layout split field name.').t(),
    },
    {
        token: '$trellis.value$',
        description: _('Trellis layout split field value for the clicked segment.').t(),
    },
    {
        token: '$trellis.split.<fieldname>$',
        description: _('Trellis layout aggregation or field value for the clicked visualization segment.').t(),
    },
];

export const eventTokens = [
    {
        token: '$click.name$',
        description: _('Field name for the clicked element in the event list.').t(),
    },
    {
        token: '$click.value$',
        description: _('Field value for the clicked element in the event list.').t(),
    },
    {
        token: '$click.name2$',
        description: _('Identical to click.name.').t(),
    },
    {
        token: '$click.value2$',
        description: _('Identical to click.value.').t(),
    },
    {
        token: '$row.<fieldname>$',
        description: _('Access any field value in the clicked event.').t(),
    },
    {
        token: '$earliest$',
        description: _('Earliest time for the clicked event. Equivalent to _time field value.').t(),
    },
    {
        token: '$latest$',
        description: _('Latest time for the clicked event. Equivalent to one second after the _time field value.').t(),
    },
];

export const mapTokens = [
    {
        token: '$click.name$',
        description: _('Field name for the clicked location. If multiple fields are associated with the location, uses the first field.').t(),
    },
    {
        token: '$click.value$',
        description: _('Field value for the clicked location. If multiple fields are associated with the location, uses the first field.').t(),
    },
    {
        token: '$click.name2$',
        description: _('Same as click.name.').t(),
    },
    {
        token: '$click.value2$',
        description: _('Same as click.value.').t(),
    },
    {
        token: '$click.lat.name$',
        description: _('For cluster maps: latitude field name for the clicked location.').t(),
    },
    {
        token: '$click.lat.value$',
        description: _('For cluster maps: latitude field value for the clicked location.').t(),
    },
    {
        token: '$click.lon.name$',
        description: _('For cluster maps: longitude field name for the clicked location.').t(),
    },
    {
        token: '$click.lon.value$',
        description: _('For cluster maps: longitude field value for the clicked location.').t(),
    },
    {
        token: '$click.bounds.<orientation>$',
        description: _('For cluster maps: south, west, north, or east outer boundary for the clicked location. For example, use $click.bounds.east$ to get the eastern outer boundary.').t(),
    },
    {
        token: '$row.<fieldname>$',
        description: _('Access field values related to the clicked location. Check the Statistics tab for available fields.').t(),
    },
    {
        token: '$earliest$',
        description: _('Earliest time for the search generating the map.').t(),
    },
    {
        token: '$latest$',
        description: _('Latest time for the search generating the map.').t(),
    },
    {
        token: '$trellis.name$',
        description: _('For choropleth maps: trellis layout split field name.').t(),
    },
    {
        token: '$trellis.value$',
        description: _('For choropleth maps: trellis layout split field value for the clicked segment.').t(),
    },
    {
        token: '$trellis.split.<fieldname>$',
        description: _('For choropleth maps: trellis layout aggregation or field value for the clicked visualization segment.').t(),
    },
];

export const singleValueTokens = [
    {
        token: '$click.name$',
        description: _('Name of the field that the single value represents.').t(),
    },
    {
        token: '$click.value$',
        description: _('Field value that the single value represents.').t(),
    },
    {
        token: '$click.name2$',
        description: _('Same as click.name.').t(),
    },
    {
        token: '$click.value2$',
        description: _('Same as click.value.').t(),
    },
    {
        token: '$row.<fieldname>$',
        description: _('Access any field value from the Statistics table row for the single value.').t(),
    },
    {
        token: '$earliest$',
        description: _('Earliest time of the search driving the single value visualization.').t(),
    },
    {
        token: '$latest$',
        description: _('Latest time of the search driving the single value visualization.').t(),
    },
    {
        token: '$trellis.name$',
        description: _('Trellis layout split field name.').t(),
    },
    {
        token: '$trellis.value$',
        description: _('Trellis layout split field value for the clicked segment.').t(),
    },
    {
        token: '$trellis.split.<fieldname>$',
        description: _('Trellis layout aggregation or field value for the clicked visualization segment.').t(),
    },
];

export const tableTokens = [
    {
        token: '$click.name$',
        description: _('Leftmost field (column) name in the table.').t(),
    },
    {
        token: '$click.value$',
        description: _('Leftmost field (column) value in the clicked table row.').t(),
    },
    {
        token: '$click.name2$',
        description: _('Clicked field (column) name.').t(),
    },
    {
        token: '$click.value2$',
        description: _('Clicked field (column) value. Captures the specific table cell value that users click.').t(),
    },
    {
        token: '$row.<fieldname>$',
        description: _('Access any field (column) value from the clicked table row.').t(),
    },
    {
        token: '$earliest$',
        description: _('Earliest time of the clicked table row, or if not applicable, the earliest time of the search.').t(),
    },
    {
        token: '$latest$',
        description: _('Latest time of the clicked table row, or if not applicable, the latest time of the search.').t(),
    },
];

export const customVizTokens = [
    // TODO: figure out whether custom viz has tokens
];

export const getTokens = (reportModel) => {
    const type = DashboardElementReport.getVizType(reportModel);
    switch (type) {
        case CHART:
            return chartTokens;
        case SINGLE_VALUE:
            return singleValueTokens;
        case MAP:
            return mapTokens;
        case CUSTOM_VIZ:
            return customVizTokens;
        case EVENT:
            return eventTokens;
        case TABLE:
            return tableTokens;
        default:
            return [];
    }
};