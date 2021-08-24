// Note: ideally this would exist in js/collections/services/search/distributed/peers

define(
	[
		'jquery',
		'underscore',
		'collections/SplunkDsBase',
		'splunk_monitoring_console/collections/Assets',
		'collections/monitoringconsole/DistsearchGroups',
		'splunk_monitoring_console/models/Peer',
		'splunkjs/mvc/savedsearchmanager'
	],
	function(
		$, 
		_, 
		SplunkDsBaseCollection, 
		AssetCollection, 
		DistsearchGroupCollection,
		PeerModel,
		SavedSearchManager
	) {

		return SplunkDsBaseCollection.extend({
			initialize: function() {
				SplunkDsBaseCollection.prototype.initialize.apply(this, arguments);
				this.assets = new AssetCollection();
				this.distsearches = new DistsearchGroupCollection();
			},
			model: PeerModel,
			url: 'search/distributed/peers',

			// Fetches AssetModels first upon which PeerModels depend.
			// Then, fetches PeerModels.
			// PeerModels are responsible for finding and maintaining AssetModels
			fetch: function() {
				var dfd = $.Deferred();
				var fetchArguments = _.toArray(arguments);

				// we're only grabbing managementconsole groups
				$.when(
					this.distsearches.fetch({
						data: {
							search: 'name=dmc_*',
							count: 1000
						}
					}),
					this.assets.fetch()
				).done(function() {
					SplunkDsBaseCollection.prototype.fetch.apply(this, fetchArguments).done(function() {
						dfd.resolve();
					}.bind(this));
				}.bind(this));

				return dfd;
			},

			// Full save functionality
			save: function() {
				var dfd = $.Deferred();

				var configuredPeers = this.filter(function(peer) {
					return (peer.entry.content.get("status-toggle") === "Enabled" || peer.entry.content.get("state") === "Configured");
				}).map(function(peer) {
					return peer.entry.get('name');
				}).join(',');
				var settingsAsset = this.assets.find(function(asset) {
					return asset.entry.get('name') === 'settings';
				});
				settingsAsset.entry.content.set('configuredPeers', configuredPeers);

				// Ensure Indexers are default group
				var indexerGroup = this.distsearches.find(function(group) {
					return group.hasServerRole('indexer');
				});
				indexerGroup.entry.content.set('default', true);

				$.when.apply(
					$,
					// N.B. any changes to models in this collection are persisted automatically
					// We just need to save the distributed search groups to save everything, essentially 
					_.map([settingsAsset].concat(this.distsearches.models), function(model) {
						return model.save();
					})
				).done(this._buildAssetCache('DMC Asset - Build Full').done(function(data) {
					dfd.resolve(data);
				}).fail(function() {
					dfd.reject();
				})).fail(function() {
					dfd.reject();
				});

				return dfd;
			},

			// Full save functionality
			saveSelected: function() {
				var dfd = $.Deferred();

				var configuredPeers = this.filter(function(peer) {
					return (peer.entry.content.get("status-toggle") === "Enabled" || peer.entry.content.get("state") === "Configured");
				}).map(function(peer) {
					return peer.entry.get('name');
				}).join(',');
				var settingsAsset = this.assets.find(function(asset) {
					return asset.entry.get('name') === 'settings';
				});
				settingsAsset.entry.content.set('configuredPeers', configuredPeers);

				// Ensure Indexers are default group
				var indexerGroup = this.distsearches.find(function(group) {
					return group.hasServerRole('indexer');
				});
				indexerGroup.entry.content.set('default', true);

				$.when.apply(
					$,
					// N.B. any changes to models in this collection are persisted automatically
					// We just need to save the distributed search groups to save everything, essentially
					_.map([settingsAsset].concat(this.distsearches.models), function(model) {
						return model.save();
					})
				).done(function() {
						dfd.resolve();
					}).fail(function() {
						dfd.reject();
					});

				return dfd;
			},

			disable: function() {
				var dfd = $.Deferred();
				var deferreds = [];

				var settingsAsset = this.assets.find(function(asset) {
					return asset.entry.get('name') === 'settings';
				});
				settingsAsset.entry.content.set('configuredPeers', '');
				settingsAsset.entry.content.set('blackList', '');

				// Ensure Indexers are turned off
				var indexerGroup = this.distsearches.find(function(group) {
					return group.hasServerRole('indexer');
				});
				indexerGroup && indexerGroup.entry.content.set('default', false);

				$.when.apply(
					$,
					_.map([settingsAsset].concat(this.distsearches.models), function(model) {
						return model.save();
					})
				).done(this._buildAssetCache('DMC Asset - Build Standalone Computed Groups Only').done(function() {
					dfd.resolve();
				}).fail(function() {
					dfd.reject();
				})).fail(function() {
					dfd.reject();
				});

				return dfd;
			},

			getAllTags: function() {
				return this._getAll('isCustomGroup');
			},

			getAllIndexerClusters: function() {
				return this._getAll('isIndexerClusterGroup');
			},

			getAllSearchHeadClusters: function() {
				return this._getAll('isSearchHeadClusterGroup');
			},

			_getAll: function(predicate) {
				return this.distsearches.filter(function(group) {
					return group[predicate].call(group);
				}).map(function(group) {
					return group.getDisplayName();
				});
			},

			_buildAssetCache: function(cacheName) {
				var dfd = $.Deferred();
				
				// Create the asset table cache
				var cacheSm = new SavedSearchManager({
					id: 'smc-create-cache-search',
					searchname: cacheName,
					cache: false,
					preview: false,
					app: 'splunk_monitoring_console',
					owner: 'nobody',
					autostart: true,
					trigger_actions: true
				});

				var resultsModel = cacheSm.data('results', {count: 0});
				resultsModel.on('data', function() {
					if (resultsModel.hasData()) {
						dfd.resolve(resultsModel.data());
					}
				});

				cacheSm.on('search:error search:failed', function() {
					dfd.reject();
				});

				return dfd;
			}
		});
	}
);
