/*
* @author atruong
* @date 6/23/2015
* Page controller for DMC alerts manager page. Modeled off Sourcetype
*/

define([
	'jquery',
	'underscore',
	'backbone',
	'module',
	'controllers/Base',
	'collections/shared/FlashMessages',
	'splunk_monitoring_console/views/settings/dmc_alerts_setup/enterprise/Master',
	'collections/managementconsole/AlertConfigs',
	'splunk_monitoring_console/collections/DMCAlertsSavedSearches',
    'models/services/server/ServerInfo',
    '../PageController.pcss'
], function(
	$,
	_,
	Backbone,
	module,
	BaseController,
	FlashMessagesCollection,
	MasterView,
	AlertConfigsCollection,
	DMCAlertsSavedSearchesCollection,
	ServerInfoModel,
    css
	) {

	return BaseController.extend({
		moduleId: module.id,

		initialize: function(options) {
			BaseController.prototype.initialize.apply(this, arguments);

			this.collection = this.collection || {};
			this.model = this.model || {};
			this.deferreds = this.deferreds || {};

			this.collection.alerts = new DMCAlertsSavedSearchesCollection();
			this.deferreds.alerts = this.collection.alerts.fetch(); 

			this.collection.alertConfigs = new AlertConfigsCollection();
			this.deferreds.alertConfigs = this.collection.alertConfigs.fetch();
			
			this.model.serverInfoModel = new ServerInfoModel();
			this.deferreds.serverInfoModel = this.model.serverInfoModel.fetch();
			
			this.collection.flashMessages = this.collection.flashMessages || new FlashMessagesCollection();

			$.when(this.deferreds.alerts, this.deferreds.alertConfigs, this.deferreds.serverInfoModel).then(_(function() {
				this.children.masterView = new MasterView({
					model: { application: this.model.application, serverInfo: this.model.serverInfoModel },
					collection: { alerts: this.collection.alerts, alertConfigs: this.collection.alertConfigs }
				});
				this.debouncedRender();
			}).bind(this));
		},

		alertConfigForName: function(name) {
			this.collection.alertConfigs.find(function(model) { return model.entry.get('name') === name; });
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
