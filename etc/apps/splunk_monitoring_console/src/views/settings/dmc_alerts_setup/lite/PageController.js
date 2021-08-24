/*
* @author vroy
* @date 10/25/15
* Page controller for DMC alerts manager page. Modeled off Sourcetype
*/

define([
	'jquery',
	'underscore',
	'backbone',
	'module',
	'controllers/Base',
	'collections/shared/FlashMessages',
	'collections/managementconsole/AlertConfigs',
	'splunk_monitoring_console/collections/DMCAlertsSavedSearches',
    'collections/services/data/ui/ModAlerts',
    'collections/shared/ModAlertActions',
    'models/services/data/ui/Manager',
    'models/services/server/ServerInfo',
	'splunk_monitoring_console/views/settings/dmc_alerts_setup/lite/Master',
    '../PageController.pcss'

], function(
	$,
	_,
	Backbone,
	module,
	BaseController,
	FlashMessagesCollection,
	AlertConfigsCollection,
	DMCAlertsSavedSearchesCollection,
	ModAlertsUICollection,
	ModAlertActionsCollection,
	ManagerViewModel,
	ServerInfoModel,
	MasterView,
    css
	) {

	return BaseController.extend({
		moduleId: module.id,

		initialize: function(options) {
			BaseController.prototype.initialize.apply(this, arguments);

			this.collection = this.collection || {};
			this.model = this.model || {};
			this.deferreds = this.deferreds || {};

			this.collection.savedSearches = new DMCAlertsSavedSearchesCollection();
			this.deferreds.savedSearches = this.collection.savedSearches.fetch();

			this.collection.alertConfigs = new AlertConfigsCollection();
			this.deferreds.alertConfigs = this.collection.alertConfigs.fetch();

			//splunk_monitoring_console/alerts/alert_actions
			this.collection.alertActions = new ModAlertActionsCollection();
			this.deferreds.alertActions = this.collection.alertActions.fetch({
				data: {
                    app: this.model.application.get("app"),
                    owner: this.model.application.get("owner"),
                    search: 'disabled!=1'
                },
                addListInTriggeredAlerts: true	
			});

			//splunk_monitoring_console/data/ui/alerts
            this.collection.alertActionUIs = new ModAlertsUICollection();
            this.deferreds.alertActionUIs = this.collection.alertActionUIs.fetch({
                data: {
                    app: this.model.application.get("app"),
                    owner: this.model.application.get("owner")
                }
            });	

            var alertActionsManagerModel = new ManagerViewModel();
            alertActionsManagerModel.set('id', 'alert_actions');
            //splunk_monitoring_console/data/ui/manager/alert_actions
            this.deferreds.alertActionsManagerModel = alertActionsManagerModel.binaryPromiseFetch({
                data: {
                    app: this.model.application.get("app"),
                    owner: this.model.application.get("owner")
                }
            });

			this.model.serverInfoModel = new ServerInfoModel();
			this.deferreds.serverInfoModel = this.model.serverInfoModel.fetch();
			
			this.collection.flashMessages = this.collection.flashMessages || new FlashMessagesCollection();

			$.when(
				this.deferreds.savedSearches, 
				this.deferreds.alertConfigs,
				this.deferreds.alertActionUIs,
				this.deferreds.alertActions,
				this.deferreds.serverInfoModel,
				this.deferreds.alertActionsManagerModel).then(_(function() {
					this.children.masterView = new MasterView({
						model: { 
							application: this.model.application, 
							serverInfo: this.model.serverInfoModel 
						},
						collection: { 
							savedSearches: this.collection.savedSearches, 
							alertConfigs: this.collection.alertConfigs, 
							alertActionUIs: this.collection.alertActionUIs, 
							alertActions: this.collection.alertActions
						}
					});
					this.debouncedRender();
			}).bind(this));
		},

		render: function() {
			if (this.children.masterView) {
				this.children.masterView.detach();
			}

			if (this.children.masterView) {
				this.children.masterView.render().appendTo(this.$el);
			}
			return this;
		}
	});
});
