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
        var Sort = BaseCommand.extend({
            _displayName: _('Sort').t(),
            _placeholderSPL: 'sort',

            initialize: function(attributes, options) {
                BaseCommand.prototype.initialize.apply(this, arguments);

                // Must migrate requiredColumns to editorValues for pre-Kimono tables containing Sort
                this.setInitialState();
            },

            // Set the order to the default one passed in on every required column
            setInitialState: function(initialStateOptions) {
                initialStateOptions = initialStateOptions || {};

                // As of Kimono, requiredColumns should only contain guids, and not attrs like 'order'
                // (which is stored in editorValues) - so we do some migration and cleanup here.
                if (!this.editorValues.length) {
                    this.requiredColumns.each(function(requiredColumn) {
                        this.editorValues.add(
                            {
                                columnGuid: requiredColumn.id,
                                order: requiredColumn.get('order') || initialStateOptions.order
                            }
                        );
                        requiredColumn.unset('order', { silent: true });
                    }, this);
                }
            },

            defaults: function() {
                return Sort.getDefaults();
            },

            validation: {
                spl: 'validateSPL'
            },

            validateSPL: function(value, attr, option) {
                var errorString = this.validateForTypes(this.getWhitelistedTypes()),
                    editorValue, i;
                if (!this.hasValidRequiredColumn()) {
                    return _('Add one or more fields.').t();
                }
                if (errorString) {
                    return errorString;
                }
                for (i = 0; i < this.editorValues.length; i++) {
                    editorValue = this.editorValues.at(i);

                    if (_.isUndefined(this.getFieldNameFromGuid(editorValue.get('columnGuid')))) {
                        return _('One or more fields to sort have been removed.').t();

                    }
                }
            },

            generateSPL: function(options) {
                options = options || {};

                if (!options.skipValidation && !this.isValid(true)) {
                    throw new Error('Sort must be in a valid state before you can generate SPL.');
                }

                // Add '-' prefix to field names if order is descending
                // Could add '+' if order is ascending, but leaving it out as it isn't necessary
                var fieldStringArray = this.editorValues.map(function(editorValue) {
                    return (editorValue.get('order') === 'descending' ? '-' : '') + this.getFieldNameFromGuid(editorValue.get('columnGuid'), { doubleQuoteWrap: true });
                }.bind(this));

                return 'sort ' + fieldStringArray.join(', ');
            },

            isDirty: function(commandPristine) {
                return BaseCommand.prototype.isDirty.call(this, commandPristine, { ignoreSortId: true });
            }

        }, {
            blacklist: [
                { selection: BaseCommand.SELECTION.TABLE },
                { selection: BaseCommand.SELECTION.CELL },
                {
                    selection: BaseCommand.SELECTION.COLUMN,
                    types: [ ColumnModel.TYPES._RAW ]
                },
                { selection: BaseCommand.SELECTION.TEXT },
                {
                    selection: BaseCommand.SELECTION.MULTICOLUMN,
                    types: [ ColumnModel.TYPES._RAW ]
                }
            ],
            getDefaults: function(overrides) {
                return _.defaults((overrides || {}), {
                    type: BaseCommand.SORT,
                    isComplete: true
                }, BaseCommand.getDefaults());
            }
        });

        return Sort;
    }
);
