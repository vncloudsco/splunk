define(
    [
        'underscore',
        'jquery',
        'module',
        'views/table/resultscontainer/actionbar/actionmenus/BaseMenu',
        'views/table/modals/WarningDialog',
        'collections/datasets/Columns',
        'collections/datasets/Commands',
        'models/datasets/Column',
        'models/datasets/commands/RemoveFields',
        'models/datasets/commands/Rename'
    ],
    function(
        _,
        $,
        module,
        BaseMenu,
        WarningDialog,
        ColumnsCollection,
        CommandsCollection,
        ColumnModel,
        RemoveFieldsCommandModel,
        RenameCommandModel
    ) {
        var TYPE = 'type',
            typesBlacklist = [
                { selection: BaseMenu.SELECTION.TABLE },
                { selection: BaseMenu.SELECTION.CELL },
                { selection: BaseMenu.SELECTION.COLUMN, types: [ ColumnModel.TYPES._RAW, ColumnModel.TYPES._TIME ] },
                { selection: BaseMenu.SELECTION.MULTICOLUMN, types: [ ColumnModel.TYPES._RAW, ColumnModel.TYPES._TIME ] },
                { selection: BaseMenu.SELECTION.TEXT }
            ];

        return BaseMenu.extend({
            moduleId: module.id,
            typeMenuItems: [
                {
                    className: 'type-string',
                    actionType: TYPE,
                    type: ColumnModel.TYPES.STRING,
                    icon: ColumnModel.ICONS[ColumnModel.TYPES.STRING],
                    label: ColumnModel.TYPE_LABELS[ColumnModel.TYPES.STRING],
                    blacklist: typesBlacklist
                },
                {
                    className: 'type-number',
                    actionType: TYPE,
                    type: ColumnModel.TYPES.NUMBER,
                    icon: ColumnModel.ICONS[ColumnModel.TYPES.NUMBER],
                    label: ColumnModel.TYPE_LABELS[ColumnModel.TYPES.NUMBER],
                    blacklist: typesBlacklist
                },
                {
                    className: 'type-boolean',
                    actionType: TYPE,
                    type: ColumnModel.TYPES.BOOLEAN,
                    icon: ColumnModel.ICONS[ColumnModel.TYPES.BOOLEAN],
                    label: ColumnModel.TYPE_LABELS[ColumnModel.TYPES.BOOLEAN],
                    blacklist: typesBlacklist
                },
                {
                    className: 'type-ipv4',
                    actionType: TYPE,
                    type: ColumnModel.TYPES.IPV4,
                    icon: ColumnModel.ICONS[ColumnModel.TYPES.IPV4],
                    label: ColumnModel.TYPE_LABELS[ColumnModel.TYPES.IPV4],
                    blacklist: typesBlacklist
                },
                {
                    className: 'type-epoch-time',
                    actionType: TYPE,
                    type: ColumnModel.TYPES.EPOCH_TIME,
                    icon: ColumnModel.ICONS[ColumnModel.TYPES.EPOCH_TIME],
                    label: ColumnModel.TYPE_LABELS[ColumnModel.TYPES.EPOCH_TIME],
                    blacklist: typesBlacklist
                }
            ],
            additionalMenuItems: [
                {
                    className: 'fields-cut-and-move',
                    label: _('Move').t(),
                    insertDividerAfter: true,
                    blacklist: [
                        { selection: BaseMenu.SELECTION.CELL },
                        { selection: BaseMenu.SELECTION.TABLE },
                        { selection: BaseMenu.SELECTION.TEXT }
                    ]
                },
                {
                    className: 'fields-delete',
                    label: _('Delete').t(),
                    commandConfigs: RemoveFieldsCommandModel.getDefaults(),
                    validateSubsequentCommands: true
                },
                {
                    className: 'fields-rename',
                    label: _('Rename...').t(),
                    insertDividerAfter: true,
                    commandConfigs: RenameCommandModel.getDefaults(),
                    prepareOptions: function(commandConfigs) {
                        var currentCommand = this.model.table.getCurrentCommandModel();

                        return {
                            columnName: currentCommand.getFieldNameFromGuid(this.model.table.selectedColumns.first())
                        };
                    }
                }
            ],

            initialize: function(options) {
                BaseMenu.prototype.initialize.apply(this, arguments);

                options = options || {};
                _.defaults(options, {
                    onlyType: false
                });

                this.commandMenuItems = options.onlyType ? this.typeMenuItems : this.additionalMenuItems.concat(this.typeMenuItems);
            },

            startListening: function() {
                this.listenTo(this.model.state, 'directColRename', function(oldFieldName, newFieldName) {
                    this.handleDirectRename(oldFieldName, newFieldName);
                });

                BaseMenu.prototype.startListening.apply(this, arguments);
            },

            handleDirectRename: function(oldFieldName, newFieldName) {
                // Do a fresh clone of a new Commands Collection so that listenIds and therefore listeners to collection
                // change events are not copied over.
                var commandsClone = new CommandsCollection(this.model.table.commands.toJSON(), {parse: true}),
                    currentCommandIdx = this.model.table.getCurrentCommandIdx(),
                    newCommandIdx = currentCommandIdx + 1,
                    selectedColumns = this.model.table.selectedColumns,
                    previousCommand = commandsClone.at(currentCommandIdx),
                    requiredColumnId,
                    errorMessages,
                    renameCommand;

                if (selectedColumns.length) {
                    requiredColumnId = selectedColumns.pluck('id');
                } else {
                    // If Direct Table Rename was triggered by blur event that clicked on Table Cell,
                    // the mousedown action clears the column selection, so we must manually determine the selected col.
                    requiredColumnId = [previousCommand.columns.where({name: oldFieldName})[0].id];
                }

                // Add rename command  to commands clone, so that we can discard changes if the new field name is
                // invalid, without the add event triggering a page render
                commandsClone.addNewCommand(
                    {
                        type: RenameCommandModel.getDefaults().type,
                        newFieldName: newFieldName,
                        isComplete: true,
                        requiredColumns: requiredColumnId
                    },
                    {
                        at: newCommandIdx,
                        updateSPLOptions: {
                            previousCommand: previousCommand,
                            applicationModel: this.model.application
                        }
                    }
                );

                renameCommand = commandsClone.at(newCommandIdx);

                this.model.table.setCollidingFieldNames({
                    commandEdited: renameCommand,
                    fieldsToAdd: [newFieldName]
                });

                errorMessages = renameCommand.validate();
                renameCommand.unset('collisionFields');

                if (!errorMessages) {
                    // Copy over cloned collection to actual collection to indirectly add rename command
                    this.model.table.commands.reset(commandsClone.toJSON(), {parse: true, add: true, at: newCommandIdx});
                    this.model.state.trigger('directRenameSucceeded', oldFieldName);
                } else {
                    this.openFieldErrorModal(errorMessages.spl || errorMessages.collisionFields, oldFieldName, newFieldName);
                }
            },

            openFieldErrorModal: function(errorMessage, oldFieldName, newFieldName) {
                if (this.children.renameWarningDialog) {
                    this.children.renameWarningDialog.deactivate({deep:true}).remove();
                    delete this.children.renameWarningDialog;
                }
                this.children.renameWarningDialog = new WarningDialog({
                    headerText: _('Rename...').t(),
                    message: '<div class="alert alert-error"><i class="icon-alert"></i>' + errorMessage + '</div>'
                });
                this.children.renameWarningDialog.activate({deep: true}).render().appendTo($('body')).show();
                this.children.renameWarningDialog.on('hidden', _.bind(function() {
                    this.model.state.trigger('directRenameFailed', oldFieldName, newFieldName);
                }, this));
            },

            handleActionClicked: function(item) {
                if (item.className === 'fields-cut-and-move') {
                    this.model.state.set('activeActionBar', 'cutAndMove');
                } else if (item.actionType === TYPE) {
                    this.setType(item);
                }

                BaseMenu.prototype.handleActionClicked.apply(this, arguments);
            },

            setType: function(item) {
                var selectedColumnGuids = this.model.table.selectedColumns.pluck('id'),
                    currentCommandModel = this.model.table.getCurrentCommandModel();

                _.each(selectedColumnGuids, function(selectedColumnGuid) {
                    currentCommandModel.columns.get(selectedColumnGuid).set('type', item.type);
                }, this);

                this.model.table.trigger('applyAction', currentCommandModel, this.model.table.commands);
            },

            shouldDisableMenuItem: function(menuItem) {
                var baseDisable = BaseMenu.prototype.shouldDisableMenuItem.apply(this, arguments);

                if (baseDisable) {
                    return baseDisable;
                }

                if (menuItem.className === 'fields-cut-and-move') {
                    return !this.model.table.selectedColumns.length;
                }
            }
        });
    });
