define(
    [
        'jquery',
        'underscore',
        'module',
        'models/Base',
        'views/Base',
        'views/shared/datasetcontrols/exploremenu/menu/Master',
        './Master.pcss'
    ],
    function (
        $,
        _,
        module,
        BaseModel,
        BaseView,
        ExploreMenuPopTart,
        css
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'dataset-explore-menu',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                var defaults = {
                    button: true
                };

                _.defaults(this.options, defaults);
            },

            events: {
                'click a.explore': function(e) {
                    e.preventDefault();
                    this.openExplore($(e.currentTarget));
                }
            },

            openExplore: function($target) {
                if (this.children.exploreMenuPopTart && this.children.exploreMenuPopTart.shown) {
                    this.children.exploreMenuPopTart.hide();
                    return;
                }

                $target.addClass('active');

                this.children.exploreMenuPopTart = new ExploreMenuPopTart({
                    model: {
                        application: this.model.application,
                        appLocal: this.model.appLocal,
                        dataset: this.model.dataset,
                        searchJob: this.model.searchJob,
                        serverInfo: this.model.serverInfo,
                        user: this.model.user
                    },
                    collection: {
                        apps: this.collection.apps
                    },
                    onHiddenRemove: true,
                    ignoreToggleMouseDown: true
                });
                this.children.exploreMenuPopTart.render().appendTo($('body'));
                this.children.exploreMenuPopTart.show($target);
                this.children.exploreMenuPopTart.on('hide', function() {
                    $target.removeClass('active');
                }, this);
            },

            render: function() {
                this.$el.append('<a class="dropdown-toggle explore' + (this.options.button ? " btn" : "") + '" href="#">' + _("Explore").t() +'<span class="caret"></span></a>');

                return this;
            }
        });
    }
);
