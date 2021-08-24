define(
    [
        'module',
        'jquery',
        'underscore',
        'models/Base',
        'views/shared/PopTart',
        'views/shared/datasetcontrols/exploremenu/menu/ExploreList',
        'uri/route'
    ],
    function(
        module,
        $,
        _,
        BaseModel,
        PopTartView,
        ExploreListView,
        route
    ) {
        return PopTartView.extend({
            moduleId: module.id,
            className: 'dropdown-menu dropdown-menu-narrow explore-menu-poptart',

            initialize: function() {
                this.model.menuState = new BaseModel();
                
                PopTartView.prototype.initialize.apply(this, arguments);

                var defaults = {
                    button: true
                };

                _.defaults(this.options, defaults);
                
                this.children.exploreListView = new ExploreListView({
                    model: {
                        menuState: this.model.menuState,
                        application: this.model.application,
                        appLocal: this.model.appLocal,
                        dataset: this.model.dataset,
                        searchJob: this.model.searchJob,
                        serverInfo: this.model.serverInfo,
                        user: this.model.user
                    },
                    collection: {
                        apps: this.collection.apps
                    }
                });
            },

            startListening: function(options) {
                this.listenTo(this.model.menuState, 'convertToExplore', function() {
                    this.children.mlListView.$el.hide();
                    this.children.exploreListView.$el.show();
                    this.children.popdownDialogDelegate.$el.find('a.explore_link').first().focus();
                });
                
                PopTartView.prototype.startListening.apply(this, arguments);
            },

            render: function() {
                this.$el.html(PopTartView.prototype.template_menu);
                this.children.exploreListView.render().appendTo(this.$el);
                
                return this;
            }
        });
    }
);
