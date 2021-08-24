define(
    [
        'underscore',
        'module',
        'views/table/resultscontainer/actionbar/actionmenus/BaseMenu',
        'models/datasets/Column',
        'models/datasets/commands/Base',
        'models/datasets/commands/ChangeCase',
        'models/datasets/commands/FillValues',
        'models/datasets/commands/Replace',
        'models/datasets/commands/ReplaceMismatchedTypes',
        'models/datasets/commands/EvalExistingField',
        'models/datasets/commands/Round',
        'models/datasets/commands/Bucket'
    ],
    function(
        _,
        module,
        BaseMenu,
        ColumnModel,
        BaseCommandModel,
        ChangeCaseModel,
        FillValuesModel,
        ReplaceModel,
        ReplaceMismatchedTypesModel,
        EvalExistingFieldModel,
        RoundModel,
        BucketModel
    ) {
        return BaseMenu.extend({
            moduleId: module.id,
            commandMenuItems: [
                {
                    className: 'clean-changecase',
                    label: _('Change Case...').t(),
                    commandConfigs: ChangeCaseModel.getDefaults()
                },
                {
                    className: 'clean-fill-values',
                    label: _('Fill Null or Empty Values...').t(),
                    commandConfigs: FillValuesModel.getDefaults()
                },
                {
                    className: 'clean-replace-values',
                    label: _('Replace Values...').t(),
                    commandConfigs: ReplaceModel.getDefaults(),
                    prepareOptions: function(commandConfigs) {
                        var options,
                            selectionType = this.model.table.entry.content.get('dataset.display.selectionType'),
                            selectionValue,
                            isText = false;

                        if (selectionType === BaseCommandModel.SELECTION.TEXT) {
                            selectionValue = this.model.table.entry.content.get('dataset.display.selectedText');
                            isText = true;
                        } else if (selectionType === BaseCommandModel.SELECTION.CELL) {
                            selectionValue = this.model.table.entry.content.get('dataset.display.selectedColumnValue');
                        }

                        options = {
                            selectionValue: selectionValue,
                            isText: isText
                        };

                        return options;
                    }
                },
                {
                     className: 'clean-round',
                     label: _('Round Values').t(),
                     commandConfigs: RoundModel.getDefaults()
                },
                {
                    className: 'clean-replace-type-mismatches',
                    label: _('Replace Type Mismatches With Null').t(),
                    commandConfigs: ReplaceMismatchedTypesModel.getDefaults()
                },
                {
                     className: 'clean-bucket',
                     label: _('Bucket...').t(),
                     insertDividerAfter: true,
                     commandConfigs: BucketModel.getDefaults()
                },
                {
                    className: 'advanced-eval',
                    label: _('Eval Expression...').t(),
                    description: _('Advanced').t(),
                    commandConfigs: _.extend(EvalExistingFieldModel.getDefaults()),
                    prepareOptions: function(commandConfigs) {
                        var currentCommand = this.model.table.getCurrentCommandModel(),
                            options = {};

                        if (this.model.table.selectedColumns.length === 1) {
                            options.columnName = currentCommand.getFieldNameFromGuid(this.model.table.selectedColumns.first());
                        }

                        return options;
                    }
                }
            ],

            initialize: function() {
                BaseMenu.prototype.initialize.apply(this, arguments);
            },

            startListening: function() {
                this.listenTo(this.model.state, 'directReplaceValue', function(oldCellValue, newCellValue, colIndex) {
                    this.handleDirectReplaceValue(oldCellValue, newCellValue, colIndex);
                });

                BaseMenu.prototype.startListening.apply(this, arguments);
            },

            handleDirectReplaceValue: function(oldCellValue, newCellValue, colIndex) {
                var requiredColumnIds = this.model.table.selectedColumns.pluck('id'),
                    currentCommandIdx = this.model.table.getCurrentCommandIdx(),
                    newCommandIdx = currentCommandIdx + 1;

                // The user has clicked on another cell after entering a new cell value, which has caused selectedColumns
                // to become cleared out. Use instead the passed colIndex to determine the selected cols.
                if (!requiredColumnIds.length) {
                    requiredColumnIds = [this.model.table.getCurrentCommandModel().getGuidForColIndex(colIndex)];
                }

                if (_(oldCellValue).isNull()) {
                    this.model.table.commands.addNewCommand(
                        {
                            type: FillValuesModel.getDefaults().type,
                            isComplete: true,
                            requiredColumns: requiredColumnIds,
                            fillType: FillValuesModel.TYPES.NULL,
                            fillValue: newCellValue
                        },
                        {
                            at: newCommandIdx,
                            updateSPLOptions: {
                                applicationModel: this.model.application
                            }
                        }
                    );
                } else {
                    this.model.table.commands.addNewCommand(
                        {
                            type:  ReplaceModel.getDefaults().type,
                            isComplete: true,
                            requiredColumns: requiredColumnIds,
                            editorValues: {
                                oldValue: oldCellValue,
                                newValue: newCellValue
                            }
                        },
                        {
                            at: newCommandIdx,
                            updateSPLOptions: {
                                applicationModel: this.model.application
                            }
                        }
                    );
                }
            },

            shouldDisableMenuItem: function(menuItem) {
                var selectedColumnGuids = this.model.table.selectedColumns.pluck('id'),
                    selectedColumnModels = this.model.table.getCurrentCommandModel().columns.filter(function(col) {
                            return selectedColumnGuids.indexOf(col.get('id')) > -1;
                        }, this),
                    selectedColumnTypes = _.map(selectedColumnModels, function(selectedColumnModel) {
                            return selectedColumnModel.get('type');
                        }),
                    shouldAllow = _.any(selectedColumnTypes, function(type) {
                            return ((type !== ColumnModel.TYPES._RAW) && (type !== ColumnModel.TYPES._TIME));
                        }, this);

                if (this.model.table.entry.content.get('dataset.display.isSelectionError') && shouldAllow) {
                    // We will enable replace mistypes with null if you click on a cell in type error
                    if (menuItem.className === 'clean-replace-type-mismatches') {
                        return false;
                    }
                }

                return BaseMenu.prototype.shouldDisableMenuItem.apply(this, arguments);
            }
        });
    });
