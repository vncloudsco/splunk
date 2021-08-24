/**
 * @author lbudchenko / jszeto
 * @date 2/6/15
 *
 */
define([
        'jquery',
        'underscore',
        'backbone',
        'module',
        'controllers/BaseManagerPageControllerFiltered',
        'collections/services/AppLocals',
        'collections/indexes/cloud/Archives',
        'collections/services/configs/conf-self-storage-locations/BucketList',
        'collections/services/catalog/metricstore/Rollup',
        'collections/services/data/IndexesExtended',
        './DeleteIndexDialog',
        'views/shared/basemanager/EditDialog',
        'views/shared/basemanager/EnableDialog',
        'views/shared/basemanager/DisableDialog',
        'views/indexes/cloud/restore_archive/Master',
        './AddEditWaitIndexDialog',
        './DeleteWaitIndexDialog',
        './GridRow',
        './NewButtons',
        'views/shared/pcss/basemanager.pcss',
        './PageController.pcss'
    ],
    function(
        $,
        _,
        Backbone,
        module,
        BaseController,
        AppsCollection,
        ArchivesCollection,
        BucketListCollection,
        RollupCollection,
        IndexesExtendedCollection,
        DeleteIndexDialog,
        AddEditDialog,
        EnableDialog,
        DisableDialog,
        RestoreArchiveDialog,
        AddEditWaitIndexDialog,
        DeleteWaitIndexDialog,
        GridRow,
        NewButtons,
        cssBaseManager,
        css
    ) {
        var SELF_STORAGE_CONST = 'SelfStorage',
            ARCHIVE_CONST = 'Archive',
            NONE_CONST = 'None';

        var IndexesController = BaseController.extend({
            moduleId: module.id,

            initialize: function(options) {
                this.deferreds = {};

                // Create models and collections
                this.model = this.model || {};
                // The controller model is passed down to all subviews and serves as the event bus for messages between
                // the controller and views.
                this.model.controller = this.model.controller || new Backbone.Model();


                if (this.options.isCloud) {
                    this.model.controller.set('mode', 'cloud');
                } else {
                    this.model.controller.set('mode', 'local');
                }

                if (this.options.isSingleInstanceCloud) {
                    this.model.controller.set('singleInstance', true);
                    // fetch the data/indexes-extended endpoint so we have raw data size for singleinstance cloud.
                    this.collection.indexesExtended = new IndexesExtendedCollection();
                    this.deferreds.indexesExtended = this.fetchIndexesExtended();
                }
                if (this.options.isCloudLight) {
                    this.model.controller.set('cloudLight', true);
                }

                if (this.options.isCloud) {
                    this.collection.archives = new ArchivesCollection();
                    this.deferreds.archives = this.fetchArchivesCollection();
                } else {
                    this.collection.rollup = new RollupCollection();
                }
                
                if (this.options.isCloud && !this.options.isSingleInstanceCloud) {
                    this.deferreds.dynamicDataArchive =
                        this.options.dynamicDataArchiveConfig.getConfigSettings();
                }

                this.collection.bucketList = new BucketListCollection();

                var showWaitSaveDialog = this.options.isCloud && !this.options.isSingleInstanceCloud,
                    showWaitDeleteDialog = this.options.isCloud && !this.options.isSingleInstanceCloud,
                    pageDesc = _("A repository for data in Splunk Enterprise. Indexes reside in flat files on the Splunk Enterprise instance known as the indexer.").t();
                if (this.model.serverInfo) {
                    if (this.model.serverInfo.isLite()){
                        pageDesc = _("A repository for data in Splunk Light. Indexes reside in flat files on the Splunk Light instance.").t();
                    }
                    else if (this.model.serverInfo.isCloud()){
                        pageDesc = _("A repository for data in Splunk Cloud. Indexes reside in flat files on the Splunk Cloud instance known as the indexer.").t();
                    }
                }
                this.model.controller.set('showWaitSaveDialog', showWaitSaveDialog);
                this.model.controller.set('showWaitDeleteDialog', showWaitDeleteDialog);

                options.enableNavigationFromUrl = true;
                options.fragments = ['data', 'indexes'];
                options.entitySingular = _('Index').t();
                options.entitiesPlural = _('Indexes').t();
                options.header = {
                    pageTitle: _('Indexes').t(),
                    pageDesc: pageDesc,
                    learnMoreLink: 'manager.indexes.about'
                };
                options.model = this.model;
                options.collection = this.collection;
                options.deferreds = this.deferreds;
                options.entitiesCollectionClass = this.options.indexesCollectionClass;
                options.entityModelClass = this.options.indexModelClass;
                options.archiverModelClass =  this.options.archiverModelClass;
                options.entityFetchDataClass = this.options.indexesFetchDataClass;
                options.grid = {
                    showAppFilter: !this.options.showAppFilter,
                    showOwnerFilter: false,
                    showSharingColumn: false
                };
                options.actions = {
                    confirmEnableDisable: true
                };
                options.customViews = {
                    AddEditDialog: this.options.addEditDialogClass,
                    GridRow: GridRow,
                    NewButtons: NewButtons
                };

                // Show rolling restart warning for stackmakr, but not rainmakr
                if (this.model.serverInfo && this.model.serverInfo.isCloud() && !options.isSingleInstanceCloud) {
                    options.showRollingRestartWarning = true;
                }

                BaseController.prototype.initialize.call(this, options);
            },

            fetchArchivesCollection: function() {
                if (this.collection.archives && this.model.user.canViewArchives()) {
                    return this.collection.archives.fetch({
                        data: {
                            count: -1
                        }
                    });
                } else {
                    var theDeferred = $.Deferred();
                    theDeferred.resolve();
                    return theDeferred;
                }
            },

            /**
             * Fetch the IndexesExtended REST endpoint.
             * Used for acquiring raw size data for single instance cloud.
             */
            fetchIndexesExtended: function() {
                return this.collection.indexesExtended.fetch({
                    data: {
                        count: -1
                    }
                });
            },

            initEventHandlers: function(options) {
                BaseController.prototype.initEventHandlers.call(this, options);
                this.listenTo(this.model.controller, "restoreEntity", this.showRestoreDialog);
            },

            /* Create/Edit action */
            // editIndex->onEditEntity->showAddEditDialog->onEntitySaved->showWaitSaveIndexDialog->onEditDialogHidden->
            // ->onWaitSaveDialogHidden->navigate
            onEntitySaved: function(index) {
                // Show save waiting dialog if enabled.
                if (this.model.controller.get('showWaitSaveDialog') && this.children.editDialog.options.isNew){
                    this.showWaitSaveIndexDialog(index);
                }
                this.fetchEntitiesCollection();
            },
            /**
             * Show the restore modal for restoring archive
             * @param entityModel
             */
            showRestoreDialog: function(entityModel) {
                this.children.restoreArchiveModal = new RestoreArchiveDialog({
                    model: {
                        entity: entityModel
                    }
                });
                this.children.restoreArchiveModal.render().appendTo($("body"));
            },
            showAddEditDialog: function(entityModel, isClone) {
                var isCloud = this.model.serverInfo.isCloud();
                var dialogOptions = $.extend({}, this.options);

                if (entityModel) {
                    // clone to prevent changes in the table as you edit the fields in the popup
                    this.model.entity = entityModel.clone();
                } else {
                    this.model.entity = new this.options.entityModelClass();
                }

                this.model.stateModel.set('isArchiverAppInstalled', this.collection.appLocals.isArchiverAppInstalled());
                if (isCloud && !_.isUndefined(this.model.stateModel.get('isArchiverAppInstalled'))) {
                    if (!_.isUndefined(this.model.entity.entry.content.get('archiver.selfStorageBucket'))) {
                        this.model.stateModel.set('dynamicStorageOption', SELF_STORAGE_CONST);
                    }

                    if (this.deferreds.dynamicDataArchive) {
                        this.deferreds.dynamicDataArchive.then(function() {
                            this.model.stateModel.set('isDataArchiveEnabled', this.options.dynamicDataArchiveConfig.isEnabled);
                            this.model.stateModel.set('maxArchiveRetention', this.options.dynamicDataArchiveConfig.maxRetentionPeriod);
                            this.model.stateModel.set('archiverConfigSet', true);
                        }.bind(this));
                    }
                    // fetch bucketlist when showAddEditDialog is called instead of constructor
                    // to avoid fetching bucketlist if not needed
                    this.deferreds.bucketList = new $.Deferred();
                    this.collection.bucketList.fetch({
                        data: {
                            count: -1,
                            owner: this.model.application.get('owner'),
                            app: this.model.application.get('app')
                        },
                        success: _(function (collection, response) {
                            if (collection.length > 0) {
                                this.model.stateModel.set('selfStorageConfigured', true);
                            } else {
                                this.model.stateModel.set('selfStorageConfigured', false);
                            }
                            this.deferreds.bucketList.resolve();
                        }).bind(this)
                    });
                    this.model.stateModel.set('archiverAppLabel', this.collection.appLocals.archiverAppLabel());
                    dialogOptions.archiverModelClass = this.options.archiverModelClass;
                } else if (this.options.isSingleInstanceCloud) {
                    this.model.stateModel.set('isDataArchiveEnabled', false);
                    this.model.stateModel.set('maxArchiveRetention', 0);
                }

                dialogOptions = $.extend(dialogOptions, {
                    isNew: _.isUndefined(entityModel),
                    isClone: isClone,
                    model: this.model,
                    collection: this.collection,
                    deferred: this.deferreds,
                    SELF_STORAGE: SELF_STORAGE_CONST,
                    ARCHIVE: ARCHIVE_CONST,
                    NONE: NONE_CONST
                });

                var _AddEditDialog = this.options.customViews.AddEditDialog || AddEditDialog;
                this.children.editDialog = new _AddEditDialog(dialogOptions);
                this.listenTo(this.children.editDialog, "entitySaved", this.onEntitySaved);
                this.listenTo(this.children.editDialog, "hidden", this.onEditDialogHidden);
                this.children.editDialog.render().appendTo($("body"));

                this.children.editDialog.show();
            },
            showWaitSaveIndexDialog: function(index){
                // Build save waiting dialog. Refresh data when dialog is hidden.
                this.children.waitSaveIndexDialog = new AddEditWaitIndexDialog({ model: index.clone() });
                this.listenTo(this.children.waitSaveIndexDialog, "hidden", this.onWaitSaveDialogHidden);
                this.children.waitSaveIndexDialog.render().appendTo($("body"));
                this.children.waitSaveIndexDialog.show();
            },
            onEditDialogHidden: function() {
                BaseController.prototype.onEditDialogHidden.apply(this, arguments);
                this.stopListening(this.children.editDialog, "entitySaved", this.showWaitSaveIndexDialog);
            },
            onWaitSaveDialogHidden: function() {
                this.fetchEntitiesCollection();
                this.stopListening(this.children.waitSaveIndexDialog, "hidden", this.onWaitSaveDialogHidden);
            },

            /* Delete action */
            /**
             * Respond to the deleteIndex event by displaying a waiting dialog
             * @param indexModel - the model to delete
             */
            onDeleteEntity: function(indexModel) {
                this.children.deleteIndexDialog = new DeleteIndexDialog({
                    model: indexModel.clone(),
                    showSpinner: this.model.controller.get('showWaitDeleteDialog')
                });

                // Show save confirmation dialog if enabled.
                if (this.model.controller.get('showWaitDeleteDialog')){
                    this.listenTo(this.children.deleteIndexDialog, "deleteIndexConfirmed", this.showWaitDeleteIndexDialog);
                }
                else {
                    this.listenTo(this.children.deleteIndexDialog, "deleteIndexConfirmed", this.fetchEntitiesCollection);
                }

                this.listenTo(this.children.deleteIndexDialog, "hidden", this.onDeleteDialogHidden);
                this.children.deleteIndexDialog.render().appendTo($("body"));
                this.children.deleteIndexDialog.show();
            },
            onDeleteDialogHidden: function() {
                // Stop listening to deleteIndexConfirmed and hidden
                this.stopListening(this.children.deleteIndexDialog, "deleteIndexConfirmed", this.fetchEntitiesCollection);
                this.stopListening(this.children.deleteIndexDialog, "deleteIndexConfirmed", this.showWaitDeleteIndexDialog);
                this.stopListening(this.children.deleteIndexDialog, "hidden", this.onDeleteDialogHidden);
                this.children.deleteIndexDialog.remove();
            },
            showWaitDeleteIndexDialog: function(indexModel){
                // Build save waiting dialog. Refresh data when dialog is hidden.
                this.children.waitDeleteIndexDialog = new DeleteWaitIndexDialog({ model: indexModel.clone() });
                this.listenTo(this.children.waitDeleteIndexDialog, "hidden", this.onWaitDeleteDialogHidden);
                this.children.waitDeleteIndexDialog.render().appendTo($("body"));
                this.children.waitDeleteIndexDialog.show();
            },
            onWaitDeleteDialogHidden: function() {
                this.onDeleteDialogHidden();
                this.fetchEntitiesCollection();
                if (this.children.waitDeleteIndexDialog){
                    this.stopListening(this.children.waitDeleteIndexDialog, "hidden", this.onWaitDeleteDialogHidden);
                }
            },

            remove: function() {
                BaseController.prototype.remove.apply(this, arguments);
                this.children.masterView.remove();
            }

        });

        return IndexesController;

    });
