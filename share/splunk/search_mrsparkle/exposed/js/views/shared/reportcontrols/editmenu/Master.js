 define(
    [
        'jquery',
        'underscore',
        'module',
        'models/classicurl',
        'views/Base',
        'views/shared/basemanager/MoveDialog',
        'views/shared/documentcontrols/dialogs/DeleteDialog',
        'views/shared/reportcontrols/dialogs/clone_dialog/Master',
        'views/shared/reportcontrols/editmenu/Menu',
        'uri/route',
        'bootstrap.modal'
    ],
    function (
        $,
        _,
        module,
        classicUrlModel,
        Base,
        MoveDialog,
        DeleteDialog,
        CloneDialog,
        EditMenuPopTart,
        route
        /* bootstrap modal */
    ) {
    return Base.extend({
            moduleId: module.id,
             /**
             * @param {Object} options {
             *      model: {
             *          report: <models.search.Report>,
             *          reportCurrent: <models.search.Report>,
             *          application: <models.Application>,
             *          searchJob: <models.services.search.Job> (Optional),
             *          appLocal: <models.services.AppLocal>,
             *          user: <models.service.admin.user>,
             *          serverInfo: <models.services.server.ServerInfo>,
             *          controller: <Backbone.Model> (Optional)
             *      },
             *      collection: {
             *          roles: <collections.services.authorization.Roles>,
             *          appLocals: <collections.appLocals>,
             *          indexes: <collection.services.data.Indexes>
             *          alertActions: <collections.shared.ModAlertActions> (Optional: for edit schedule dialog)
             *      },
             *      {Boolean} button: (Optional) Whether or not the Edit dropdown has class btn-pill. Default is false and class is btn.
             *      {Boolean} showOpenActions: (Optional) Whether or not the open actions links are visable. Default is true.
             *      {Boolean} deleteRedirect: (Optional) Whether or not to redirect to reports page after delete. Default is false.
             *      {Boolean} showDisable: (optional) Whether or not to show the enable/disable option. Default is false.
             *      {Boolean} showMove: (optional) Whether or not to show the move option. Default is false.
             *      {Boolean} showAdvancedEdit: (Optional) Whether or not to show the advanced edit option. Default is false.
             *      {Boolean} showSearchField: (Optional) Whether to display a field to the user for entering the search string.
             *                                    Default is false
             *      {Boolean} showSummaryIndexing: (Optional) Whether or not to show the summary indexing option. Default is false.
             *      {String} entitySingular: Title of the type of entity.
             * }
             */
            initialize: function () {
                Base.prototype.initialize.apply(this, arguments);

                var defaults = {
                    button: true,
                    showOpenActions: true,
                    deleteRedirect: false,
                    showDisable: false,
                    showMove: false,
                    showAdvancedEdit: false,
                    showSearchField: false,
                    showSummaryIndexing: false
                };

                _.defaults(this.options, defaults);

                if (this.model.searchJob){
                    this.model.searchJob.on("prepared", function() {
                        this.$('a.clone').removeClass('disabled');
                    }, this);
                }
            },
            events: {
                'click a.open-in-search': function(e) {
                    var data = {};
                    if (this.model.searchJob && !this.model.searchJob.isNew()) {
                        data = classicUrlModel.toJSON();
                    } else {
                        data = {s: this.model.report.id};
                    }
                    var openInView = this.model.report.openInView(this.model.user);
                    var viewRouteData = route.getViewRouteData(openInView);
                    var routeString = viewRouteData.route(
                            this.model.application.get('root'),
                            this.model.application.get('locale'),
                            this.model.application.get('app'),
                            {data: data}
                        );
                    window.location = routeString;

                    e.preventDefault();
                },
                'click a.clone': function(e) {
                    this.children.cloneDialog = new CloneDialog({
                        model: {
                            report: this.model.report,
                            searchJob: this.model.searchJob,
                            application: this.model.application,
                            user: this.model.user
                        },
                        collection: {
                            appLocals: this.collection.appLocals
                        },
                        onHiddenRemove: true
                    });

                    this.children.cloneDialog.render().appendTo($("body")).show();

                    e.preventDefault();
                },
                'click a.delete': function(e){
                    this.children.deleteDialog = new DeleteDialog({
                        model: {
                            report: this.model.report,
                            application: this.model.application,
                            controller: this.model.controller
                        },
                        deleteRedirect: this.options.deleteRedirect,
                        onHiddenRemove: true
                    });

                    this.children.deleteDialog.render().appendTo($("body")).show();

                    e.preventDefault();
                },
                'click a.edit': function(e) {
                    e.preventDefault();
                    this.openEdit($(e.currentTarget));
                },
                'click a.move': function(e) {
                    this.children.moveDialog = new MoveDialog({
                        model: {
                            entity: this.model.report,
                            application: this.model.application,
                            controller: this.model.controller
                        },
                        collection: {
                            appLocals: this.collection.appLocals
                        },
                        entitySingular: this.options.entitySingular,
                        onHiddenRemove: true
                    });

                    this.children.moveDialog.render().appendTo($("body")).show();

                    e.preventDefault();
                }
            },
            openEdit: function($target) {
                if (this.children.editMenuPopTart && this.children.editMenuPopTart.shown) {
                    this.children.editMenuPopTart.hide();
                    return;
                }

                $target.addClass('active');

                this.children.editMenuPopTart = new EditMenuPopTart({
                    model: {
                        report: this.model.report,
                        reportCurrent: this.model.reportCurrent,
                        application: this.model.application,
                        searchJob: this.model.searchJob,
                        appLocal: this.model.appLocal,
                        user: this.model.user,
                        serverInfo: this.model.serverInfo,
                        controller: this.model.controller
                    },
                    collection: this.collection,
                    showOpenActions: this.options.showOpenActions,
                    deleteRedirect: this.options.deleteRedirect,
                    onHiddenRemove: true,
                    ignoreToggleMouseDown: true,
                    showDisable: this.options.showDisable,
                    showMove: this.options.showMove,
                    showAdvancedEdit: this.options.showAdvancedEdit,
                    showSearchField: this.options.showSearchField,
                    entitySingular: this.options.entitySingular,
                    showSummaryIndexing: this.options.showSummaryIndexing
                });
                this.children.editMenuPopTart.render().appendTo($('body'));
                this.children.editMenuPopTart.show($target);
                this.children.editMenuPopTart.on('hide', function() {
                    $target.removeClass('active');
                }, this);
            },
            render: function () {
                var canWrite = this.model.report.canWrite(this.model.user.canScheduleSearch(), this.model.user.canRTSearch()),
                    canClone = this.model.report.canClone(this.model.user.canScheduleSearch(), this.model.user.canRTSearch()),
                    canEmbed = this.model.report.canEmbed(this.model.user.canScheduleSearch(), this.model.user.canEmbed()),
                    canDelete = this.model.report.canDelete(),
                    canMove = this.model.report.canMove();

                if (canWrite || 1 < (0 + this.options.showOpenActions + canClone + canDelete + canEmbed +
                                      (this.options.showMove && canMove))) {
                    this.$el.append('<a class="dropdown-toggle edit' + (this.options.button ? " btn" : "") + '" href="#">' + _("Edit").t() +'<span class="caret"></span></a>');
                } else {
                    if (this.options.showOpenActions) {
                        var openInView = this.model.report.openInView(this.model.user);
                        var viewRouteData = route.getViewRouteData(openInView);
                        var link = viewRouteData.route(
                                this.model.application.get("root"),
                                this.model.application.get("locale"),
                                this.model.application.get("app"),
                                {data: {s: this.model.report.id}});
                        this.$el.append('<a class="open-in-' + openInView + (this.options.button ? " btn" : "") + '" href="' + link + '">' + viewRouteData.openLabel +'</a>');
                    }
                    if (canClone) {
                        this.$el.append('<a class="clone' + (this.options.button ? " btn" : "") + '" href="#">' + _("Clone").t() +'</a>');
                    }
                    if (canEmbed) {
                        this.$el.append('<a class="embed' + (this.options.button ? " btn" : "") + '" href="#">' + _("Embed").t() +'</a>');
                    }
                    if (this.options.showMove && canMove) {
                        this.$el.append('<a class="move' + (this.options.button ? " btn" : "") + '" href="#">' + _("Move").t() +'</a>');
                    }
                    if (canDelete) {
                        this.$el.append('<a class="delete' + (this.options.button ? " btn" : "") + '" href="#">' + _("Delete").t() +'</a>');
                    }
                }

                if (this.model.searchJob && this.model.searchJob.isPreparing()) {
                    this.$('a.clone').addClass('disabled');
                }

                return this;
            }
        });
    }
);
