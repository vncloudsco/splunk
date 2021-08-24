/**
 * @author jszeto
 * @date 2/5/15
 *
 * Router for Cloud Index Manager
 *
 *
 */

define(
    [
        'underscore',
        'backbone',
        './IndexesBase',
        'models/indexes/cloud/Archiver',
        'models/indexes/cloud/DynamicDataArchiveConfig',
        'models/services/data/Archiver',
        'models/indexes/cloud/Index',
        'models/indexes/cloud/CloudIndex',
        'collections/indexes/cloud/Indexes',
        'collections/services/data/Indexes',
        'collections/indexes/cloud/Archives',
        'models/indexes/shared/IndexFetchData',
        'models/indexes/shared/NoInternalIndexFetchData',
        'views/error/Master',
        'views/indexes/cloud/AddEditIndexDialog',
        'views/indexes/shared/PageController',
        'contrib/text!views/indexes/cloud/GridRow.html',
        'contrib/text!views/indexes/cloud/GridRowSingleInstance.html'
    ],
    function(
        _,
        Backbone,
        BaseRouter,
        ArchiverModel,
        DynamicDataArchiveConfig,
        ArchiverSingleInstanceModel,
        IndexModel,
        CloudIndexSingleInstanceModel,
        IndexesCollection,
        IndexesSingleInstanceCollection,
        ArchivesCollection,
        IndexFetchData,
        IndexSingleInstanceFetchData,
        ErrorView,
        AddEditIndexDialog,
        IndexesController,
        IndexesGridRowTemplate,
        IndexesGridRowSingleInstanceTemplate

    ) {
        return BaseRouter.extend({
            initialize: function(options) {
                BaseRouter.prototype.initialize.apply(this, arguments);
                this.setPageTitle(_('Manage Indexes').t());
                this.isSingleInstanceCloud = _.isObject(options) ? !!options.isSingleInstanceCloud : false;
                this.pageError = options.pageError;
            },

            createController: function(model, collection) {
                if (!this.model.user.canEditIndexes() || this.pageError) {
                    var status = _("Access Denied").t(),
                        message = _("You do not have permission to view this page.").t();
                    if (this.pageError){
                        status = this.pageError.status + " - " + this.pageError.statusText;
                        if (this.pageError.responseJSON.messages && this.pageError.responseJSON.messages.length) {
                            message = this.pageError.responseJSON.messages[0].text;
                        } else {
                            message = this.pageError.statusText;
                        }
                    }
                    var errorController = new ErrorView({
                        model: {
                            application: this.model.application,
                            error: new Backbone.Model({
                                status: status,
                                message: message
                            })
                        }
                    });

                    // Patch the view to satisfy the API expected by IndexesBase router
                    errorController.model.controller = new Backbone.Model();
                    return errorController;
                } else {
                    var archiverModelSingleInstance = this.collection.appLocals.isArchiverAppInstalled() ? 
                        ArchiverSingleInstanceModel : CloudIndexSingleInstanceModel;
                    return new IndexesController({
                        model: model || this.model,
                        router: this,
                        isCloud: true,
                        isSingleInstanceCloud: this.isSingleInstanceCloud,
                        collection: collection || this.collection,
                        archivesCollectionClass: ArchivesCollection,
                        dynamicDataArchiveConfig: new DynamicDataArchiveConfig(),
                        archiverModelClass: this.isSingleInstanceCloud ? archiverModelSingleInstance : ArchiverModel,
                        indexModelClass: this.isSingleInstanceCloud ? CloudIndexSingleInstanceModel : IndexModel,
                        indexesCollectionClass: this.isSingleInstanceCloud ? IndexesSingleInstanceCollection : IndexesCollection,
                        indexesFetchDataClass: this.isSingleInstanceCloud ? IndexSingleInstanceFetchData : IndexFetchData,
                        addEditDialogClass: AddEditIndexDialog,
                        showAppFilter: false,
                        showConfirmSaveDialog: !this.isSingleInstanceCloud,
                        showConfirmDeleteDialog: !this.isSingleInstanceCloud,
                        templates: {
                            gridRow: this.isSingleInstanceCloud ? IndexesGridRowSingleInstanceTemplate : IndexesGridRowTemplate
                        }
                    });
                }
            }

        });
    }
);
