define([
    'underscore',
    'jquery',
    'views/Base',
    'module',
    'views/shared/reportcontrols/details/History',
    'views/shared/reportcontrols/details/Creator',
    'views/shared/documentcontrols/details/App',
    'views/shared/reportcontrols/details/Schedule',
    'views/shared/reportcontrols/details/EditSchedule',
    'views/shared/documentcontrols/details/Actions',
    'views/shared/reportcontrols/details/Acceleration',
    'views/shared/reportcontrols/details/EditAcceleration',
    'views/shared/documentcontrols/details/Permissions',
    'views/shared/documentcontrols/details/ModifiedDate',
    'views/shared/reportcontrols/details/EditPermissions',
    'views/shared/reportcontrols/details/Embed',
    'views/shared/reportcontrols/details/EditEmbed',
    'util/general_utils',
    'bootstrap.modal'
    ],
    function(
        _,
        $,
        BaseView,
        module,
        HistoryView,
        CreatorView,
        AppView,
        ScheduleView,
        EditScheduleView,
        ActionsTextView,
        AccelerationView,
        EditAccelerationView,
        PermissionsView,
        ModifiedView,
        EditPermissionsView,
        EmbedView,
        EditEmbedView,
        util,
        bootstrapModal
    ) {
        return BaseView.extend({
            moduleId: module.id,
            showLinks: true,
            /**
            * @param {Object} options {
            *       model: {
            *           report: <models.Report>,
            *           application: <models.Application>,
            *           intentionsParser: (Optional) <models.IntentionsParser>,
            *           appLocal: <models.services.AppLocal>,
            *           user: <models.service.admin.user>
            *       },
            *       collection: {
            *          roles: <collections.services.authorization.Roles>,
            *          apps: <collections.services.AppLocals> (Optional for creator view),
            *          alertActions: <collections.shared.ModAlertActions>,
            *          workloadManagementStatus: <collections.services.admin.workload_management>
            *       },
            *       alternateApp: <alternate_app_to_open>
            * }
            */
            initialize: function(options) {
                BaseView.prototype.initialize.apply(this, arguments);
                this.children.appView = new AppView({model: this.model.report});
                this.children.scheduleView = new ScheduleView({model: this.model.report});
                this.children.actionsView = new ActionsTextView({
                    model: {
                        document: this.model.report,
                        application: this.model.application
                    },
                    collection: {
                        alertActions: this.collection.alertActions
                    }
                });
                this.children.accelerationView = new AccelerationView({model: this.model.report});
                this.children.permissionsView = new PermissionsView({
                    model: {
                        report:this.model.report,
                        user: this.model.user,
                        serverInfo: this.model.serverInfo
                    }
                });
                this.children.modifiedView = new ModifiedView({
                    model: {
                        document: this.model.report
                    }
                });

                if(options.showLinks !== undefined) {
                    this.showLinks = options.showLinks;
                }
                this.children.creatorView = new CreatorView({
                    model: {
                        report: this.model.report,
                        application: this.model.application
                    },
                    collection: {
                        apps: this.collection.apps
                    },
                    showLinks: this.showLinks,
                    alternateApp: this.options.alternateApp
                });
                if(this.showLinks) {
                    this.children.editScheduleView = new EditScheduleView({
                        model: {
                            report: this.model.report,
                            application: this.model.application,
                            user: this.model.user,
                            appLocal: this.model.appLocal,
                            serverInfo: this.model.serverInfo
                        },
                        collection: {
                            alertActions: this.collection.alertActions,
                            workloadManagementStatus: this.collection.workloadManagementStatus
                        }
                    });
                    this.children.editAccelerationView = new EditAccelerationView({
                        model: {
                            report: this.model.report,
                            searchJob: this.model.searchJob,
                            application: this.model.application,
                            user: this.model.user
                        },
                        collection: {
                            workloadManagementStatus: this.collection.workloadManagementStatus
                        }
                    });
                    this.children.editPermissionsView = new EditPermissionsView({
                        model: {
                            report: this.model.report,
                            user: this.model.user,
                            serverInfo: this.model.serverInfo,
                            application: this.model.application
                        },
                        collection: this.collection.roles
                    });
                    this.children.editEmbedView = new EditEmbedView({model: this.model});
                }
                this.children.embedView = new EmbedView({model: this.model.report});

                if (this.model.searchJob){
                    this.model.searchJob.on("prepared", function() {
                        this.$('a.edit-acceleration').css('display', '');
                    }, this);
                }
            },
            startListening: function() {
                this.listenTo(this.model.report.entry.content, 'change:embed.enabled', this.debouncedRender);
            },
            render: function() {
                var canWrite = this.model.report.entry.acl.get('can_write') && !(this.model.report.entry.content.get('is_scheduled') && !this.model.user.canScheduleSearch()),
                    canEmbed = this.model.report.canEmbed(this.model.user.canScheduleSearch(), this.model.user.canEmbed()),
                    isEmbedded = util.normalizeBoolean(this.model.report.entry.content.get('embed.enabled'));
                this.el.innerHTML = this.compiledTemplate({reportName: _.escape(this.model.report.entry.get('name'))});
                this.children.creatorView.render().appendTo(this.$('dd.creator'));
                this.children.appView.render().appendTo(this.$('dd.app'));
                this.children.scheduleView.render().appendTo(this.$('dd.schedule'));
                this.children.actionsView.render().appendTo(this.$('dd.actions'));
                this.children.accelerationView.render().appendTo(this.$('dd.acceleration'));
                this.children.permissionsView.render().appendTo(this.$('dd.permissions'));
                this.children.modifiedView.render().appendTo(this.$('dd.modified'));
                this.children.embedView.render().appendTo(this.$('dd.embed'));

                if(this.showLinks) {
                    if (canWrite && !isEmbedded) {
                        if (this.model.user.canScheduleSearch() && !this.model.report.isRealTime()) {
                            // Check if real-time. User can not schedule a real-time search
                            this.children.editScheduleView.render().appendTo(this.$('dd.schedule'));
                        }
                        if (this.model.user.canAccelerateReport()) {
                            this.children.editAccelerationView.render().appendTo(this.$('dd.acceleration'));
                        }
                        // Only show if user has perm to change perms
                        if (this.model.report.entry.acl.get('can_change_perms')) {
                            this.children.editPermissionsView.render().appendTo(this.$('dd.permissions'));
                        }
                    }
                    if (canEmbed) {
                        this.children.editEmbedView.render().appendTo(this.$('dd.embed'));
                    }
                }

                if (this.model.searchJob && this.model.searchJob.isPreparing()) {
                    this.$('a.edit-acceleration').css('display', 'none');
                }

                if(this.model.report.isPivotReport()) {
                    this.$('dt.acceleration').remove();
                    this.$('dd.acceleration').remove();
                }

                return this;
            },
            template: '\
            <span class="property-row-identifier visuallyhidden"><%- _("Properties of ").t() %><%= reportName %></span>\
            <dl class="list-dotted">\
                <!--TODO when these attributes exist-->\
                <!--<dt class="history"><%- _("History").t() %></dt>\
                    <dd class="history"></dd>-->\
                <dt class="creator"><%- _("Creator").t() %></dt>\
                    <dd class="creator"></dd>\
                <dt class="app"><%- _("App").t() %></dt>\
                    <dd class="app"></dd>\
                <dt class="schedule"><%- _("Schedule").t() %></dt>\
                    <dd class="schedule"></dd>\
                <dt class="actions"><%- _("Actions").t() %></dt>\
                    <dd class="actions"></dd>\
                <dt class="acceleration"><%- _("Acceleration").t() %></dt>\
                    <dd class="acceleration"></dd>\
                <dt class="permissions"><%- _("Permissions").t() %></dt>\
                    <dd class="permissions"></dd>\
                <dt class="modified"><%- _("Modified").t() %></dt>\
                    <dd class="modified"></dd>\
                <dt class="embed"><%- _("Embedding").t() %></dt>\
                    <dd class="embed"></dd>\
            </dl>\
        '
        });
    }
);
