define([
    'jquery',
    'underscore',
    'backbone',
    'models/Base',
    'models/shared/ScheduleWindow',
    'models/search/ScheduledReport',
    'collections/services/data/ui/Times',
    'views/shared/Modal',
    'module',
    'views/shared/reportcontrols/dialogs/schedule_dialog/edit/Master',
    'views/shared/reportcontrols/dialogs/schedule_dialog/Success',
    'splunk.util',
    './Master.pcss'
    ],
    function(
        $,
        _,
        Backbone,
        BaseModel,
        ScheduleWindowModel,
        ScheduledReportModel,
        TimesCollection,
        Modal,
        module,
        Edit,
        Success,
        splunkUtil,
        css
    ) {
    return Modal.extend({
            moduleId: module.id,
            /**
            * @param {Object} options {
            *       model: {
            *           application: <models.Application>
            *           report: <models.Report>,
            *           appLocal: <models.services.AppLocal>,
            *           user: <models.services.admin.User>,
            *           controller: <Backbone.Model> (Optional)
            *       },
            *       collection: {
            *           alertActions: <collections.shared.ModAlertActions> (Optional, will be fetched if not passed in),
            *           workloadManagementStatus: <collections.services.admin.workload_management>
            *       }
            * }
            */
            className: Modal.CLASS_NAME + ' ' + Modal.CLASS_MODAL_WIDE + ' schedule-modal',
            initialize: function() {
                Modal.prototype.initialize.apply(this, arguments);
                //model
                this.model = {
                    application: this.model.application,
                    report: this.model.report,
                    user: this.model.user,
                    serverInfo: this.model.serverInfo,
                    appLocal: this.model.appLocal,
                    inmem: new ScheduledReportModel({}, {splunkDPayload: this.model.report.toSplunkD()}),
                    scheduleWindow: new ScheduleWindowModel(),
                    controller: this.model.controller
                };
                //collections
                this.collection = this.collection || {};
                this.collection.times = new TimesCollection();

                this.collectionDeferred = this.collection.times.fetch({
                    data: {
                        app: this.model.application.get("app"),
                        owner: this.model.application.get("owner"),
                        count: -1
                    }
                });

                this.model.scheduleWindow.setScheduleWindow(this.model.inmem.entry.content.get('schedule_window'));

                //views
                this.children.edit = new Edit({
                    model: {
                        application: this.model.application,
                        inmem: this.model.inmem,
                        user: this.model.user,
                        appLocal: this.model.appLocal,
                        scheduleWindow: this.model.scheduleWindow,
                        report: this.model.report
                    },
                    collection: {
                        times: this.collection.times,
                        alertActions: this.collection.alertActions, //passed in if it exists
                        workloadManagementStatus: this.collection.workloadManagementStatus
                    }
                });

                this.children.success = new Success({
                    model: {
                        application: this.model.application,
                        report: this.model.inmem
                    },
                    message: this.options.successMessage
                });

                //event listeners for saving
                this.model.inmem.on('saveSuccessNotScheduled', function() {
                    this.model.report.entry.content.set('is_scheduled', 0);
                    this.model.report.entry.content.set('next_scheduled_time',
                        this.model.inmem.entry.content.get('next_scheduled_time'));
                    this.hide();
                    if (this.model.controller) {
                        this.model.controller.trigger('refreshEntities');
                    }
                }, this);

                this.model.inmem.on('saveSchedule', function() {
                    var wasNew = this.model.report.isNew();
                    var data = {};

                    if (wasNew) {
                        data.data = {
                            app: this.model.application.get('app'),
                            owner: this.model.application.get('owner')
                        };
                    }

                    if (this.model.inmem.get('scheduled_and_enabled')) {
                        this.model.scheduleWindow.validate();
                        this.model.inmem.entry.content.set('schedule_window', this.model.scheduleWindow.getScheduleWindow());

                        var removedAttr = this.model.inmem.unsetUnselectedActionArgs();

                        var saveDeferred = this.model.inmem.save({}, _.extend(data, {
                            success: function(model, response) {
                                if (wasNew) {
                                    this.children.edit.$el.hide();
                                    this.children.success.render().$el.show();
                                } else {
                                    this.model.report.fetch();
                                    this.hide();
                                }

                                if (this.model.controller) {
                                    this.model.controller.trigger('refreshEntities');
                                }
                            }.bind(this)
                        }));

                        // if save fails due to validation error we need to reset unset unselected alert actions args 
                        $.when(saveDeferred).done(function() {
                            if (!this.model.inmem.entry.content.isValid()) {
                                this.model.inmem.entry.content.set(removedAttr);
                            }
                        }.bind(this));
                    } else {
                        this.model.inmem.save({is_scheduled: 0}, _.extend(data, {
                            patch: true,
                            success: function(model, response) {
                                this.model.inmem.trigger('saveSuccessNotScheduled');
                            }.bind(this)
                        }));
                    }
                }, this);
            },
            render: function() {

                $.when(this.collectionDeferred).then(function() {
                    this.children.edit.render().appendTo(this.$el);
                    this.children.success.render().appendTo(this.$el);
                    this.children.success.$el.hide();
                }.bind(this));
            }
        }
    );
});