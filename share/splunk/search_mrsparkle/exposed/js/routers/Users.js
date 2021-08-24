define(
    [
        'jquery',
        'underscore',
        'backbone',
        'routers/BaseManager',
        'views/users/PageController'
    ],
    function(
        $,
        _,
        Backbone,
        BaseManagerRouter,
        PageController
    ) {
        return BaseManagerRouter.extend({
            routes: {
                ':locale/manager/:app/authentication/:page': 'page',
                ':locale/manager/:app/authentication/:page/': 'page',
                ':locale/manager/:app/authentication/:page/_new': 'pageNew',
                ':locale/manager/:app/authentication/:page/_new*splat': 'pageNew',
                ':locale/manager/:app/authentication/:page/:users?*splataction=edit': 'pageEdit', // For backwards compatibility edit mode url
                ':locale/manager/:app/authentication/:page/*splat': 'page',
                '*root/:locale/manager/:app/authentication/:page': 'pageRooted',
                '*root/:locale/manager/:app/authentication/:page/': 'pageRooted',
                '*root/:locale/manager/:app/authentication/:page/_new': 'pageNewRooted',
                '*root/:locale/manager/:app/authentication/:page/_new*splat': 'pageNewRooted',
                '*root/:locale/manager/:app/authentication/:page/:users?*splataction=edit': 'pageEditRooted', // For backwards compatibility edit mode url
                '*root/:locale/manager/:app/authentication/:page/*splat': 'pageRooted',
                '*splat': 'notFound'
            },

            initialize: function() {
                BaseManagerRouter.prototype.initialize.apply(this, arguments);
                this.enableAppBar = false;
                this.fetchAppLocals = true;
                this.model.controller = new Backbone.Model();
            },

            page: function(locale, app, page, action) {
                BaseManagerRouter.prototype.page.apply(this, arguments);

                this.setPageTitle(_('Users').t());

                $.when(this.deferreds.pageViewRendered).done(_(function() {
                    $('.preload').replaceWith(this.pageView.el);

                    if (this.entityController) {
                        this.entityController.remove();
                    }
                    this.entityController = new PageController({
                        model: this.model,
                        collection: this.collection,
                        router: this
                    });
                    if (action) {
                        // Trigger action from url.
                        this.entityController.model.controller.trigger(action);
                    }
                    this.pageView.$('.main-section-body').append(this.entityController.render().el);
                }).bind(this));
            }
        });
    }
);
