/**
 * @author cykao
 * Page controller for Authentication User manager page.
 */
define([
        'jquery',
        'underscore',
        'backbone',
        'module',

        /* As a Controller, you can extend this one */
        //'controllers/BaseManagerPageControllerFiltered',
        /* or this one */
        'controllers/BaseManagerPageController',

        'collections/services/authentication/Users',
        'collections/services/authorization/Roles',

        'models/shared/EAIFilterFetchData',
        'models/services/authentication/User',
        'models/services/admin/splunk-auth',
    
        './EditDialog',
        './GridRow',
    
        'uri/route',
        'views/shared/pcss/basemanager.pcss',
        './PageController.pcss'
    ],
    function(
        $,
        _,
        Backbone,
        module,
        BaseController,
        UsersCollection,  // User data 
        RolesCollection,
        EAIFilterFetchData,
        UserModel,
        SplunkAuthModel,
        AddEditDialog,
        GridRow,   
        route,
        cssBaseManager,
        css
    ) {
        return BaseController.extend({
            moduleId: module.id,

            initialize: function(options) {
                this.collection = this.collection || {};
                this.model = this.model || {};
                this.deferreds = this.deferreds || {};

                //MODELS
                this.model.metadata = new EAIFilterFetchData({
                    sortKey: 'name',
                    sortDirection: 'asc',
                    count: 10,
                    offset: 0,
                    ownerSearch: "*",
                    visible: false
                });

                this.model.splunkAuth = new SplunkAuthModel({id: 'splunk_auth'});
                this.deferreds.passwordConfigs = this.model.splunkAuth.fetch();

                //COLLECTIONS
                this.collection.roles = new RolesCollection();
                this.deferreds.roles = this.collection.roles.fetch();

                options.enableNavigationFromUrl = true;
                options.model = this.model;
                options.collection = this.collection;
                options.deferreds = this.deferreds;
                options.entitiesCollectionClass = UsersCollection || {};
                options.entityModelClass = UserModel || {};
                options.fragments = ['authentication', 'users'];
                options.entitiesPlural = _('Users').t();
                options.entitySingular = _('User').t();
                options.grid = {
                    showOwnerFilter: false,
                    showAppColumn: false,
                    showAppFilter: false,
                    showOwnerColumn: false,
                    showDispatchAs: false,
                    showStatusColumn: false,
                    showSharingColumn: false
                };
                
                options.customViews = {
                    AddEditDialog: AddEditDialog,
                    GridRow: GridRow
                };

                options.canEditUser = this.model.user.canEditUsers();
                 
                BaseController.prototype.initialize.call(this, options);
            },

            /**
             * Override default which is _new
             */
            navigateToNew: function() {
                this.navigate('_new', { data: {action: 'edit'}});
            }
        });
    });
