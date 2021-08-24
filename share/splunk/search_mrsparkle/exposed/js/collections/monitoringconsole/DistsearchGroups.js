// Note: ideally this lives in collections/services/search/distributed/groups
// but that is not implemented yet.
// So we go to the raw conf file

define(
	[
		'jquery',
		'underscore',
		'collections/SplunkDsBase',
		'models/monitoringconsole/DistsearchGroup'
	],
	function(
		$,
		_,
		SplunkDsBaseCollection,
		DistsearchGroupModel
	) {
		
		return SplunkDsBaseCollection.extend({
			url: '/services/search/distributed/groups',
			model: DistsearchGroupModel
		});
	} 
);