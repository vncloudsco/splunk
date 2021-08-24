define(
    [
        'underscore',
        'jquery',
        'routers/BaseListings',
        'collections/search/Jobs',
        'collections/services/authentication/Users',
        'collections/services/admin/workload_management/Status',
        'models/shared/EAIFilterFetchData',
        'views/jobmanager/Master'
    ],
    function(
        _,
        $,
        BaseListingsRouter,
        JobsCollection,
        UsersCollection,
        WorkloadManagementStatus,
        EAIFilterFetchData,
        JobManagerView
    ){
        return BaseListingsRouter.extend({
            initialize: function() {
                BaseListingsRouter.prototype.initialize.apply(this, arguments);
                this.setPageTitle(_('Job Manager').t());
                this.loadingMessage = _('Loading...').t();
                this.enableAppBar = false;
                this.deferreds.stateModelSet = $.Deferred();
                this.deferreds.workloadManagementStatus = $.Deferred();

                this.urlFilter = [
                   "^countPerPage$",
                   "^owner$",
                   "^app$",
                   "^jobStatus$",
                   "^sortDirection$",
                   "^sortKey$",
                   "^filter$"
                ];

                this.uiPrefsFilter = [
                    "^countPerPage$"
                ];
                
                this.fetchFilter = [
                    "^countPerPage$",
                    "^owner$",
                    "^app$",
                    "^jobStatus$",
                    "^sortDirection$",
                    "^sortKey$",
                    "^filter$",
                    "^offset$"
                ];

                this.stateModel.set({
                    sortKey: 'dispatch_time',
                    sortDirection: 'desc',
                    offset: 0,
                    owner: '', //owner='' in URL fetches admin by default which avoids calling the REST endpoint __raw/services/search/jobs twice when Owner dropdown is initialized.
                    jobStatus: '*',
                    fetching: true
                });

                //collections
                this.jobsCollection = new JobsCollection();
                this.usersCollection = new UsersCollection();
                this.workloadManagementStatus = new WorkloadManagementStatus();
            },
            initializeAndRenderViews: function() {
                var usersCollectionDeferred = this.usersCollection.fetch();

                if (this.deferreds.workloadManagementStatus.state() !== 'resolved') {
                    if (this.model.user.hasCapability('list_workload_pools')) {
                        this.workloadManagementStatus.fetch({
                            success: function () {
                                this.deferreds.workloadManagementStatus.resolve();
                            }.bind(this),
                            error: function () {
                                this.deferreds.workloadManagementStatus.resolve();
                            }.bind(this)
                        });
                    } else {
                        this.deferreds.workloadManagementStatus.resolve();
                    }
                }

                $.when(usersCollectionDeferred, this.deferreds.workloadManagementStatus).then(function(users) {
                    this.jobMangerView = new JobManagerView({
                        model: {
                            application: this.model.application,
                            appLocal: this.model.appLocal,
                            user: this.model.user,
                            serverInfo: this.model.serverInfo,
                            state: this.stateModel
                        },
                        collection: {
                            jobs: this.jobsCollection,
                            apps: this.collection.appLocals,
                            users: this.usersCollection,
                            workloadManagementStatus: this.workloadManagementStatus
                        }
                    });

                    this.jobMangerView.render().replaceContentsOf(this.pageView.$('.main-section-body'));

                    this.uiPrefsModel.entry.content.on('change', function() {
                        this.populateUIPrefs();
                    }, this);
                    
                    this.listenTo(this.jobsCollection, 'refresh remove', _.debounce(this.fetchListCollection));
                    
                    this.stateModel.on('change', _.debounce(function(){
                        var changedURLAttrs = this.stateModel.filterChangedByWildcards(this.urlFilter, {allowEmpty: true}),
                            changedUIPrefAttr = this.stateModel.filterChangedByWildcards(this.uiPrefsFilter, {allowEmpty: true});

                        if (changedURLAttrs && !_.isEmpty(changedURLAttrs)){
                            this.model.classicUrl.save($.extend({}, changedURLAttrs), { replaceState: true });
                        }

                        if (changedUIPrefAttr && !_.isEmpty(changedUIPrefAttr)){
                            // this trigger the change listener above that calls populateUIPrefs
                            this.uiPrefsModel.entry.content.set($.extend({}, changedUIPrefAttr));
                        }
                        
                        var changedFetchAttrs = this.stateModel.filterChangedByWildcards(this.fetchFilter, {allowEmpty: true});
                        if (changedFetchAttrs && !_.isEmpty(changedFetchAttrs)){
                            this.fetchListCollection();
                        }
                    }.bind(this)));
                    
                }.bind(this));
            },
            page: function(locale, app, page) {
                BaseListingsRouter.prototype.page.apply(this, arguments);
                $.when(this.uiPrefsDeferred, this.deferreds.appLocals).then(function() {
                    var currentApp = this.model.application.get('app');
                    this.stateModel.set({
                        app: this.collection.appLocals.findByEntryName(currentApp) ? currentApp : ''
                    });
                    this.stateModel.set($.extend({}, this.uiPrefsModel.entry.content.filterByWildcards(this.uiPrefsFilter, {allowEmpty: true})));
                    this.model.classicUrl.fetch({
                        success: function(model, response) {
                            var urlFilters = this.model.classicUrl.filterByWildcards(this.urlFilter, { allowEmpty: true });
                            // savedSearch is a legacy url param for job_manager that must be translated to filter
                            if (this.model.classicUrl.has("savedSearch")) {
                                var savedSearchFilter = 'label="' + this.model.classicUrl.get("savedSearch") + '"';
                                if (urlFilters.filter) {
                                    urlFilters.filter = urlFilters.filter + " " + savedSearchFilter;
                                } else {
                                    urlFilters.filter = savedSearchFilter;
                                }
                                this.model.classicUrl.save({ savedSearch: undefined, filter: urlFilters.filter }, { replaceState: true });
                            }
                            
                            this.stateModel.set($.extend({}, urlFilters));
                            this.deferreds.stateModelSet.resolve();
                        }.bind(this),
                        error: function(model, response) {
                            this.deferreds.stateModelSet.resolve();
                        }.bind(this)
                    });
                }.bind(this));
            },
            $whenFetchCollectionDependencies: function() {
                return $.when(this.deferreds.stateModelSet);
            },
            fetchListCollection: function() {
                this.stateModel.set('fetching', true);
                // SPL-119882 there are some cases with SHC where we get back empty jobs. Adding 
                // dispatchState=* to the filter filters out the empty jobs. 
                var filter = 'dispatchState=*';
                if (this.stateModel.get('filter')) {
                    filter = filter + ' AND ' + this.stateModel.get('filter');
                }
                this.jobsCollection.fetchNonAutoSummaryJobs({
                    data: {
                        app: this.stateModel.get('app'),
                        owner: this.stateModel.get('owner'),
                        jobStatus: this.stateModel.get('jobStatus'),
                        sortDirection: this.stateModel.get('sortDirection'),
                        sortKey: this.stateModel.get('sortKey').split(','),
                        search: filter,
                        count: this.stateModel.get('countPerPage'),
                        listDefaultActionArgs: true,
                        offset: this.stateModel.get('offset')
                    },
                    success: function(collection, response, options) {
                        // If we are trying to fetch a page that no longer exists the CollectionPaginator will
                        // do another fetch. Only set fetching to false once that fetch is complete. 
                        if (!(collection.length === 0 &&
                            collection.paging.get('offset') !== 0 &&
                            (collection.paging.get('offset') >= collection.paging.get('total')))) {
                            this.stateModel.set('fetching', false);
                        }
                    }.bind(this)
                });
            }
        });
    }
);