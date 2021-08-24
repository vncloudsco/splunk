/**
 * @author vroy
 * @date 10/25/15
 *
 * Grid component of listing page for DMC Alerts Setup; modeled off of Sourcetypes
 */

 define([
 	'underscore',
 	'jquery',
 	'module',
 	'views/Base',
 	'helpers/grid/RowIterator',
 	'views/shared/FlashMessages',
 	'splunk_monitoring_console/views/settings/dmc_alerts_setup/lite/GridRow',
 	'contrib/text!./Grid.html',
 	'util/splunkd_utils',
	'util/general_utils'
 ], function(
 	_,
 	$,
 	module,
 	BaseView,
 	RowIterator,
 	FlashMessagesView,
 	GridRow,
 	template,
 	splunkDUtils,
	util
 ){
 	return BaseView.extend({
 		moduleId: module.id,
 		template: template,

 		initialize: function(options) {
 			BaseView.prototype.initialize.call(this, options);
 			this.validAlertCount = 0;

 			this.children.flashMessages = new FlashMessagesView({
 				className: 'message-single',
 				collection: {
 					dmc_alerts: this.collection.savedSearches
 				},
 				helperOptions: {
 					removeServerPrefix: true
 				}
 			});

 			this.listenTo(this.collection.savedSearches, 'change reset', this.debouncedRender);
 		},

 		updateNoAlertsMessage: function() {
	        if (this.collection.savedSearches.length === 0) {
	            var errMessage = _('No preconfigured alerts found.').t();
	            this.children.flashMessages.flashMsgHelper.addGeneralMessage('no_alerts',
	                {
	                    type: splunkDUtils.ERROR,
	                    html: errMessage
	                });
	        } else {
	            this.children.flashMessages.flashMsgHelper.removeGeneralMessage('no_alerts');
	        }
	    },

	    getValidAlertCount: function() {
	    	return (this.validAlertCount > 0)? this.validAlertCount : 0;
	    },

 		render: function() {
 			var rowIterator = new RowIterator();
 			var $html = $(this.compiledTemplate());
 			
 			rowIterator.eachRow(this.collection.savedSearches, function(savedSearch) {
 				var alertConfig = this.collection.alertConfigs.find(function(model) { return model.entry.get('name') === savedSearch.entry.get('name'); });
 				var gridRow = new GridRow({
 					model: { 
 						savedSearch: savedSearch, 
 						alertConfig: alertConfig, 
 						serverInfo: this.model.serverInfo, 
 						application: this.model.application 
 					},
 					collection: {
 						savedSearches: this.collection.savedSearches,
 						alertActionUIs: this.collection.alertActionUIs,
 						alertActions: this.collection.alertActions 
 					}
  				});

 				var toShow = true;

 				if (!alertConfig) {
 					toShow = false;
 				}
 				
 				if (alertConfig && !util.normalizeBoolean(alertConfig.entry.content.get('enabled_for_light')) ) {
					toShow = false;
				}

				if (this.model.serverInfo.isCloud() && !util.normalizeBoolean(alertConfig.entry.content.get('enabled_for_cloud')) ) {
					toShow = false;
				}

 				if (toShow) {
 					this.validAlertCount++;
					$html.find('.grid-table-body').append(gridRow.render().el);
				}

 			}, this);
 			this.$el.html($html);
			this.children.flashMessages.render().appendTo(this.$el);
			this.updateNoAlertsMessage();

 			return this;
 		}

 	});
 });