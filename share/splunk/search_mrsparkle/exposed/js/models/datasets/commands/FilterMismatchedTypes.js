define(
    [
        'jquery',
        'underscore',
        'models/datasets/commands/Base',
        'models/datasets/Column'
    ],
    function(
        $,
        _,
        BaseCommand,
        ColumnModel
    ) {
        var FilterMismatchedTypes = BaseCommand.extend({
            _displayName: _("Remove Type Mismatches").t(),
            _placeholderSPL: BaseCommand.WHERE,
            _advancedCommand: BaseCommand.WHERE,
            isSearchPoint: true,

            initialize: function(attributes, options) {
                BaseCommand.prototype.initialize.apply(this, arguments);
            },

            validation: {
                spl: 'validateSPL'
            },

            defaults: function() {
                return FilterMismatchedTypes.getDefaults();
            },

            validateSPL: function (value, attr, options) {
                var errorString = this.validateForTypes(this.getWhitelistedTypes());
                
                if (!this.hasValidRequiredColumn()) {
                    return _('Select a field.').t();
                }
                
                if (errorString) {
                    return errorString;
                }
            },

            generateSPL: function(options) {
                options = options || {};
                
                if (!options.skipValidation && !this.isValid(true)) {
                    throw new Error('FilterMismatchedTypes must be in a valid state before you can generate SPL.');
                }

                return 'where ' + this.getExpression();
            },

            getAdvancedCommandAttributes: function() {
                return {
                    expression: this.getExpression()
                };
            },
            
            getExpression: function() {
                var requiredColumnId = this.hasValidRequiredColumn() ? this.requiredColumns.first().id : undefined,
                    basicExpression = 'mvcount(mvfilter()) >= 1',
                    fieldNameSingleQuoted,
                    column,
                    columnType;
                    
                if (!requiredColumnId) {
                    return basicExpression;
                }
                
                fieldNameSingleQuoted = this.getFieldNameFromGuid(this.requiredColumns.first().id, { singleQuoteWrap: true });
                column = this.columns.get(requiredColumnId);
                columnType = column.get('type');
                
                if (columnType === ColumnModel.TYPES.NUMBER) {
                    return 'mvcount(mvfilter(isnum(' + fieldNameSingleQuoted + '))) >= 1';
                }
                
                if (columnType === ColumnModel.TYPES.BOOLEAN) {
                    return 'mvcount(mvfilter(match(' + fieldNameSingleQuoted + ', "^true$|^false$"))) >= 1';
                }
                
                if (columnType === ColumnModel.TYPES.IPV4) {
                    return 'mvcount(mvfilter(match(' + fieldNameSingleQuoted + ', "^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$"))) >= 1';
                }
                
                if (columnType === ColumnModel.TYPES.EPOCH_TIME) {
                    return 'mvcount(mvfilter(match(' + fieldNameSingleQuoted + ', "^\\d+\\.?\\d{0,3}$|^\\d*\\.\\d{0,3}$"))) >= 1';
                }
                
                return basicExpression;
            }
        }, {
            blacklist: [
                { selection: BaseCommand.SELECTION.MULTICOLUMN },
                { selection: BaseCommand.SELECTION.TABLE },
                { selection: BaseCommand.SELECTION.CELL },
                { selection: BaseCommand.SELECTION.COLUMN,
                    types: [ ColumnModel.TYPES._RAW, ColumnModel.TYPES._TIME, ColumnModel.TYPES.STRING ]
                },
                { selection: BaseCommand.SELECTION.TEXT }
            ],
            getDefaults: function(overrides) {
                return _.defaults((overrides || {}), {
                    type: BaseCommand.FILTER_MISMATCHED_TYPES,
                    isComplete: true
                }, BaseCommand.getDefaults());
            }
        });
        
        return FilterMismatchedTypes;
    }
);