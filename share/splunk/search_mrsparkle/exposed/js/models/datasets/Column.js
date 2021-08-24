define(
    [
        'jquery',
        'underscore',
        'models/Base',
        'util/general_utils'
    ],
    function(
        $,
        _,
        BaseModel,
        generalUtils
    ) {
        var TYPES = {
                // Generic Types
                EPOCH_TIME: 'epochTime',
                NUMBER: 'number',
                STRING: 'string',
                BOOLEAN: 'boolean',
                IPV4: 'ipv4',

                // Unique Data Types
                // - Users cannot assign these types to other fields
                // - Users cannot change the types of these fields
                // - If field is duplicated, assign 'epoch' or 'string' generic types
                _RAW: 'raw',
                _TIME: 'timestamp'
            },
            WIDTH_SELECT_ALL = 60,
            WIDTH_DEFAULT = 200,
            WIDTH_DEFAULT_RAW = 600,
            ICONS = {},
            TYPE_LABELS = {};

        ICONS[TYPES.EPOCH_TIME] = 'clock';
        ICONS[TYPES.NUMBER] = 'number';
        ICONS[TYPES.STRING] = 'string';
        ICONS[TYPES.BOOLEAN] = 'boolean';
        ICONS[TYPES.IPV4] = 'ipv4';
        ICONS[TYPES._RAW] = 'greater';
        ICONS[TYPES._TIME] = 'clock';

        TYPE_LABELS[TYPES.EPOCH_TIME] = _('Epoch Time').t();
        TYPE_LABELS[TYPES.NUMBER] = _('Number').t();
        TYPE_LABELS[TYPES.STRING] = _('String').t();
        TYPE_LABELS[TYPES.BOOLEAN] = _('Boolean').t();
        TYPE_LABELS[TYPES.IPV4] = _('IPv4').t();
        TYPE_LABELS[TYPES._RAW] = _('Raw').t();
        TYPE_LABELS[TYPES._TIME] = _('Timestamp').t();

        return BaseModel.extend({
            initialize: function(attributes, options) {
                BaseModel.prototype.initialize.apply(this, arguments);
            },

            defaults: function() {
                return {
                    id: generalUtils.generateUUID(),
                    type: TYPES.STRING
                };
            },

            validation: {
                name: function(value) {
                    if (!value) {
                        throw new Error('You cannot set on a column without a name.');
                    }
                }
            },

            sync: function(method, model, options) {
                throw new Error('sync not allowed for the Column model');
            },

            isTouchedByComparison: function(comparisonColumn, options) {
                options = options || {};
                var currentName = options.previousColumnName || this.get('name'),
                    comparisonName = comparisonColumn.get('name');

                if (this.id !== comparisonColumn.id) {
                    throw new Error('You cannot compare columns with different ids!');
                }

                return (currentName !== comparisonName);
            },

            isEpochTime: function() {
                var type = this.get('type');
                return ((type === TYPES.EPOCH_TIME) || (type === TYPES._TIME));
            },

            isSplunkTime: function() {
                var type = this.get('type');
                return (type === TYPES._TIME);
            },

            getWidth: function() {
                var customSetWidth = parseFloat(this.get('display.width'));

                if (customSetWidth && !_.isNaN(customSetWidth)) {
                    return customSetWidth;
                } else {
                    return this.get('type') === TYPES._RAW ? WIDTH_DEFAULT_RAW : WIDTH_DEFAULT;
                }
            }
        }, {
            TYPES: TYPES,
            ICONS: ICONS,
            TYPE_LABELS: TYPE_LABELS,
            WIDTH_SELECT_ALL: WIDTH_SELECT_ALL,
            WIDTH_DEFAULT: WIDTH_DEFAULT,
            WIDTH_DEFAULT_RAW: WIDTH_DEFAULT_RAW
        });
    }
);
