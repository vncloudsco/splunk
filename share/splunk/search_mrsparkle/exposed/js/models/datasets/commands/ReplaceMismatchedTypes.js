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
        var ReplaceMismatchedTypes = BaseCommand.extend({
            _displayName: _("Replace Type Mismatches With Null").t(),
            _placeholderSPL: "eval",
            _advancedCommand: BaseCommand.EVAL_EXISTING_FIELD,

            initialize: function(attributes, options) {
                BaseCommand.prototype.initialize.apply(this, arguments);
            },

            validation: {
                spl: 'validateSPL'
            },

            defaults: function() {
                return ReplaceMismatchedTypes.getDefaults();
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
                    throw new Error('ReplaceMismatchedTypes must be in a valid state before you can generate SPL.');
                }

                var requiredColumnGuid = this.requiredColumns.first().id,
                    fieldNameDoubleQuoted = this.getFieldNameFromGuid(requiredColumnGuid, { doubleQuoteWrap: true }),
                    expression = this.getExpression();

                return 'eval ' + fieldNameDoubleQuoted + ' = ' + expression;
            },

            getAdvancedCommandAttributes: function() {
                return {
                    expression: this.getExpression()
                };
            },

            getExpression: function() {
                var requiredColumnId = this.hasValidRequiredColumn() ? this.requiredColumns.first().id : undefined,
                    basicExpression = 'mvfilter()',
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
                    return 'mvfilter(isnum(' + fieldNameSingleQuoted + '))';
                }
                
                if (columnType === ColumnModel.TYPES.BOOLEAN) {
                    return 'mvfilter(match(' + fieldNameSingleQuoted + ', "^true$|^false$"))';
                }
                
                if (columnType === ColumnModel.TYPES.IPV4) {
                    return 'mvfilter(match(' + fieldNameSingleQuoted + ', "^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$"))';
                }
                
                if (columnType === ColumnModel.TYPES.EPOCH_TIME) {
                    return 'mvfilter(match(' + fieldNameSingleQuoted + ', "^\\d+\\.?\\d{0,3}$|^\\d*\\.\\d{0,3}$"))';
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
                    type: BaseCommand.REPLACE_MISMATCHED_TYPES,
                    isComplete: true
                }, BaseCommand.getDefaults());
            }
        });
        
        return ReplaceMismatchedTypes;
    }
);