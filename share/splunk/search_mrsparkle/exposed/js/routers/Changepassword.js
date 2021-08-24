define(
    [
        'jquery',
        'underscore',
        'backbone',
        'routers/BaseManager',
        'views/changepassword/ChangePassword',
        'models/services/admin/splunk-auth',
		'models/services/authentication/User'
    ],
    function(
        $,
        _,
        Backbone,
        BaseManagerRouter,
        PageController,
		SplunkAuthModel,
		ChangePasswordModel
    ) {
        return BaseManagerRouter.extend({
            routes: {
                ':locale/manager/:app/authentication/:page': 'page',
                ':locale/manager/:app/authentication/:page/': 'page',
                ':locale/manager/:app/authentication/:page/_new': 'pageNew',
                ':locale/manager/:app/authentication/:page/_new*splat': 'pageNew',
                ':locale/manager/:app/authentication/:page/:changepassword?*splataction=edit': 'pageEdit', // For backwards compatibility edit mode url
                ':locale/manager/:app/authentication/:page/*splat': 'page',
                '*root/:locale/manager/:app/authentication/:page': 'pageRooted',
                '*root/:locale/manager/:app/authentication/:page/': 'pageRooted',
                '*root/:locale/manager/:app/authentication/:page/_new': 'pageNewRooted',
                '*root/:locale/manager/:app/authentication/:page/_new*splat': 'pageNewRooted',
                '*root/:locale/manager/:app/authentication/:page/:changepassword?*splataction=edit': 'pageEditRooted', // For backwards compatibility edit mode url
                '*root/:locale/manager/:app/authentication/:page/*splat': 'pageRooted',
                '*splat': 'notFound'
            },

            initialize: function() {
                BaseManagerRouter.prototype.initialize.apply(this, arguments);
                this.enableAppBar = false;
                this.fetchAppLocals = true;
                this.fetchServerInfo = true;
				
				this.model.splunkAuth = new SplunkAuthModel({id: 'splunk_auth'});
				this.deferreds.splunkAuth = $.Deferred();
				
				this.model.entity = new ChangePasswordModel({
					id: this.model.application.get('owner')
				});
				this.deferreds.entity = $.Deferred();
            },

            page: function(locale, app, page, action) {
                BaseManagerRouter.prototype.page.apply(this, arguments);
				
				this.setPageTitle(_('Account Settings').t());
				
				this.model.splunkAuth.fetch({
					success: function(model, response) {
                        this.deferreds.splunkAuth.resolve();
                    }.bind(this),
                    error: function(model, response) {
                        this.deferreds.splunkAuth.resolve();
                    }.bind(this)
				});
				
				this.model.entity.fetch({
					success: function(model, response) {
                        this.deferreds.entity.resolve();
                    }.bind(this),
                    error: function(model, response) {
                        this.deferreds.entity.resolve();
                    }.bind(this)
				});

                $.when(this.deferreds.pageViewRendered, this.deferreds.entity, this.deferreds.splunkAuth).done(_(function() {
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