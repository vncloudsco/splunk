define(
	[
		'underscore',
		'splunk.config',
		'uri/route',
		'models/classicurl'
	],
	function(
		_,
		config,
		route,
		classicurl
	) {
		return {
            pages: {
                SERVER_CLASS: 'server_classes_page',
                APP: 'apps_page',
                TOPOLOGY: 'topology_page'
            },

			pageUrl: function(pageName, options) {
				var root = this._configureRoot();

                return route.page(
                	root,
                	config.LOCALE,
                	'dmc',
                	pageName,
                	{ data: options }
                );
			},

            appBrowserUrl: function() {
                var root = this._configureRoot();

                return route.page(
                    root,
                    config.LOCALE,
                    'dmc',
                    'install_app'
                );
            },

            viewObjectsUrl: function(bundleName) {
                var root = this._configureRoot();

                return route.manager(
                    root,
                    config.LOCALE,
                    'launcher',
                    ['admin', 'directory'],
                    {
                        data: {
                            ns: bundleName,
                            appOnly: 1
                        }
                    }
                );
            },

            setupUrl: function(bundleName) {
                var root = this._configureRoot();

                return route.manager(
                    root,
                    config.LOCALE,
                    bundleName,
                    ['apps', 'local', bundleName, 'setup'],
                    {
                        data: {
                            action: 'edit'
                        }
                    }
                );
            },

            appUrl: function(appName) {
                var root = this._configureRoot();

                return route.page(
                    root,
                    config.LOCALE,
                    appName
                );
            },

			docUrl: function(locationString) {
				var root = this._configureRoot();

				return route.docHelp(
					root,
					config.LOCALE,
					locationString
				);
			},

			getUrlParam: function(param) {
                return classicurl.decode(location.search)[param];
            },

			removeUrlParam: function(param) {
				classicurl.fetch().done(function() {
					classicurl.unset(param, {silent: true});
					classicurl.save({}, {replaceState: true});
				});
			},

            replaceState: function(attrs) {
            	classicurl.fetch().done(function() {
                    classicurl.set(attrs);
                    classicurl.replaceState(classicurl.encode(classicurl));
                });
            },

			_configureRoot: function() {
				return config.MRSPARKLE_ROOT_PATH.indexOf("/") === 0 ? config.MRSPARKLE_ROOT_PATH.substring(1) : config.MRSPARKLE_ROOT_PATH;
			}
		};
	}
);
