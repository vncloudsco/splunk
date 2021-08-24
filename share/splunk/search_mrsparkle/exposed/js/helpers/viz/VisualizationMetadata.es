import { normalizeBoolean } from 'util/general_utils';
import { isInteger } from 'util/math_utils';
import { isCoreVisualization } from './CoreVisualizations';

export function getCoreVizMatchConfig(vizConfig) {
    const coreType = vizConfig.get('core.type');
    const result = {
        'display.general.type': coreType,
    };
    if (coreType === 'visualizations') {
        const vizType = vizConfig.get('core.viz_type');
        result['display.visualizations.type'] = vizType;
        if (vizType === 'charting') {
            result['display.visualizations.charting.chart'] = vizConfig.get('core.charting_type');
        } else if (vizType === 'mapping') {
            result['display.visualizations.mapping.type'] = vizConfig.get('core.mapping_type');
        }
    }
    return result;
}

export function getExternalVizMatchConfig(vizId) {
    return {
        'display.general.type': 'visualizations',
        'display.visualizations.type': 'custom',
        'display.visualizations.custom.type': vizId,
    };
}

const normalizeInt = (stringValue, defaultValue) => (
    isInteger(stringValue) ? (+stringValue) : defaultValue
);

const normalizeIntList = (stringValue, defaultValue) => {
    if (stringValue && stringValue.trim()) {
        return stringValue.split(',').map(s => s.trim()).map(normalizeInt);
    }
    return defaultValue;
};

export function getSizeConfig(vizConfig) {
    return {
        resizable: true,
        minHeight: normalizeInt(vizConfig.get('min_height'), 0),
        maxHeight: normalizeInt(vizConfig.get('max_height'), 1000),
        minWidth: normalizeInt(vizConfig.get('min_width')),
        maxWidth: normalizeInt(vizConfig.get('max_width')),
        defaultHeight: normalizeInt(vizConfig.get('default_height'), 250),
        defaultWidth: normalizeInt(vizConfig.get('default_width')),
        defaultTrellisHeight: normalizeInt(vizConfig.get('trellis_default_height')),
        trellisMinWidths: normalizeIntList(vizConfig.get('trellis_min_widths')),
        trellisPerRow: normalizeIntList(vizConfig.get('trellis_per_row')),
    };
}

export function getCoreSizeConfig(vizConfig) {
    return {
        heightAttribute: vizConfig.get('core.height_attribute'),
    };
}

export function getExternalSizeConfig(/* vizConfig */) {
    return {
        heightAttribute: 'display.visualizations.custom.height',
    };
}


export function getRecommendations(vizConfig) {
    const value = vizConfig.get('core.recommend_for');
    return value && value.trim() ? value.trim().split(/\s*,\s*/g) : undefined;
}

export function getSupportFlags(vizConfig) {
    return {
        trellis: normalizeBoolean(vizConfig.get('supports_trellis'), { default: false }),
        drilldown: normalizeBoolean(vizConfig.get('supports_drilldown'), { default: false }),
        export: normalizeBoolean(vizConfig.get('supports_export'), { default: false }),
    };
}

export function getExternalVizRegistrationData(vizConfig, vizId) {
    return {
        categories: ['external'],
        icon: 'external-viz',
        preview: 'preview.png',
        matchConfig: getExternalVizMatchConfig(vizId),
        order: Number.MAX_SAFE_INTEGER,
    };
}

export function getCoreVizRegistrationData(vizConfig) {
    return {
        icon: vizConfig.get('core.icon'),
        preview: vizConfig.get('core.preview_image'),
        matchConfig: getCoreVizMatchConfig(vizConfig),
        recommendFor: getRecommendations(vizConfig),
        order: normalizeInt(vizConfig.get('core.order')),
    };
}

export function getVisualizationMetadata(vizModel) {
    const isCoreViz = isCoreVisualization(vizModel);
    const appName = vizModel.entry.acl.get('app');
    const vizName = vizModel.entry.get('name');
    const vizId = isCoreViz ? vizName : `${appName}.${vizName}`;
    const vizConfig = vizModel.entry.content;
    const supportFlags = getSupportFlags(vizConfig);
    const disabled = normalizeBoolean(vizConfig.get('disabled'), { default: false });

    return Object.assign({
        id: vizId,
        vizName,
        appName,
        disabled,
        label: vizConfig.get('label'),
        description: vizConfig.get('description'),
        searchHint: vizConfig.get('search_fragment') || undefined,
        isSelectable: (!disabled) && normalizeBoolean(vizConfig.get('allow_user_selection'), { default: true }),
        isSplittable: supportFlags.trellis,
        isCore: isCoreViz,
        isExternal: !isCoreViz,
        supports: supportFlags,
        size: Object.assign(
            getSizeConfig(vizConfig),
            isCoreViz ? getCoreSizeConfig(vizConfig) : getExternalSizeConfig(vizConfig),
        ),
        config: vizConfig.toJSON(),
        formatterHtml: vizConfig.get('formatter'),
    }, isCoreViz ?
        getCoreVizRegistrationData(vizConfig) :
        getExternalVizRegistrationData(vizConfig, vizId));
}
