/**
 * This the router for the Saved Searches manager page
 */

define(
    [
        'jquery',
        'underscore',
        'backbone',
        'routers/BaseManager',
        'collections/services/admin/workload_management/Status',
        'views/savedsearches/PageController',
        'uri/route'
    ],
    function(
        $,
        _,
        Backbone,
        BaseManagerRouter,
        WorkloadManagementStatus,
        PageController,
        route
        ) {
        return BaseManagerRouter.extend({
            routes: {
                ':locale/app/:app/saved/:page': 'page',
                ':locale/app/:app/saved/:page/': 'page',
                ':locale/app/:app/saved/:page/_new': 'pageNew',
                ':locale/app/:app/saved/:page/_new*splat': 'pageNew',
                ':locale/app/:app/saved/:page/:savedsearch?*splataction=edit*splat': 'pageEdit',
                ':locale/app/:app/saved/:page/*splat': 'page',
                ':locale/manager/:app/saved/:page': 'page',
                ':locale/manager/:app/saved/:page/': 'page',
                ':locale/manager/:app/saved/:page/_new': 'pageNew',
                ':locale/manager/:app/saved/:page/_new*splat': 'pageNew',
                ':locale/manager/:app/saved/:page/:savedsearch?*splataction=edit*splat': 'pageEdit',
                ':locale/manager/:app/saved/:page/*splat': 'page',
                '*root/:locale/app/:app/saved/:page': 'pageRooted',
                '*root/:locale/app/:app/saved/:page/': 'pageRooted',
                '*root/:locale/app/:app/saved/:page/_new': 'pageNewRooted',
                '*root/:locale/app/:app/saved/:page/_new*splat': 'pageNewRooted',
                '*root/:locale/app/:app/saved/:page/:savedsearch?*splataction=edit*splat': 'pageEditRooted',
                '*root/:locale/app/:app/saved/:page/*splat': 'pageRooted',
                '*root/:locale/manager/:app/saved/:page': 'pageRooted',
                '*root/:locale/manager/:app/saved/:page/': 'pageRooted',
                '*root/:locale/manager/:app/saved/:page/_new': 'pageNewRooted',
                '*root/:locale/manager/:app/saved/:page/_new*splat': 'pageNewRooted',
                '*root/:locale/manager/:app/saved/:page/:savedsearch?*splataction=edit*splat': 'pageEditRooted',
                '*root/:locale/manager/:app/saved/:page/*splat': 'pageRooted',
                '*splat': 'notFound'
            },

            initialize: function() {
                BaseManagerRouter.prototype.initialize.apply(this, arguments);
                this.enableAppBar = false;
                this.fetchAppLocals = true;
                this.fetchServerInfo = true;
                this.fetchVisualizations = true;

                // The controller model is passed down to all subviews and serves as the event bus for messages between
                // the controller and views.
                this.model.controller = new Backbone.Model();

                this.collection.workloadManagementStatus = new WorkloadManagementStatus();

                this.deferreds.workloadManagementStatus = $.Deferred();
            },

            page: function(locale, app, page, action) {
                BaseManagerRouter.prototype.page.apply(this, arguments);

                this.setPageTitle(_('Searches, reports, and alerts').t());

                this.collection.workloadManagementStatus.bootstrapWorkloadManagementStatus(this.deferreds.workloadManagementStatus);

                $.when(this.deferreds.pageViewRendered).done(_(function() {
                    $('.preload').replaceWith(this.pageView.el);

                    if (this.pageController) {
                        this.pageController.detach();
                    }
                    this.pageController = new PageController({
                        model: this.model,
                        collection: this.collection,
                        router: this
                    });
                    if (action) {
                        // Trigger action from url.
                        this.pageController.model.controller.trigger(action);
                        // Refresh URL to base saved/searches, we want to stick with the single page usage.
                        var nextUrl = route.manager(
                            this.model.application.get('root'),
                            this.model.application.get('locale'),
                            this.model.application.get('app'),
                            ['saved', 'searches'],
                            {data: {app: this.model.classicurl.get('app'),
                                    count: this.model.classicurl.get('count'),
                                    offset: this.model.classicurl.get('offset'),
                                    itemType: this.model.classicurl.get('itemType'),
                                    owner: this.model.classicurl.get('owner'),
                                    search: this.model.classicurl.get('search') || ''
                            }});
                        this.navigate(nextUrl, {trigger: false, replace: true});
                    }
                    this.pageView.$('.main-section-body').append(this.pageController.render().el);
                }).bind(this));
            }
        });
    }
);
