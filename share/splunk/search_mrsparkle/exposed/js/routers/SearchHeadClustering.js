define(
    [
        'jquery',
        'underscore',
        'backbone',
        'routers/Base',
        'views/search_head_clustering/PageController'
    ],
    function(
        $,
        _,
        Backbone,
        BaseRouter,
        PageController
    ) {
        return BaseRouter.extend({
          
            initialize: function() {
                BaseRouter.prototype.initialize.apply(this, arguments);
                this.enableAppBar = false;
                this.fetchAppLocals = true;
                this.fetchServerInfo = true;
                this.setPageTitle(_('Manage Search Head Cluster').t());

                // The controller model is passed down to all
                // subviews and serves as the event bus for 
                // messages between the controller and views.
                this.model.controller = new Backbone.Model();
            },

            page: function(locale, app, page, action) {
                BaseRouter.prototype.page.apply(this, arguments);

                $.when(this.deferreds.pageViewRendered).done(_(function() {
                    $('.preload').replaceWith(this.pageView.el);

                    if (this.entityController) {
                        this.entityController.detach();
                    }
                    this.entityController = new PageController({
                        model: this.model,
                        collection: this.collection,
                        router: this
                    });

                    this.pageView.$('.main-section-body').append(this.entityController.render().el);
                }).bind(this));
            }
        });
    }
);