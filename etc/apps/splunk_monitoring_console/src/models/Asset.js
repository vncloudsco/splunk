define(
	[
		'jquery',
		'underscore',
		'backbone',
		'models/SplunkDBase',
		'models/SplunkDWhiteList'
	], 
	function(
		$,
		_,
		Backbone,
		SplunkDBaseModel,
		SplunkDWhiteListModel
	) {

		// Subclass SplunkDBaseModel's SplunkDWhiteListModel
		// Reason: specify attributes required because I'm not sure how to do it any other way
		// for conf files. via .conf.spec perhaps?
		var AssetWhiteListModel = SplunkDWhiteListModel.extend({
			initialize: function() {
				SplunkDWhiteListModel.prototype.initialize.apply(this, arguments);
			},
			concatOptionalRequired: function() {
				// Save previous state
				var previousOptional = (this.get('optional') || []).slice();

				// Inject optional fields
				this.set('optional', (this.get('optional') || []).concat([
					'configuredPeers',
					'host',
					'host_fqdn',
					'indexerClusters',
					'searchHeadClusters'
				]), { silent: true });

				var whiteListOptAndReq = 
					SplunkDWhiteListModel.prototype.concatOptionalRequired.apply(this, arguments);

				// Revert to previous state
				this.set('optional', previousOptional, { silent: true });

				return whiteListOptAndReq;
			}
		});


		var AssetModel = SplunkDBaseModel.extend(
			{
				url: 'configs/conf-splunk_monitoring_console_assets',

				initialize: function(attributes, options) {
					SplunkDBaseModel.prototype.initialize.call(
						this,
						attributes,
						_.defaults(options || {}, {
							splunkDWhiteList: new AssetWhiteListModel()
						})
					);
				},

				// Need to set the app/owner since this .conf only exists in splunk_monitoring_console
				save: function(attributes, options) {
					if (this.isNew()) {
						options = options || {};
						options.data = _.defaults(options.data || {}, {
							app: 'splunk_monitoring_console',
							owner: 'nobody',
							name: this.entry.get('name')
						});
					}

					return SplunkDBaseModel.prototype.save.call(this, attributes, options);
				}
			}
		);

		return AssetModel;
	}
);
