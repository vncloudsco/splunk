define(
    [
        'jquery',
        'underscore',
        'routers/Base',
        'uri/route',
        'collections/services/saved/Searches',
        'splunk_monitoring_console/views/settings/forwarder_setup/enterprise/Master',
        'splunk_monitoring_console/views/settings/forwarder_setup/lite/Master'
    ],
    function(
        $,
        _,
        BaseRouter,
        Route,
        SearchesCollection,
        MasterView,
        MasterLightView
    ) {
        return BaseRouter.extend({
            initialize: function() {
                BaseRouter.prototype.initialize.apply(this, arguments);
                this.setPageTitle(_('Forwarder Setup').t());
                this.loadingMessage = _('Loading...').t();
                this.collection.searchesCollection = new SearchesCollection();
                this.deferreds.searchesCollectionDfd = $.Deferred();

                this.collection.searchesCollection.fetch({
                    data: {
                        app: 'splunk_monitoring_console',
                        owner: '-',
                        search: 'name="DMC Forwarder - Build Asset Table"'
                    }
                }).done(function() {
                    this.deferreds.searchesCollectionDfd.resolve();
                }.bind(this));
            },
            page: function(locale, app, page) {
                BaseRouter.prototype.page.apply(this, arguments);
                $.when(this.deferreds.searchesCollectionDfd, this.deferreds.pageViewRendered).done(function(){
                    if (this.shouldRender) {
                        $('.preload').replaceWith(this.pageView.el);
                        if (this.model.serverInfo.isLite()) {
                            if (!this.collection.searchesCollection.models[0].entry.content.get('disabled')) {
                                document.location.href = Route.page(
                                    this.model.application.get('root'),
                                    locale,
                                    app,
                                    'forwarder_overview');
                            }
                            else {
                                $('.main-section-body').html((new MasterLightView({
                                    model: {
                                        application: this.model.application,
                                        savedSearch: this.collection.searchesCollection.models[0]
                                    }
                                })).render().$el);
                            }
                        }
                        else {
                            $('.main-section-body').html((new MasterView({
                                model: {
                                    application: this.model.application,
                                    savedSearch: this.collection.searchesCollection.models[0]
                                }
                            })).render().$el);  
                        }
                    }
                }.bind(this));
            }
        });
    }
);
