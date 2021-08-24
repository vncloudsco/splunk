define(
    [
        'jquery',
        'underscore',
        'backbone',
        'routers/BaseManager',
        'views/management/PasswordConfig',
        'models/services/admin/splunk-auth'
    ],
    function(
        $,
        _,
        Backbone,
        BaseManagerRouter,
        PasswordConfig,
        SplunkAuthModel
    ) {
        return BaseManagerRouter.extend({
            routes: {
                ':locale/manager/:app/password/:page': 'page',
                ':locale/manager/:app/password/:page/': 'page',
                ':locale/manager/:app/password/:page/_new': 'pageNew',
                ':locale/manager/:app/password/:page/_new*splat': 'pageNew',
                ':locale/manager/:app/password/:page/:management?*splataction=edit': 'pageEdit', // For backwards compatibility edit mode url
                ':locale/manager/:app/password/:page/*splat': 'page',
                '*root/:locale/manager/:app/password/:page': 'pageRooted',
                '*root/:locale/manager/:app/password/:page/': 'pageRooted',
                '*root/:locale/manager/:app/password/:page/_new': 'pageNewRooted',
                '*root/:locale/manager/:app/password/:page/_new*splat': 'pageNewRooted',
                '*root/:locale/manager/:app/password/:page/:management?*splataction=edit': 'pageEditRooted', // For backwards compatibility edit mode url
                '*root/:locale/manager/:app/password/:page/*splat': 'pageRooted',
                '*splat': 'notFound'
            },

            initialize: function() {
                BaseManagerRouter.prototype.initialize.apply(this, arguments);
                this.enableAppBar = false;

                this.model.splunkAuth = new SplunkAuthModel({id: 'splunk_auth'});
                this.deferreds.passwordConfigs = $.Deferred();
            },

            page: function(locale, app, page, action) {
                BaseManagerRouter.prototype.page.apply(this, arguments);

                this.setPageTitle(_('Password Management').t());

                this.model.splunkAuth.fetch({
                    success: function(model, response) {
                        this.deferreds.passwordConfigs.resolve();
                    }.bind(this),
                    error: function(model, response) {
                        this.deferreds.passwordConfigs.resolve();
                    }.bind(this)
                });

                $.when(this.deferreds.pageViewRendered, this.deferreds.passwordConfigs).done(_(function() {
                    $('.preload').replaceWith(this.pageView.el);

                    if (this.entityController) {
                        this.entityController.detach();
                    }
                    
                    this.entityController = new PasswordConfig({
                        model: {
                            application: this.model.application,
                            splunkAuth: this.model.splunkAuth,
                            serverInfo: this.model.serverInfo
                        },
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