// Note: this collection should not exist. It represents a set of requirements we need to push to the back end
define(
	[
		'jquery',
		'underscore',
		'splunk_monitoring_console/models/Asset',
		'collections/SplunkDsBase'
	],
	function(
		$,
		_,
		AssetModel,
		SplunkDsBaseCollection
	) {

		return SplunkDsBaseCollection.extend({
			model: AssetModel,
			url: 'configs/conf-splunk_monitoring_console_assets',
			fetch: function(options) {
				options = _.defaults(options || {}, { count: 0 });
				options.data = _.defaults(options.data || {}, {
					app: 'splunk_monitoring_console',
					owner: 'nobody',
					count: -1
				});

				return SplunkDsBaseCollection.prototype.fetch.call(this, options);
			}
		});

	}
);
