define([
    'underscore',
    'module',
    'backbone',
    'collections/monitoringconsole/splunk_health_check/CheckLists',
    'controllers/BaseManagerPageController',
    'models/monitoringconsole/splunk_health_check/CheckList',
    'views/monitoringconsole/splunk_health_check_list/ActionCell',
    'views/monitoringconsole/splunk_health_check_list/GridRow',
    'views/monitoringconsole/splunk_health_check_list/AddEditDialog',
    'views/monitoringconsole/splunk_health_check_list/NewButtons',
    'views/monitoringconsole/splunk_health_check_list/PageController.pcss',
    'views/shared/pcss/basemanager.pcss'
], function(
    _,
    module,
    Backbone,
    CheckListsCollection,
    BaseController,
    CheckListModel,
    ActionCell,
    GridRow,
    AddEditDialog,
    NewButtons,
    css,
    cssShared
) {
    return BaseController.extend({
        moduleId: module.id,

        initialize: function(options) {
            options.entitiesPlural = _('Health Check Items').t();
            options.entitySingular = _('Health Check Item').t();
            // TODO: fill in page description and learnMore link
            options.header = {
                pageDesc: '',
                learnMoreLink: ''
            };
            options.entitiesCollectionClass = CheckListsCollection;
            options.entityModelClass = CheckListModel;
            options.grid = {
                showAllApps: true,
                showOwnerFilter: false,
                showSharingColumn: false,
                showStatusColumn: false
            };
            options.customViews = options.customViews || {};
            options.customViews.ActionCell = ActionCell;
            options.customViews.GridRow = GridRow;
            options.customViews.AddEditDialog = AddEditDialog;
            options.customViews.NewButtons = NewButtons;

            BaseController.prototype.initialize.call(this, options);
        }
    });
});
