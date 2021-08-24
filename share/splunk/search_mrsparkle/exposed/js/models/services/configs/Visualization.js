define([
        'jquery',
        'underscore',
        'models/SplunkDBase',
        'util/splunkd_utils',
        'util/general_utils'
    ],
    function(
        $,
        _,
        BaseModel,
        splunkdUtils,
        generalUtils
    ) {
        var VisualizationModel = BaseModel.extend({
            url: 'data/ui/visualizations',

            isDisabled: function() {
                return generalUtils.normalizeBoolean(this.entry.content.get('disabled'), { 'default': false });
            },

            isSelectable: function() {
                return (
                    !this.isDisabled() &&
                    generalUtils.normalizeBoolean(this.entry.content.get('allow_user_selection'), { 'default': true })
                );
            },

            isSplittable: function() {
                return (
                    !this.isDisabled() &&
                    generalUtils.normalizeBoolean(this.entry.content.get('supports_trellis'), { 'default': false })
                );
            }
        },
        {
            createFromCustomTypeAndContext: function(customType, context) {
                var appAndVizName = customType.split('.'),
                    id = splunkdUtils.fullpath(
                        VisualizationModel.prototype.url + '/' + appAndVizName[1],
                        context
                    );

                return new VisualizationModel({ id: id });
            },

            ENABLED_FILTER: 'disabled=0',
            SELECTABLE_FILTER: 'disabled=0 AND allow_user_selection=1'
        });

        return VisualizationModel;
    }
);
