define(
    [
        'jquery',
        'underscore',
        'backbone',
        'routers/Base',
        'models/classicurl',
        'models/monitoringconsole/splunk_health_check/Conductor',
        'models/monitoringconsole/splunk_health_check/DmcConfigs',
        'collections/monitoringconsole/splunk_health_check/Tasks',
        'collections/services/AppLocals',
        'views/monitoringconsole/splunk_health_check/Master',
        'views/shared/Paywall'
    ],
    function(
        $,
        _,
        Backbone,
        BaseRouter,
        classicurl,
        ConductorModel,
        DmcConfigsModel,
        TasksCollection,
        AppLocalsCollection,
        MasterView,
        Paywall
    ) {
        return BaseRouter.extend({
            initialize: function() {
                BaseRouter.prototype.initialize.apply(this, arguments);
                this.setPageTitle(_('Health Check').t());
                this.loadingMessage = _('Loading...').t();
                this.fetchAppLocals = true;
                
                /*
                 *  Collections
                 */
                this.collection.tasks = new TasksCollection();
                this.collection.appLocalsDisabled = new AppLocalsCollection();
                this.appLocalsDisabledFetchData = {
                    sort_key: 'name',
                    sort_dir: 'asc',
                    app: '-' ,
                    owner: this.model.application.get('owner'),
                    search: 'disabled=1',
                    count: -1
                };
                
                /*
                 *  Models
                 */
                this.model.classicurl = classicurl;
                this.model.dmcConfigs = new DmcConfigsModel({}, {
                    appLocal: this.model.appLocal,
                    serverInfo: this.model.serverInfo
                });
                // conductor serves as a central controller that tracks all kinds of states, also handles all kinds of
                // user actions.
                // conductor needs to know the tasks and dmcConfigs
                this.model.conductor = new ConductorModel({}, {
                    tasks: this.collection.tasks,
                    dmcConfigs: this.model.dmcConfigs
                });
            },
            
            parseUrlTags: function() {
                var urlTags = this.model.classicurl.get('tag');
                if (urlTags) {
                    urlTags = Array.isArray(urlTags) ? urlTags.join(',') : urlTags;
                    this.model.conductor.set('tag', urlTags);
                }
                this.model.classicurl.clear();
                this.model.classicurl.save();
            },
            
            page: function(locale, app, page) {
                BaseRouter.prototype.page.apply(this, arguments);
                $.when(
                    this.model.classicurl.fetch(),
                    this.model.dmcConfigs.fetch(),
                    this.collection.tasks.fetch({
                        // cannot move these to the collections default fetch option because that will break the
                        // sorting and pagination of the listing page
                        data: {
                            sort_key: 'category',
                            count: 0
                        }
                    }), 
                    this.collection.appLocalsDisabled.fetch({
                        data: this.appLocalsDisabledFetchData,
                    }),
                    this.deferreds.pageViewRendered
                ).done(function(){
                    if (this.shouldRender) {
                        $('.preload').replaceWith(this.pageView.el);
                        
                        // Parsing URL tag parameter - used for anomalies table Investigate action
                        this.parseUrlTags();

                        this.masterView = new MasterView({
                            model: {
                                application: this.model.application,
                                conductor: this.model.conductor,
                                dmcConfigs: this.model.dmcConfigs
                            },
                            collection: {
                                tasks: this.collection.tasks,
                                appLocals: this.collection.appLocals,
                                appLocalsUnfilteredAll: this.collection.appLocalsUnfilteredAll,
                                appLocalsDisabled: this.collection.appLocalsDisabled
                            }
                        });
                        $('.main-section-body').html(this.masterView.render().$el);
                    }
                }.bind(this)).fail(function(response){
                    if (response.status === 402) {   // free or forwarder license
                        this.paywallView = new Paywall({title: _('Alerts').t(), model:this.model});
                        $("#placeholder-main-section-body").html(this.paywallView.render().$el);
                    }
                }.bind(this));
            }
        });
    }
);