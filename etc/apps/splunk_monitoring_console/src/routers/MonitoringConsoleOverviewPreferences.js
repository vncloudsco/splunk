define(
    [
        'underscore',
        'jquery',
        'backbone',
        'routers/Base',
        'splunk_monitoring_console/views/settings/overview_preferences/PageController'
    ],
    function(
        _,
        $,
        Backbone,
        BaseRouter,
        PageController
    ) {
        return BaseRouter.extend({
            page: function(locale, app, page) {
                BaseRouter.prototype.page.apply(this, arguments);

                this.setPageTitle(_('Overview Preferences').t());
                
                $.when(this.deferreds.pageViewRendered).done(function() {
                   $('.preload').replaceWith(this.pageView.el);

                    if (this.pageController) {
                        this.pageController.detach();
                    }
                    this.pageController = new PageController({
                        model: this.model,
                        collection: this.collection
                    });
                    this.pageView.$('.main-section-body').append(this.pageController.render().el);
                }.bind(this));
            }

        });
    }
);