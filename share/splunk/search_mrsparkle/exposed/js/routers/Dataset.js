define(
    [
        'jquery',
        'underscore',
        'routers/Base',
        'collections/services/authorization/Roles',
        'collections/services/data/ui/Times',
        'models/Base',
        'models/classicurl',
        'models/datasets/PolymorphicDataset',
        'models/datasets/TableAST',
        'models/services/search/jobs/ResultJsonRows',
        'models/shared/fetchdata/ResultsFetchData',
        'models/shared/TimeRange',
        'models/search/Job',
        'mixins/dataset',
        'views/dataset/Master',
        'views/shared/documentcontrols/dialogs/permissions_dialog/Master',
        'util/general_utils',
        'util/time'
    ],
    function(
        $,
        _,
        BaseRouter,
        RolesCollection,
        TimesCollection,
        BaseModel,
        classicUrlModel,
        PolymorphicDatasetModel,
        ASTModel,
        ResultJsonRowsModel,
        ResultsFetchDataModel,
        TimeRangeModel,
        SearchJobModel,
        datasetMixin,
        DatasetView,
        PermissionsDialogView,
        generalUtils,
        timeUtils
    ) {
        return BaseRouter.extend({
            initialize: function() {
                BaseRouter.prototype.initialize.apply(this, arguments);
                this.fetchAppLocals = true;

                this.urlFilter = [
                    '^dataset\.display\..*',
                    '^dispatch.earliest_time$',
                    '^dispatch.latest_time$'
                ];

                this.userPrefsFilter = [
                    '^default_earliest_time$',
                    '^default_latest_time$'
                ];

                // Models:
                this.model.classicUrl = classicUrlModel;
                this.model.resultJsonRows = new ResultJsonRowsModel();
                this.model.searchJob = new SearchJobModel({}, {delay: SearchJobModel.DEFAULT_POLLING_INTERVAL, processKeepAlive: true, keepAliveInterval: SearchJobModel.DEFAULT_LONG_POLLING_INTERVAL});
                this.model.state = new BaseModel();
                this.model.ast = new ASTModel();
                // Datasets can't be used with real time searches
                this.model.timeRange = new (TimeRangeModel.extend({
                    defaults: {
                        enableRealTime: false
                    }
                }))();
                // this.model.dataset is created in fetchDataset, not here!

                // Collections:
                this.collection.roles = new RolesCollection();
                this.collection.times = new TimesCollection();

                // Deferreds:
                this.deferreds.preloadReplaced = $.Deferred();
                this.deferreds.rolesCollection = $.Deferred();
                this.deferreds.timesCollection = $.Deferred();

                this.setPageTitle(_('Dataset').t());
            },

            page: function(locale, app, page) {
                BaseRouter.prototype.page.apply(this, arguments);

                if (!this.shouldRender) {
                    // Deactivating cleans up the models and attempts to stop in flight requests
                    this.deactivate();
                }

                if (this.deferreds.rolesCollection.state() !== 'resolved') {
                    this.rolesCollectionBootstrap(this.deferreds.rolesCollection);
                }

                if (this.deferreds.timesCollection.state() !== 'resolved') {
                    this.timesCollectionBootstrap(this.deferreds.timesCollection);
                }

                // This deferred is resolved after we've fetched everything we need to activate the views
                this.bootstrapDeferred = $.Deferred();
                // This deferred finishes when we successfully fetch the dataset
                this.datasetInstantiatedDeferred = $.Deferred();

                $.when(this.deferreds.userPref).then(function() {
                    this.model.classicUrl.fetch({
                        success: function(model, response) {
                            // Remove any items that should not be permalinked before we syncFromClassicURL
                            this.model.classicUrl.set({
                                'dataset.display.offset': undefined,
                                // This is to prevent the user from trying to access data summary through the URL,
                                // which shouldn't be possible due to lookup table files not being compatible.
                                'dataset.display.mode': undefined
                            });

                            // Remove earliest/latest from the URL if either of them are real-time.
                            // (Datasets should not be run over real-time.)
                            if (timeUtils.isRealtime(this.model.classicUrl.get('dispatch.earliest_time')) ||
                                    timeUtils.isRealtime(this.model.classicUrl.get('dispatch.latest_time'))) {
                                this.model.classicUrl.set({
                                    'dispatch.earliest_time': undefined,
                                    'dispatch.latest_time': undefined
                                });
                            }

                            this.syncFromClassicURL();
                        }.bind(this)
                    });
                }.bind(this));

                // We can't initialize the view before all models are present (even if they haven't been fetched).
                // Because this.model.dataset is a PolymorphicDataset and thus we need to fetch URL attributes
                // before instantiating it, if we were to just wait for pageViewRendered, the dataset may not have
                // been instantiated yet. Therefore, we must wait for the dataset initialization as well.
                $.when(this.deferreds.pageViewRendered, this.datasetInstantiatedDeferred).then(function() {
                    if (this.shouldRender) {
                        this.initializeDatasetView();
                        $('.preload').replaceWith(this.pageView.el);
                        this.deferreds.preloadReplaced.resolve();
                    }
                }.bind(this));

                // Wait for all the relevant deferreds to finish, including our own bootstrapDeferred, before we activate
                $.when(
                    this.deferreds.appLocal,
                    this.deferreds.user,
                    this.deferreds.preloadReplaced,
                    this.deferreds.serverInfo,
                    this.deferreds.rolesCollection,
                    this.bootstrapDeferred
                ).then(function() {
                    this.datasetView.activate({ deep: true, skipRender: true });
                    this.activate();

                    if (this.shouldRender) {
                        this.datasetView.render().replaceContentsOf($('.main-section-body'));
                        $(document).trigger('rendered');

                        // When the user saves a dataset across the product, we can offer them the chance to edit
                        // permissions. If they click that link, they'll arrive at the viewing page (here) with a flag
                        // in the URL to display the permissions dialog. Handling that case here.
                        if (this.model.classicUrl.get('dialog') === 'permissions') {
                            // Now that we're gonna handle it, get rid of it in the URL, so if the user refreshes or
                            // something, they won't get the dialog again.
                            this.model.classicUrl.save({ dialog: undefined }, { replaceState: true });

                            this.permissionsDialog = new PermissionsDialogView({
                                model: {
                                    document: this.model.dataset,
                                    nameModel: this.model.dataset.entry,
                                    user: this.model.user,
                                    serverInfo: this.model.serverInfo,
                                    application: this.model.application
                                },
                                collection: this.collection.roles,
                                onHiddenRemove: true,
                                nameLabel: this.model.dataset.getDatasetDisplayType()
                            });

                            this.permissionsDialog.render().appendTo($('body'));
                            this.permissionsDialog.show();
                        }
                    }
                }.bind(this));
            },

            activate: function() {
                // We debounce here to make sure that if both earliest and latest both change, the function is only
                // called once instead of twice.
                this.model.dataset.entry.content.on('newSample change:dispatch.earliest_time change:dispatch.latest_time', _.debounce(this.loadNewJob, 0), this);

                // One of the job controls is a reload button which essentially clears the sid for a new job.
                this.model.searchJob.on('reload', this.loadNewJob, this);

                // When we save the job, we need to wait until the searchJob is prepared before registering search job
                // friends. In case it took a little while to prepare, this callback will catch that event and fire.
                this.model.searchJob.on('prepared', function() {
                    this.registerSearchJobFriends();
                }, this);

                // When the count/offset changes, we'll get new events through fetchResultJSONRows. We also need to
                // mediate the count/offset attributes to the URL.
                // NOTE: SearchResultsPaginator does set offset to 0 when count is changed, but if offset is already 0,
                // that change event won't fire. So, we need to also listen to change:count, and debounce so we don't
                // do this work multiple times.
                this.model.dataset.entry.content.on('change:dataset.display.count change:dataset.display.offset', _.debounce(function() {
                    this.fetchResultJSONRows();
                    this.populateClassicUrlFromDataset();
                }.bind(this), 0), this);
                
                this.model.dataset.on('updateCollection', function() {
                    /** HACK: The acceleration dialog cannot operate on a clone of the dataset. Thus we must clean up after it if it gets cancelled. **/
                    
                    this.model.dataset.fetch({
                        success: function(model, response) {
                            if (this.model.dataset.entry.content.acceleration) {
                                var accelerated = this.model.dataset.entry.content.acceleration.get("enabled");
                                this.model.dataset.entry.content.set('accelerated',  !!accelerated);
                            }
                        }.bind(this)
                    });
                }, this);
            },

            deactivate: function() {
                // Deactivate the dataset view tree first to make sure there are no side effects to cleaning up the models
                this.datasetView.deactivate({ deep: true });

                if (this.permissionsDialog) {
                    this.permissionsDialog.remove();
                }

                if (!this.shouldRender) {
                    this.model.state.off(null, null, this);
                    this.model.dataset.off(null, null, this);
                    this.model.dataset.entry.content.off(null, null, this);
                }

                this.model.searchJob.off(null, null, this);
                this.model.searchJob.clear();

                this.model.state.clear();

                this.model.dataset.clear({ setDefaults: true });
                this.model.ast.fetchAbort();
                this.model.resultJsonRows.fetchAbort();
                this.model.resultJsonRows.clear();
            },

            // Initialize the main dataset view, which will trigger all the initialization for all children.
            // All models are present at this stage.
            initializeDatasetView: function() {
                if (!this.datasetView) {
                    this.datasetView = new DatasetView({
                        model: {
                            application: this.model.application,
                            ast: this.model.ast,
                            config: this.model.config,
                            dataset: this.model.dataset,
                            resultJsonRows: this.model.resultJsonRows,
                            searchJob: this.model.searchJob,
                            serverInfo: this.model.serverInfo,
                            state: this.model.state,
                            timeRange: this.model.timeRange,
                            user: this.model.user
                        },
                        collection: {
                            apps: this.collection.appLocals,
                            roles: this.collection.roles,
                            times: this.collection.times
                        }
                    });
                }
            },

            // This happens after classicurl and user prefs models have been populated, so we can apply the
            // proper layering and fetch our own models.
            syncFromClassicURL: function() {
                var fetchDatasetDeferred = $.Deferred(),
                    fetchJobDeferred = $.Deferred(),
                    jobCreationDeferred = $.Deferred(),
                    astFetchDeferred = $.Deferred(),
                    timeRangeDeferred = $.Deferred(),
                    searchJobIdFromURL = this.model.classicUrl.get('sid'),
                    attrsFromUserPrefs = this.model.userPref.entry.content.filterByWildcards(this.userPrefsFilter),
                    attrsFromUrl = this.model.classicUrl.filterByWildcards(this.urlFilter, { allowEmpty: true });

                // We're going to layer in the user pref's default_earliest_time and default_latest_time and have those
                // map to dispatch.earliest_time and dispatch.latest_time, so we need to transfer those keys here.
                this.mediateUserPrefAttrs(attrsFromUserPrefs);

                // Fetch the job first, because it might have the attributes necessary to fetch the dataset.
                this.fetchJob(fetchJobDeferred, searchJobIdFromURL);

                $.when(fetchJobDeferred).then(function() {
                    // Now that the job and classicURL have been fetched, we can fetch the dataset. Hopefully, one
                    // of those two models will give us the attributes necessary to successfully fetch. If not, well,
                    // something went wrong, and the user will be given an error message.
                    this.fetchDataset(fetchDatasetDeferred);

                    $.when(fetchDatasetDeferred).then(function() {
                        // With the dataset fetched, fetching the corresponding AST is possible.
                        this.astBootstrap(astFetchDeferred);

                        $.when(astFetchDeferred).then(function() {
                            // Any attributes from the URL and user prefs should be layered in. URL beats user prefs.
                            // NOTE: Datasets don't usually have earliest/latest time, but we're setting it here just for
                            // convenience's sake, since the viewing/explore page has a time range picker, and we need
                            // some way to manage that state.
                            this.model.dataset.entry.content.set($.extend(true, {}, attrsFromUserPrefs, attrsFromUrl));

                            // Any attributes on the dataset that need to go in the URL will go here.
                            // URL overrides everything else, so that's why we're doing this after setting on entry.content.
                            this.populateClassicUrlFromDataset();

                            // We need to create a new search, so we'll call startNewSearch
                            if (this.model.searchJob.isNew()) {
                                this.startNewSearch(jobCreationDeferred);
                                // Else, job has already been created and fetched, so we're done here
                            } else {
                                jobCreationDeferred.resolve();
                            }

                            // We need the time range model for the time range picker
                            this.timeRangeBootstrap(timeRangeDeferred);

                            $.when(jobCreationDeferred, timeRangeDeferred).then(function() {
                                // If it's done preparing, we can registerSearchJobFriends immediately.
                                // Otherwise, the listener we set up in activate will handle the registration.
                                if (!this.model.searchJob.isPreparing()) {
                                    this.registerSearchJobFriends();
                                }

                                if (!this.model.searchJob.isNew()) {
                                    // Now that we have a successful job, we can mediate its attributes to the URL
                                    this.populateClassicUrlFromSearchJob();
                                    // Start polling, it's a long way to the bay!
                                    this.model.searchJob.startPolling();
                                }

                                // After the job is running properly, we're all done! Trigger to activate the page~
                                this.bootstrapDeferred.resolve();
                            }.bind(this));
                        }.bind(this));
                    }.bind(this));
                }.bind(this));
            },

            loadNewJob: function() {
                // Only force a page route if we have a search job already
                if (this.model.classicUrl.get('sid')) {
                    // Blow away the sid to force a new page route, and save relevant attributes to the URL
                    this.model.classicUrl.save(
                        {
                            sid: undefined,
                            'dispatch.earliest_time': this.model.dataset.entry.content.get('dispatch.earliest_time'),
                            'dispatch.latest_time': this.model.dataset.entry.content.get('dispatch.latest_time')
                        },
                        {
                            trigger: true
                        }
                    );
                }
            },

            mediateUserPrefAttrs: function(attrs) {
                generalUtils.transferKey(attrs, 'default_earliest_time', 'dispatch.earliest_time');
                generalUtils.transferKey(attrs, 'default_latest_time', 'dispatch.latest_time');
            },

            // Fetch the dataset. Depending on whether the search job exists, we can either grab the necessary
            // attributes to fetch a dataset from the search job or the URL.
            fetchDataset: function(fetchDatasetDeferred) {
                var datasetName,
                    datasetEAIType,
                    datasetEAIApp,
                    datasetEAIOwner,
                    datasetType,
                    datasetLinksAlternate,
                    splunkDPayload,
                    fetchSuccess;

                if (this.model.searchJob.isNew()) {
                    // If there's no valid sid in the URL, then we'll look to the URL for the right dataset attributes.
                    datasetName = this.model.classicUrl.get('name');
                    datasetEAIType = this.model.classicUrl.get('eaiType');
                    datasetEAIApp = this.model.classicUrl.get('eaiApp');
                    datasetEAIOwner = this.model.classicUrl.get('eaiOwner');
                    datasetType = this.model.classicUrl.get('datasetType');
                    datasetLinksAlternate = this.model.classicUrl.get('linksAlternate');
                } else {
                    // If we successfully fetched the existing search job, it should have the attributes on custom.
                    datasetName = this.model.searchJob.entry.content.custom.get('dataset.name');
                    datasetEAIType = this.model.searchJob.entry.content.custom.get('dataset.eaiType');
                    datasetEAIApp = this.model.searchJob.entry.content.custom.get('dataset.eaiApp');
                    datasetEAIOwner = this.model.searchJob.entry.content.custom.get('dataset.eaiOwner');
                    datasetType = this.model.searchJob.entry.content.custom.get('dataset.type');
                    datasetLinksAlternate = this.model.searchJob.entry.content.custom.get('dataset.linksAlternate');
                }

                splunkDPayload = {
                    entry: [{
                        acl: {
                            app: datasetEAIApp,
                            owner: datasetEAIOwner
                        },
                        content: {
                            // If we don't provide a eai:type, then we can't actually instantiate a PolymorphicDataset,
                            // and a JS error will actually be thrown. We still want the page to load if, for whatever
                            // reason, we can't read the dataset attributes properly, so provide a default here.
                            'eai:type': datasetEAIType || 'datamodel',
                            'dataset.type': datasetType
                        },
                        links: {
                            alternate: datasetLinksAlternate
                        },
                        name: datasetName
                    }]
                };

                // We'll be fetching this dataset every page route, but we don't want to reinitialize it every time,
                // so prevent that here.
                if (!this.model.dataset) {
                    // If we were to try to create a new PolymorphicDatasetModel without passing in these attributes,
                    // PolymorphicDatasetModel would blow up and yell at us! It wouldn't know how to create the right
                    // model. Therefore, we must call new on it here, and not in initialize of this router.
                    this.model.dataset = new PolymorphicDatasetModel(splunkDPayload, {
                        parse: true
                    });
                // If we already have the dataset, the attributes will have been cleared in deactivate, so we just
                // need to reapply the payload again.
                } else {
                    this.model.dataset.setFromSplunkD(splunkDPayload);
                }

                // Now that it's been instantiated, we can resolve the deferred so the views' initializes can happen.
                this.datasetInstantiatedDeferred.resolve();

                // Define the success handler for when the normal fetch comes back
                fetchSuccess = function() {
                    // If ANY of these attributes are empty, then fetchAsDataset won't do the right thing. Bail.
                    if (_.isEmpty(this.model.dataset.entry.get('name')) ||
                            _.isEmpty(this.model.dataset.entry.acl.get('owner')) ||
                            _.isEmpty(this.model.dataset.entry.acl.get('app')) ||
                            _.isEmpty(this.model.dataset.entry.content.get('eai:type'))) {
                        fetchDatasetDeferred.resolve();
                    } else {
                        // We instantiated the model with all the attributes it needs to do this fetch, and the object
                        // definitely exists (unless it's a DMO with no linksAlternate), so we can now call into
                        // the mixin to fetch the dataset from the consolidated endpoint.
                        $.when(this.model.dataset.fetchAsDataset({
                            app: this.model.application.get('app'),
                            owner: this.model.application.get('owner')
                        })).then(function() {
                            // These are default attributes for every dataset when viewing (not persisted attributes).
                            this.model.dataset.entry.content.set({
                                'dataset.display.count': '20',
                                'dataset.display.offset': '0',
                                'dataset.display.mode': datasetMixin.MODES.TABLE
                            });

                            fetchDatasetDeferred.resolve();
                        }.bind(this));
                    }
                }.bind(this);

                /*
                 This is a bit strange, but first we're going to fetch the dataset from its true endpoint (not going
                 through the mixin/fetchAsDataset). This is because if we fetchAsDataset with bad data, we'll make a
                 call to the datasets collection endpoint, and that endpoint will return 0 models (instead of 404ing!).
                 As of now, we're using Backbone 1.1.2, so the parse: false option isn't respected, and thus the model
                 (which doesn't exist) will attempt to be parsed, which will blow things up. So first we'll make sure
                 the entity exists from its true endpoint (which will 404 if it doesn't) before fetchingAsDataset.

                 Additionally, this has the side effect of fetching the exact ACL for this dataset, and thus we know
                 if the user can do things like delete. The combined listings endpoint doesn't give us that knowledge.

                 TODO: Data model objects cannot be singularly fetched, you need to fetch the entire data
                 TODO: model and then introspect it. This will mean if the user has a bad URL or something, we won't
                 TODO: be able to tell. Shelving for now. SPL-118294
                 */
                if (datasetLinksAlternate) {
                    this.model.dataset.fetch({
                        // The model exists - we can fetchAsDataset with confidence
                        success: fetchSuccess,

                        error: function() {
                            fetchDatasetDeferred.resolve();
                        }.bind(this)
                    });
                } else {
                    fetchSuccess();
                }
            },

            // Fetch the job from the sid in the URL
            fetchJob: function(fetchJobDeferred, searchJobIdFromUrl) {
                // If the URL contained an sid...
                if (searchJobIdFromUrl) {
                    this.model.searchJob.set('id', searchJobIdFromUrl);

                    // Try to fetch it with that id on the job
                    this.model.searchJob.fetch({
                        success: function(model, response) {
                            // Make sure the job doesn't define a real-time timerange, because that won't work here.
                            if (this.model.searchJob.isRealtime()) {
                                this.model.searchJob.clear();
                            }

                            fetchJobDeferred.resolve();
                        }.bind(this),

                        // The job no longer exists. Might be malformed, or expired, or just plain wrong.
                        error: function(model, response) {
                            // Get rid of it from the URL
                            this.model.classicUrl.save({ sid: undefined }, { replaceState: true });
                            // Unset it from the model, since it was bad
                            this.model.searchJob.unset('id');

                            fetchJobDeferred.resolve();
                        }.bind(this)
                    });
                // If it didn't, we just resolve
                } else {
                    fetchJobDeferred.resolve();
                }
            },

            // Start a new search for the job
            startNewSearch: function(jobCreationDeferred, options) {
                options = options || {};

                var fromSearch = this.model.dataset.getFromSearch(),
                    isTransforming = this.model.ast.isTransforming(),
                    // We're going to start all the job stuff on an inmem job, then copy it over on sync
                    newSearchModel = new SearchJobModel();

                newSearchModel.entry.content.custom.set({
                    // We're setting all the necessary attributes to fetch a dataset on the search job model's custom.
                    // This way, you can share a URL like /dataset?sid=<sid>, and as long as that SID is still
                    // valid, we can initialize and fetch the corresponding dataset.
                    'dataset.name': this.model.dataset.entry.get('name'),
                    'dataset.eaiType': this.model.dataset.entry.content.get('eai:type'),
                    'dataset.eaiApp': this.model.dataset.entry.acl.get('app'),
                    'dataset.eaiOwner': this.model.dataset.entry.acl.get('owner'),
                    'dataset.type': this.model.dataset.entry.content.get('dataset.type'),
                    'dataset.linksAlternate': this.model.dataset.getType() !== 'datamodel' ? this.model.dataset.entry.links.get('alternate') : undefined
                });

                // This is where we set up listeners to handle when the save comes back
                this.addNewSearchListeners(newSearchModel, jobCreationDeferred);

                newSearchModel.save({}, {
                    data: {
                        // The search on the dataset explorer page doesn't have a diversity
                        search: fromSearch,
                        earliest_time: this.model.dataset.entry.content.get('dispatch.earliest_time'),
                        latest_time: this.model.dataset.entry.content.get('dispatch.latest_time'),
                        auto_cancel: SearchJobModel.DEFAULT_AUTO_CANCEL,
                        status_buckets: 300,
                        ui_dispatch_app: this.model.application.get('app'),
                        preview: true,
                        adhoc_search_level: 'smart',
                        app: this.model.application.get('app'),
                        owner: this.model.application.get('owner'),
                        sample_seed: undefined,
                        sample_ratio: options.sample_ratio || this.model.dataset.getDispatchRatio({ isTransforming: isTransforming }),
                        indexedRealtime: this.model.dataset.entry.content.get('dispatch.indexedRealtime'),
                        auto_finalize_ec: this.model.dataset.getEventLimit({ isTransforming: isTransforming }),
                        provenance: 'UI:Dataset'
                    }
                });
            },

            // Sets up sync/error listeners on the inmem job for proxying over to this.model.searchJob
            addNewSearchListeners: function(newSearchModel, jobCreationDeferred) {
                newSearchModel.on('sync', function(model, response, options) {
                    var messages;

                    // Clear out any stale data from the real job
                    this.model.searchJob.clear();
                    // Copy all the contents of the inmem job to this.model.searchJob
                    this.model.searchJob.setFromSplunkD(newSearchModel.toSplunkD());

                    // I believe the error model isn't handled in the toSplunkD() call, so we have to do
                    // it manually here. We only care about the messages.
                    if (model.error.get('messages')) {
                        messages = model.error.get('messages');
                    }
                    if (messages) {
                        this.model.searchJob.error.set({
                            messages: messages
                        });
                    }

                    // Turn off all listeners on the inmem model, now that we're done with it
                    newSearchModel.off();
                    jobCreationDeferred.resolve();
                }, this);

                newSearchModel.on('error', function(model, response, options) {
                    // If the inmem search job errors, we'll consider this.model.searchJob to be in error as well
                    this.model.searchJob.trigger('error', this.model.searchJob, response);

                    // Turn off all listeners on the inmem model, now that we're done with it
                    model.off();
                    jobCreationDeferred.resolve();
                }, this);
            },

            // Any callbacks that should fire when new search results come in should be registered here
            registerSearchJobFriends: function() {
                // We'll call fetchResultJsonRows as we get progress to populate this.model.resultJsonRows.
                if (this.model.searchJob.isReportSearch()) {
                    this.model.searchJob.registerJobProgressLinksChild(SearchJobModel.RESULTS_PREVIEW, this.model.resultJsonRows, this.fetchResultJSONRows, this);
                } else {
                    // If the search is not a transforming one, then the true place to get the events is the events endpoint
                    this.model.searchJob.registerJobProgressLinksChild(SearchJobModel.EVENTS, this.model.resultJsonRows, this.fetchResultJSONRows, this);
                }
            },

            // Populate this.model.resultJsonRows as the job progresses
            fetchResultJSONRows: function(options) {
                options = options || {};

                if (this.model.searchJob.entry.content.get('isPreviewEnabled') || this.model.searchJob.isDone()) {
                    var fetchDataModel = new ResultsFetchDataModel(),
                        columnsList = this.model.dataset.getFlattenedFieldsObj().fields.join(','),
                        data = $.extend(
                            fetchDataModel.toJSON(),
                            {
                                show_metadata: false,
                                include_null_fields: true,
                                field_list: columnsList,
                                time_format: '%s.%Q',
                                count: this.model.dataset.entry.content.get('dataset.display.count'),
                                offset: this.model.dataset.entry.content.get('dataset.display.offset')
                            }
                        );

                    $.extend(true, data, options);

                    this.model.resultJsonRows.safeFetch({
                        data: data
                    });
                }
            },

            // This mediates the specified attrs of the dataset to the URL
            populateClassicUrlFromDataset: function() {
                var attrs = {
                    'dataset.display.count': this.model.dataset.entry.content.get('dataset.display.count'),
                    'dataset.display.offset': this.model.dataset.entry.content.get('dataset.display.offset')
                };

                this.model.classicUrl.save(attrs, {
                    replaceState: true
                });
            },

            // This mediates attributes of the search job to the URL
            populateClassicUrlFromSearchJob: function() {
                var attrs = {
                    'sid': this.model.searchJob.entry.content.get('sid'),
                    'dispatch.earliest_time': this.model.searchJob.getDispatchEarliestTimeOrAllTime(),
                    'dispatch.latest_time': this.model.searchJob.getDispatchLatestTimeOrAllTime(),
                    'name': this.model.searchJob.entry.content.custom.get('dataset.name'),
                    'eaiType': this.model.searchJob.entry.content.custom.get('dataset.eaiType'),
                    'eaiApp': this.model.searchJob.entry.content.custom.get('dataset.eaiApp'),
                    'eaiOwner': this.model.searchJob.entry.content.custom.get('dataset.eaiOwner'),
                    'datasetType': this.model.searchJob.entry.content.custom.get('dataset.type'),
                    'linksAlternate': this.model.searchJob.entry.content.custom.get('dataset.linksAlternate')
                };

                this.model.classicUrl.save(attrs, {
                    replaceState: true
                });
            },

            // Fetches the roles collection, which is necessary for editing permissions on the dataset
            rolesCollectionBootstrap: function(rolesCollectionDeferred) {
                this.collection.roles.fetch({
                    data: {
                        app: this.model.application.get('app'),
                        owner: this.model.application.get('owner'),
                        count: -1
                    },

                    success: function(model, response) {
                        rolesCollectionDeferred.resolve();
                    }.bind(this),

                    error: function(model, response) {
                        rolesCollectionDeferred.resolve();
                    }.bind(this)
                });
            },

            // Fetches the times collection, which powers the presets in the time range picker
            timesCollectionBootstrap: function(timesCollectionDeferred) {
                this.collection.times.fetch({
                    data: {
                        app: this.model.application.get('app'),
                        owner: this.model.application.get('owner'),
                        count: -1
                    },

                    success: function(model, response) {
                        timesCollectionDeferred.resolve();
                    }.bind(this),

                    error: function(model, response) {
                        timesCollectionDeferred.resolve();
                    }.bind(this)
                });
            },

            // Fetch the AST for the current command
            astBootstrap: function(astFetchDeferred) {
                var search = this.model.dataset.getFromSearch();

                // check and see if this is the same search we have already fetched an AST for
                if ((this.model.ast.get('spl') === search) && this.model.ast.get('ast')) {
                    astFetchDeferred.resolve();
                    return;
                }

                // ensure the AST is ready to be fetched
                this.model.ast.set({
                    spl: search,
                    ast: undefined
                });

                this.model.ast.fetch({
                    data: {
                        app: this.model.application.get('app'),
                        owner: this.model.application.get('owner')
                    },
                    success: function(model, response) {
                        astFetchDeferred.resolve();
                    }.bind(this),
                    error: function(model, response) {
                        astFetchDeferred.resolve();
                    }.bind(this)
                });
            },

            timeRangeBootstrap: function(timeRangeDeferred) {
                this.model.timeRange.save(
                    {
                        'earliest': this.model.dataset.entry.content.get('dispatch.earliest_time'),
                        'latest': this.model.dataset.entry.content.get('dispatch.latest_time')
                    },
                    {
                        validate: false,
                        success: function(model, response) {
                            timeRangeDeferred.resolve();
                        }.bind(this),
                        error: function(model, response) {
                            timeRangeDeferred.resolve();
                        }.bind(this)
                    }
                );
            }
        });
    }
);
