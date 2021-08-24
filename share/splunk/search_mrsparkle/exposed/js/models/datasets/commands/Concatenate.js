define(
    [
        'jquery',
        'underscore',
        'models/datasets/commands/Base',
        'util/dataset_utils',
        'util/general_utils'
    ],
    function(
        $,
        _,
        BaseCommand,
        datasetUtils,
        generalUtils
    ) {
        var Concatenate = BaseCommand.extend({
            _displayName: _('Concatenate').t(),
            _placeholderSPL: 'eval',
            _advancedCommand: BaseCommand.EVAL,

            initialize: function(attributes, options) {
                BaseCommand.prototype.initialize.apply(this, arguments);
            },

            // Create an editor value for each requiredColumn
            setInitialState: function(initialStateOptions) {
                initialStateOptions = initialStateOptions || {};

                if (!this.editorValues.length) {
                    this.requiredColumns.each(function(requiredColumn) {
                        this.editorValues.add({ columnGuid: requiredColumn.id });
                    }, this);
                }
            },

            defaults: function() {
                return Concatenate.getDefaults();
            },

            validation: {
                spl: 'validateSPL',
                collisionFields: 'validateCollisionFields'
            },
    
            editorValueIsText: function(editorValue) {
                return _.isUndefined(editorValue.get('columnGuid'));
            },

            validateSPL: function(value, attr, option) {
                var newFieldName = this.get('newFieldName'),
                    invalidFieldMessage = this.validateFieldName(newFieldName),
                    i = 0,
                    editorValue;


                if (invalidFieldMessage) {
                    return invalidFieldMessage;
                }

                if (this.editorValues.length < 2) {
                    return _('Select at least two fields or text strings to concatenate.').t();
                }

                for (; i < this.editorValues.length; i++) {
                    editorValue = this.editorValues.at(i);

                    if (this.editorValueIsText(editorValue) && !editorValue.get('text').length) {
                        return _('One or more of your strings is empty.').t();
                    }

                    if (!this.editorValueIsText(editorValue) &&
                            _.isUndefined(this.getFieldNameFromGuid(editorValue.get('columnGuid')))) {
                        return _('One or more fields to concatenate have been removed.').t();
                    }
                }
            },

            generateSPL: function(options) {
                options = options || {};

                if (!options.skipValidation && !this.isValid(true)) {
                    throw new Error('Concatenate must be in a valid state before you can generate SPL.');
                }

                var newFieldName = this.get('newFieldName'),
                    expression = this.getExpression();

                return 'eval "' + newFieldName + '"=' + expression;
            },

            getAdvancedCommandAttributes: function() {
                return {
                    newFieldName: this.get('newFieldName'),
                    expression: this.getExpression()
                };
            },

            getExpression: function() {
                var text,
                    fieldName;

                return this.editorValues.map(function(editorValue) {
                    if (this.editorValueIsText(editorValue)) {
                        return '"' + datasetUtils.splEscape(editorValue.get('text') || '') + '"';
                    } else {
                        fieldName = this.getFieldNameFromGuid(editorValue.get('columnGuid'), { singleQuoteWrap: true }) || '\'\'';
                        // If you concatenate two fields, and one of the values in either field is null, the result
                        // is null. We don't want that, we just want the null to be treated as an empty string.
                        return 'if(isnull(' + fieldName + '), "", ' + fieldName + ')';
                    }
                }, this).join('.');
            },

            isDirty: function(commandPristine) {
                return BaseCommand.prototype.isDirty.call(this, commandPristine, { ignoreSortId: true });
            }
        }, {
            blacklist: [
                { selection: BaseCommand.SELECTION.CELL },
                { selection: BaseCommand.SELECTION.TABLE },
                { selection: BaseCommand.SELECTION.TEXT }
            ],
            getDefaults: function(overrides) {
                return _.defaults((overrides || {}), {
                    type: BaseCommand.CONCATENATE
                }, BaseCommand.getDefaults(overrides));
            }
        });

        return Concatenate;
    }
);
