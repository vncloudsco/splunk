/*
* @author atruong
* @date 8/05/2015
*/

define([
	'jquery',
	'underscore',
	'backbone',
	'module',
	'controllers/Base',
	'collections/shared/FlashMessages',
	'splunk_monitoring_console/views/settings/overview_preferences/Master',
	'splunk_monitoring_console/collections/ThresholdConfigs',
	'models/Base',
    'views/shared/vizcontrols/format/Master.pcss',
    './PageController.pcss'
], function(
	$,
	_,
	Backbone,
	module,
	BaseController,
	FlashMessagesCollection,
	MasterView,
	ThresholdConfigsCollection,
	BaseModel,
    sharedVizControlsCss,
    css
	) {

	return BaseController.extend({
		moduleId: module.id,

		initialize: function(options) {
			BaseController.prototype.initialize.apply(this, arguments);

			this.collection = this.collection || {};
			this.model = this.model || {};
			this.deferreds = this.deferreds || {};

			this.collection.thresholdConfigs = new ThresholdConfigsCollection();
			this.collection.thresholdConfigs.fetchData.set({count: 25});
			
			$.when(this.collection.thresholdConfigs.fetch()).done(_(function() {
				this.children.masterView = new MasterView({
					collection: { thresholdConfigs: this.collection.thresholdConfigs }
				});
				this.debouncedRender();
			}).bind(this));
		},

		render: function() {
			if (this.children.masterView) {
				this.children.masterView.detach();
				this.children.masterView.render().appendTo(this.$el);
			}

			return this;
		}
	});
});
