define(
    [
        'underscore',
        'module',
        'views/Base',
        'views/shared/datasetcontrols/editmenu/Master',
        'views/shared/datasetcontrols/details/Master',
        'views/shared/datasetcontrols/exploremenu/Master',
        'views/shared/datasetcontrols/extendmenu/Master',
        'views/shared/delegates/Popdown'
    ],
    function(
        _,
        module,
        BaseView,
        EditMenu,
        DetailsView,
        ExploreMenu,
        ExtendMenu,
        Popdown
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'pull-right',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.children.editMenu = new EditMenu({
                    model: {
                        application: this.model.application,
                        appLocal: this.model.appLocal,
                        dataset: this.model.dataset,
                        searchJob: this.model.searchJob,
                        serverInfo: this.model.serverInfo,
                        user: this.model.user
                    },
                    collection: {
                        roles: this.collection.roles
                    },
                    deleteRedirect: true,
                    showScheduleLink: true,
                    className: 'btn-combo'
                });

                this.children.detailsView = new DetailsView({
                    model: {
                        dataset: this.model.dataset,
                        application: this.model.application,
                        searchJob: this.model.searchJob,
                        user: this.model.user,
                        appLocal: this.model.appLocal,
                        serverInfo: this.model.serverInfo
                    },
                    collection: {
                        roles: this.collection.roles
                    }
                });

                this.children.exploreMenu = new ExploreMenu({
                    model: {
                        dataset: this.model.dataset,
                        application: this.model.application,
                        searchJob: this.model.searchJob,
                        user: this.model.user,
                        appLocal: this.model.appLocal,
                        serverInfo: this.model.serverInfo
                    },
                    collection: {
                        apps: this.collection.apps
                    }
                });
                
                this.children.extendMenu = new ExtendMenu({
                    model: {
                        dataset: this.model.dataset,
                        application: this.model.application,
                        timeRange: this.model.timeRange,
                        searchJob: this.model.searchJob,
                        user: this.model.user,
                        appLocal: this.model.appLocal,
                        serverInfo: this.model.serverInfo
                    },
                    collection: {
                        apps: this.collection.apps
                    },
                    displayAsButtons: true
                });
            },

            activate: function(options) {
                if (this.active) {
                    return BaseView.prototype.activate.apply(this, arguments);
                }

                // A new page route can change the extend menu's links, so we need to rerender it here
                this.children.extendMenu.render();

                return BaseView.prototype.activate.apply(this, arguments);
            },

            render: function() {
                this.$el.html(this.compiledTemplate({
                    _: _
                }));

                this.children.editMenu.render().prependTo(this.$('.edit-info-section'));
                this.children.detailsView.render().prependTo(this.$('.more-info .popdown-dialog-body'));
                this.children.exploreMenu.render().appendTo(this.$el);
                this.children.extendMenu.render().appendTo(this.$el);

                this.children.popdownDelegate = new Popdown({el: this.$('.more-info')});

                return this;
            },
            template: '\
                <div class="edit-info-section btn-group">\
                    <div class="btn-combo more-info">\
                        <div class="popdown-dialog">\
                            <div class="arrow">\
                            </div>\
                            <div class="popdown-dialog-body">\
                            </div>\
                        </div>\
                        <a href=# class="popdown-toggle btn">\
                            <%- _("More Info").t() %>\
                            <span class="caret"></span>\
                        </a>\
                    </div>\
                </div>\
            '
        });
    });
