define([
        'jquery',
        'underscore',
        'backbone',
        'models/shared/Application',
        'models/services/AppLocal',
        'models/config',
        'collections/services/configs/Visualizations',
        'models/services/server/ServerInfo',
        'models/services/data/ui/Nav',
        'models/services/data/UserPrefGeneral',
        'models/shared/User',
        'models/services/data/ui/Tour',
        'models/services/configs/Visualization',
        'models/services/configs/Web',
        'models/shared/UpdateChecker',
        'collections/services/data/ui/Tours',
        'collections/services/AppLocals',
        'collections/services/data/ui/Managers',
        'views/shared/Page',
        'util/csrf_protection',
        'util/ajax_no_cache',
        'util/ajax_logging',
        'util/splunkd_utils',
        'splunk.util',
        'util/console',
        'splunk.error',
        'uri/route',
        'util/general_utils',
        'models/classicurl'
    ],
    function(
        $,
        _,
        Backbone,
        ApplicationModel,
        AppLocalModel,
        configModel,
        VisualizationsCollection,
        ServerInfoModel,
        AppNavModel,
        UserPrefModel,
        UserModel,
        TourModel,
        VisualizationModel,
        WebConfModel,
        UpdateCheckerModel,
        ToursCollection,
        AppLocalsCollection,
        ManagersCollection,
        PageView,
        csrf_protection,
        ajaxNoCache,
        ajaxLogging,
        splunkd_utils,
        splunkUtils,
        console,
        splunkError,
        route,
        generalUtils,
        classicurl
    ) {
        /**
         * @namespace routers
         */
        /**
         * @constructor
         * @memberOf routers
         * @name Base
         * @extends {Backbone.Router}
         */
    return Backbone.Router.extend(/** @lends routers.Base.prototype */{
        routes: {
            ':locale/app/:app/:page': 'page',
            ':locale/app/:app/:page/': 'page',
            ':locale/app/:app/:page/*splat': 'page',
            ':locale/manager/:app/:page': 'page',
            ':locale/manager/:app/:page/': 'page',
            ':locale/manager/:app/:page/*splat': 'page',
            '*root/:locale/app/:app/:page': 'pageRooted',
            '*root/:locale/app/:app/:page/': 'pageRooted',
            '*root/:locale/app/:app/:page/*splat': 'pageRooted',
            '*root/:locale/manager/:app/:page': 'pageRooted',
            '*root/:locale/manager/:app/:page/': 'pageRooted',
            '*root/:locale/manager/:app/:page/*splat': 'pageRooted',
            '*splat': 'notFound'
        },
        initialize: function(options) {
            options = $.extend({model:{}, collection:{}, deferreds: {}}, options);
            //add __splunk__ to global namespace
            if (window.location.href.indexOf('debug=1')!=-1) {
                (function(exports) {
                    this.__splunk__ = exports;
                })(this);
            }
            //configuration
            this.enableSplunkBar = true;
            this.enableAppBar = true;
            this.enablePageView = true;
            this.showAppsList = true;

            this.fetchUser = true;
            this.fetchAppLocals = false;
            this.fetchAppLocal = true;
            this.fetchUserPref = false;
            this.fetchServerInfo = true;
            this.fetchManagers = true;
            // Pages that display multiple visualizations (search, dashboards) should set this flag.
            this.fetchVisualizations = false;
            // Pages that need only the visualizations.conf info but not the formatter schema for each
            // external visualization (e.g. only labels and icons for save flows) should set this to false.
            this.fetchVisualizationFormatters = true;
            // Allows pages to configure whether only "selectable" external visualizations (i.e. those that
            // should be available for user selection) should be fetched, or all enabled visualizations.
            this.requireSelectableVisualizations = true;

            this.loadingMessage = '';

            // Tracks how many times the page function has been called
            this.pageViewCount = 0;

            //models
            this.model = {};
            // Some routers have used camelCase, while others have used lowercase
            // for this model, so aliasing both minimize impact of adding this to the base router.
            this.model.classicurl = options.model.classicurl || classicurl;
            this.model.classicUrl = this.model.classicurl;
            this.model.config = options.model.config || configModel;
            this.model.application = options.model.application || new ApplicationModel({owner: this.model.config.get('USERNAME')});
            this.model.appNav = options.model.appNav || new AppNavModel();
            this.model.appLocal = options.model.appLocal || new AppLocalModel();
            this.model.userPref = options.model.userPref || new UserPrefModel();
            this.model.serverInfo = options.model.serverInfo || new ServerInfoModel();
            this.model.tour = options.model.tour || new TourModel();
            this.model.web = options.model.web || new WebConfModel({id: 'settings'});
            this.model.updateChecker = options.model.updateChecker || new UpdateCheckerModel();

            //collections
            this.collection = {};
            this.collection.appLocals = options.collection.appLocals || new AppLocalsCollection();
            this.collection.appLocalsUnfiltered = options.collection.appLocalsUnfiltered || new AppLocalsCollection();
            this.collection.appLocalsUnfilteredAll = options.collection.appLocalsUnfilteredAll || new AppLocalsCollection();
            this.collection.managers = options.collection.managers || new ManagersCollection();
            this.collection.tours = options.collection.tours || new ToursCollection();
            this.collection.visualizations = new VisualizationsCollection();

            // the user model is a special case that also needs the apps collection
            this.model.user = options.model.user || new UserModel({}, {
                serverInfoModel: this.model.serverInfo,
                appLocalsCollection: this.collection.appLocals
            });

            //views
            this.views = {};

            //deferreds
            this.deferreds = options.deferreds || {};
            this.deferreds.user = options.deferreds.user || $.Deferred();
            this.deferreds.appNav = options.deferreds.appNav || $.Deferred();
            this.deferreds.appLocal = options.deferreds.appLocal || $.Deferred();
            this.deferreds.appLocals = options.deferreds.appLocals || $.Deferred();
            this.deferreds.appLocalsUnfiltered = options.deferreds.appLocalsUnfiltered || $.Deferred();
            this.deferreds.appLocalsUnfilteredAll = options.deferreds.appLocalsUnfilteredAll || $.Deferred();
            this.deferreds.userPref = options.deferreds.userPref || $.Deferred();
            this.deferreds.serverInfo = options.deferreds.serverInfo || $.Deferred();
            this.deferreds.web = options.deferreds.web || $.Deferred();
            this.deferreds.pageViewRendered = options.deferreds.pageViewRendered || $.Deferred();
            this.deferreds.tour = options.deferreds.tour || $.Deferred();
            this.deferreds.managers = options.deferreds.managers || $.Deferred();
            this.deferreds.application = options.deferreds.application || $.Deferred();
            this.deferreds.visualizations = options.deferreds.visualizations || $.Deferred();
            this.deferreds.updateChecker = options.deferreds.updateChecker || $.Deferred();

            //history
            if(options.history){
                this.history = options.history;
            }else{
                this.history = {};
                _.each(this.routes, function(value) {
                    this.on('route:' + value, function() {
                        this.history[window.location.pathname] = true;
                    }, this);
                }, this);
            }
        },
        page: function(locale, app, page) {
            this.pageViewCount++;

            this.shouldRender = !this.history[window.location.pathname];
            this.model.application.set({
                locale: locale,
                app: app,
                page: page.split('?')[0]
            });
            this.deferreds.application.resolve();

            this.bootstrapAppNav();
            this.bootstrapAppLocal();
            this.bootstrapServerInfo();
            this.bootstrapWebConf();
            this.bootstrapTour();
            this.bootstrapUserPref();
            this.bootstrapManagers();
            this.bootstrapVisualizations();
            this.applyPageUrlOptions();
            this.bootstrapUpdateChecker();

            if (this.enablePageView && !this.pageView) {
                this.$whenPageViewDependencies().then(function(){
                    this.pageView = new PageView({
                        splunkBar: this.enableSplunkBar,
                        showAppsList: this.showAppsList,
                        showAppNav: this.enableAppBar,
                        section: this.model.application.get('page'),
                        loadingMessage: this.loadingMessage,
                        model: {
                            application: this.model.application,
                            appNav: this.model.appNav,
                            appLocal: this.model.appLocal,
                            user: this.model.user,
                            serverInfo: this.model.serverInfo,
                            config: this.model.config,
                            tour: this.model.tour,
                            userPref: this.model.userPref,
                            web: this.model.web,
                            updateChecker: this.model.updateChecker
                        },
                        collection: {
                            apps: this.collection.appLocals,
                            tours: this.collection.tours,
                            managers: this.collection.managers,
                            appsVisible: this.collection.appLocalsUnfiltered,
                            appsAll: this.collection.appLocalsUnfilteredAll
                        },
                        deferreds: {
                            tour: this.deferreds.tour,
                            pageViewRendered: this.deferreds.pageViewRendered
                        }
                    });
                    this.pageView.render();
                    this.deferreds.pageViewRendered.resolve();
                }.bind(this));
            }
        },
        pageRooted: function(root, locale, app, page) {
            this.model.application.set({
                root: root
            }, {silent: true});
            this.page(locale, app, page);
        },
        notFound: function() {
            console.log('Page not found.');
        },
        $whenPageViewDependencies: function() {
            this.bootstrapUser();
            this.bootstrapAppLocals();
            return $.when(
                this.deferreds.user,
                this.deferreds.appLocals,
                this.deferreds.appLocal,
                this.deferreds.appNav,
                this.deferreds.serverInfo,
                this.deferreds.tour,
                this.deferreds.managers,
                this.fetchVisualizations ? this.deferreds.visualizations : $.Deferred().resolve(),
                this.deferreds.web,
                this.deferreds.updateChecker
            );
        },
        bootstrapAppNav: function() {
            var appNavPartialData;
            if (this.deferreds.appNav.state() !== 'resolved') {
                if (this.enableAppBar) {
                    appNavPartialData = __splunkd_partials__['/appnav'];
                    if (appNavPartialData) {
                        this.model.appNav.setFromSplunkD(appNavPartialData);
                        this.deferreds.appNav.resolve();
                    } else {
                        this.model.appNav.fetch({
                            data: {
                                app: this.model.application.get("app"),
                                owner: this.model.application.get("owner")
                            },
                            success: function(model, response) {
                                this.deferreds.appNav.resolve();
                            }.bind(this),
                            error: function(model, response) {
                                this.deferreds.appNav.resolve();
                            }.bind(this)
                        });
                    }
                } else {
                    this.model.appNav = undefined;
                    this.deferreds.appNav.resolve();
                }
            }
        },
        /**
         * Allows for overrides of the appsLocalFetchData.
         * For example, in appsLocal page, disabled apps are also needed.
         *
         * @returns a JSON data object
         */
        appLocalsFetchData: function() {
            return {
                sort_key: 'name',
                sort_dir: 'asc',
                app: '-' ,
                owner: this.model.application.get('owner'),
                search: 'disabled=0',
                count: -1
            };
        },
        bootstrapAppLocals: function() {
            /*
             appLocalsUnfilteredAll - all not disabled
             appLocalsUnfiltered - all not disabled AND visible
             appLocals - all not disabled AND visible AND not 'launcher'
             */
            if (this.deferreds.appLocals.state() !== 'resolved') {
                if (this.fetchAppLocals || this.fetchVisualizations) {
                    //fetch all apps in one shot filtering out launcher on success
                    this.collection.appLocals.fetch({
                        data: this.appLocalsFetchData(),
                        success: function(collection, response) {
                            //This collection includes visible and hidden apps
                            this.collection.appLocalsUnfilteredAll.set(collection.models);

                            //Filter out the invisible apps
                            var onlyVisibleAppsCollection = new AppLocalsCollection();
                            onlyVisibleAppsCollection.set(collection.listVisibleApps());

                            //Set the appLocals collection to only show visible apps and remove launcher app
                            collection.set(onlyVisibleAppsCollection.models);
                            collection.removeLauncherApp();

                            //Set unfiltered so that it only shows visible apps
                            this.collection.appLocalsUnfiltered.set(onlyVisibleAppsCollection.models);
                            this.deferreds.appLocals.resolve();
                            this.deferreds.appLocalsUnfiltered.resolve();
                            this.deferreds.appLocalsUnfilteredAll.resolve();
                        }.bind(this),
                        error: function(collection, response) {
                            this.deferreds.appLocals.resolve();
                            this.deferreds.appLocalsUnfiltered.resolve();
                            this.deferreds.appLocalsUnfilteredAll.resolve();
                        }.bind(this)
                    });
                } else {
                    this.collection.appLocals = undefined;
                    this.collection.appLocalsUnfiltered = undefined;
                    this.deferreds.appLocals.resolve();
                    this.deferreds.appLocalsUnfiltered.resolve();
                    this.deferreds.appLocalsUnfilteredAll.resolve();
                }
            }
        },
        bootstrapTour :function() {
            if (this.deferreds.tour.state() !== 'resolved') {
                this.collection.tours.fetch({
                    data: {
                        app: this.model.application.get("app"),
                        owner: this.model.application.get("owner"),
                        count: -1
                    },
                    success: function(collection, response) {
                        this.setTourModel();
                    }.bind(this),
                    error: function(collection, response) {
                        this.deferreds.tour.resolve();
                    }.bind(this)
                });
            } else {
                this.deferreds.tour.resolve();
            }
        },
        setTourModel: function() {
            var tourCheck = this.model.classicurl.get('tour'),
                autoTour = false,
                tour;

            if (tourCheck) {
                // Check for a tour instantiation via querystring
                tour = this.collection.tours.getTourModel(tourCheck);
                this._removeQSVar('tour');
            } else {
                // Check if is Light and if Light global tour has been viewed
                if (this.model.serverInfo.isLite()) {
                    var lightTour = this.collection.tours.getTourModel('light-product-tour'),
                        app = this.model.application.get('app');
                    if (app === 'search' && lightTour && !lightTour.viewed()) {
                        tour = lightTour;
                    }
                }

                // If not Light tour, check for view specific auto tour
                if (!tour) {
                    var tourName = this.model.application.get('page') + '-tour',
                        productType = this.model.serverInfo.getProductType(),
                        instanceType = this.model.serverInfo.getInstanceType(),
                        envTourName = tourName + ':' + productType + ((instanceType) ? ':' + instanceType : '');

                    tour = this.collection.tours.getTourModel(envTourName);
                }

                if (tour) {
                    autoTour = true;
                    tour.entry.content.set('autoTour', autoTour);
                }
            }

            if (tour && tour.isValidTour()) {
                var name = tour.getName(),
                    tourApp = tour.getTourApp(),
                    owner = this.model.application.get('owner');

                this.model.tour.bootstrap(this.deferreds.tour, tourApp, owner, name, autoTour);
                this.model.tour.on('viewed', function() {
                    this.updateTour();
                }, this);
            } else {
                this.model.tour = null;
                this.deferreds.tour.resolve();
            }
        },
        updateTour: function() {
            var data = {};
            if (this.model.tour.isNew()) {
                data = {
                    app: this.model.tour.getTourApp(),
                    owner: this.model.application.get('owner')
                };
            }
            this.model.tour.save({}, {
                data: data
            });
        },
        bootstrapAppLocal: function() {
            var app, appLocalPartialData;
            if (this.deferreds.appLocal.state() !== 'resolved') {
                app = this.model.application.get('app');

                if (this.fetchAppLocal && (app !== 'system')) {
                    appLocalPartialData = __splunkd_partials__['/servicesNS/nobody/system/apps/local/' + encodeURIComponent(app)];
                    if (appLocalPartialData) {
                        this.model.appLocal.setFromSplunkD(appLocalPartialData);
                        this.deferreds.appLocal.resolve();
                    } else {
                        this.model.appLocal.fetch({
                            url: splunkd_utils.fullpath(this.model.appLocal.url + "/" + encodeURIComponent(app)),
                            data: {
                                app: app,
                                owner: this.model.application.get("owner")
                            },
                            success: function(model, response) {
                                this.deferreds.appLocal.resolve();
                            }.bind(this),
                            error: function(model, response) {
                                this.deferreds.appLocal.resolve();
                            }.bind(this)
                        });
                    }
                } else {
                    this.model.appLocal = undefined;
                    this.deferreds.appLocal.resolve();
                }
            }
        },
        bootstrapServerInfo: function() {
            var serverInfoPartialData,
                fromLogin = splunkUtils.loginCheck();

            if (this.deferreds.serverInfo.state() !== 'resolved') {
                if (this.fetchUser || this.fetchServerInfo) {
                    serverInfoPartialData = __splunkd_partials__['/services/server/info'];
                    if (serverInfoPartialData && !fromLogin) {
                        this.model.serverInfo.setFromSplunkD(serverInfoPartialData);
                        this.deferreds.serverInfo.resolve();
                    } else {
                        this.model.serverInfo.fetch({
                            success: function(model, response) {
                                this.deferreds.serverInfo.resolve();
                            }.bind(this),
                            error: function(model, response) {
                                this.deferreds.serverInfo.resolve();
                            }.bind(this)
                        });
                    }
                } else {
                    this.model.serverInfo = undefined;
                    this.deferreds.serverInfo.resolve();
                }
            }
        },
        bootstrapUserPref: function() {
            if (this.deferreds.userPref.state() !== 'resolved') {
                this.model.userPref.fetch({
                    success: function(model, response) {
                        this.deferreds.userPref.resolve();
                    }.bind(this),
                    error: function(model, response) {
                        this.deferreds.userPref.resolve();
                    }.bind(this)
                });
            }
        },
        bootstrapWebConf: function() {
            if (this.deferreds.web.state() !== 'resolved') {
                this.model.web.fetch({
                    success: function(model, response) {
                        this.deferreds.web.resolve();
                    }.bind(this),
                    error: function(model, response) {
                        this.deferreds.web.resolve();
                    }.bind(this)
                });
            }
        },
        bootstrapUpdateChecker: function() {
            $.when(this.deferreds.web, this.deferreds.serverInfo, this.deferreds.userPref, this.deferreds.user).then(function() {
                var fromLogin = splunkUtils.loginCheck(),
                    canPhonehome = splunkUtils.normalizeBoolean(this.model.web.entry.content.get('updateCheckerBaseURL')),
                    canRenderSplunkMessages = canPhonehome && !this.model.serverInfo.isCloud();

                if (fromLogin) {
                    var uid = splunkUtils.getCookie('splunkweb_uid');
                    var canRenderMessagesCheck = splunkUtils.normalizeBoolean(this.model.userPref.entry.content.get('render_version_messages'));
                    if (canRenderMessagesCheck != canRenderSplunkMessages) {
                        this.model.userPref.entry.content.set('render_version_messages', canRenderSplunkMessages);
                        this.model.userPref.save({});
                    }
                    splunkUtils.deleteCookie('login');
                    splunkUtils.deleteCookie('splunkweb_uid');

                    if (canPhonehome) {
                        this.model.updateChecker.set('useQuickdraw', true);
                        this.model.updateChecker.fetchHelper(
                            this.model.serverInfo,
                            this.model.web,
                            this.model.application,
                            this.model.user,
                            'login',
                            uid,
                            {timeout: 5000})
                            .error(function() {
                                // No internet connection or user changed
                                // the updateCheckerBaseURL to something funky.
                                this.model.updateChecker.set('useQuickdraw', false);
                                console.error('Update check endpoint is unreachable.');
                            }.bind(this));
                    } else {
                        // User has removed updateCheckerBaseURL
                        console.error('Update check url is empty. Aborting update check to quickdraw.');
                    }
                }
                this.deferreds.updateChecker.resolve();
            }.bind(this));
        },
        bootstrapUser: function() {
            if (this.deferreds.user.state() !== 'resolved') {
                if (this.fetchUser) {
                    this.model.user.fetch({
                        url: splunkd_utils.fullpath(this.model.user.url + "/" + encodeURIComponent(this.model.application.get("owner"))),
                        data: {
                            app: this.model.application.get("app"),
                            owner: this.model.application.get("owner")
                        },
                        success: function(model, response) {
                            $.when(this.deferreds.serverInfo).then(function() {
                                this.deferreds.user.resolve();
                            }.bind(this));
                        }.bind(this),
                        error: function(model, response) {
                            $.when(this.deferreds.serverInfo).then(function() {
                                this.deferreds.user.resolve();
                            }.bind(this));
                        }.bind(this)
                    });
                } else {
                    this.model.user = undefined;
                    this.deferreds.user.resolve();
                }
            }
        },
        bootstrapManagers: function() {
            if (this.deferreds.managers.state() !== 'resolved') {
                if (this.fetchManagers) {
                    this.collection.managers.fetch({
                        data: {
                            app: "-",
                            owner: this.model.application.get("owner"),
                            count: 0,
                            digest: 1
                        },
                        success: function(collection, response, options) {
                            this.deferreds.managers.resolve();
                        }.bind(this),
                        error: function(collection, response, options) {
                            this.deferreds.managers.resolve();
                        }.bind(this)
                    });
                } else {
                    this.collection.managers = undefined;
                    this.deferreds.managers.resolve();
                }
            }
        },
        bootstrapVisualizations: function(data) {
            if (this.fetchVisualizations) {
                var vizDfd = this.deferreds.visualizations;
                if (vizDfd.state() !== 'resolved') {
                    var filterSearch = this.requireSelectableVisualizations ?
                            VisualizationModel.SELECTABLE_FILTER : VisualizationModel.ENABLED_FILTER;
                    $.when(this.deferreds.appLocals).done(function() {
                        this.collection.visualizations.fetch({
                            includeFormatter: this.fetchVisualizationFormatters,
                            appLocalsCollection: this.collection.appLocalsUnfilteredAll,
                            data: _.extend(
                                {
                                    search: filterSearch,
                                    count: 0
                                },
                                this.model.application.pick('app', 'owner'),
                                data
                            ),
                            success: function(collection, response, options) {
                                vizDfd.resolve();
                            }.bind(this),
                            error: function(collection, response, options) {
                                vizDfd.resolve();
                            }.bind(this)
                        });
                    }.bind(this))
                    .fail(function(){
                        vizDfd.resolve();
                    });
                } else {
                    this.collection.visualizations = undefined;
                    vizDfd.resolve();
                }
            }
        },
        _removeQSVar: function(qsVar) {
            this.model.classicurl.fetch({
                success: function(model, response) {
                    this.model.classicurl.unset(qsVar);
                    this.model.classicurl.save({}, {replaceState: true});
                }.bind(this)
            });
        },
        // convenience method for subclasses to update the page <title>
        // as browser compatibility issues arise, they can be encapsulated here
        setPageTitle: function(title) {
            this.deferreds.serverInfo.done(function(){
                var version = this.model.serverInfo.getVersion() || _('N/A').t();
                var isLite = this.model.serverInfo.isLite();
                document.title = splunkUtils.sprintf(_(title).t()+' | '+_('Splunk %s %s').t(),isLite ? 'Light' : '', version);
            }.bind(this));
        },
        applyPageUrlOptions: function() {
            var that = this;
            // Note: classicUrl.fetch is always synchronous
            this.model.classicurl.fetch({
                success: function() {
                    var availablePageOptions = [
                        'hideSplunkBar',
                        'hideAppBar',
                        'hideAppsList',
                        'hideChrome'
                    ];
                    var pageOptions = that.model.classicurl.pick(availablePageOptions);
                    _.forEach(pageOptions, function(value, key) {
                        pageOptions[key] = generalUtils.normalizeBoolean(value, {
                            'default': true
                        });
                    });
                    if (pageOptions.hideSplunkBar) {
                        that.enableSplunkBar = false;
                    }
                    if (pageOptions.hideAppBar) {
                        that.enableAppBar = false;
                    }
                    if (pageOptions.hideAppsList) {
                        that.showAppsList = false;
                    }
                    if (pageOptions.hideChrome) {
                        that.enableSplunkBar = false;
                        that.enableAppBar = false;
                    }
                }
            });
        }
    });
});
