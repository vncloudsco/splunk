define(
        [
            'jquery',
            'underscore',
            'module',
            'models/services/data/ui/Manager',
            'collections/services/data/ui/ModAlerts',
            'collections/shared/ModAlertActions',
            'views/Base',
            'views/shared/Modal',
            'views/shared/delegates/ModalTimerangePicker',
            'views/shared/reportcontrols/dialogs/schedule_dialog/edit/Title',
            'views/shared/reportcontrols/dialogs/schedule_dialog/edit/Settings',
            'views/shared/documentcontrols/triggeractions/Master',
            'views/shared/timerangepicker/dialog/Master',
            'views/shared/FlashMessages',
            'util/pdf_utils'
        ],
        function(
            $,
            _,
            module,
            ManagerViewModel,
            ModAlertsUICollection,
            ModAlertActionsCollection,
            Base,
            Modal,
            TimeRangeDelegate,
            TitleView,
            ScheduleView,
            TriggerActionsView,
            TimeRangePickerDialog,
            FlashMessage,
            pdfUtils
        ) {
        return Base.extend({
            moduleId: module.id,
            /**
            * @param {Object} options {
            *        model: {
            *            application: <models.Application>
            *            inmem: <models.search.ScheduledReport>,
            *            user: <models.services.admin.User>,
            *            appLocal: <models.services.AppLocal>,
            *            scheduleWindow: <models.shared.ScheduleWindow>,
            *            report: <models.search.Report>
            *        },
            *        collection: {
            *            times: <collections.services.data.ui.Times>,
            *            alertActions: <collections.shared.ModAlertActions>, (Optional, will be fetched if it is not passed in)
            *            workloadManagementStatus: <collections.services.admin.workload_management> (Optional.)
            *        }
            * }
            **/
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);
                //views
                this.children.flashMessage = new FlashMessage({
                    model: {
                        inmem: this.model.inmem,
                        content: this.model.inmem.entry.content,
                        cron: this.model.inmem.cron,
                        scheduleWindow: this.model.scheduleWindow
                    }
                });

                var warningMessage = this.model.inmem.getScheduleWarning(this.model.report);
                if (warningMessage) {
                    this.children.flashMessage.flashMsgHelper.addGeneralMessage('schedule_warning_message', warningMessage);
                }

                this.children.title = new TitleView({
                    model: {
                        inmem: this.model.inmem,
                        report: this.model.report,
                        application: this.model.application
                    }
                });
                this.children.scheduleView = new ScheduleView({
                    model: {
                        application: this.model.application,
                        inmem: this.model.inmem,
                        user: this.model.user,
                        scheduleWindow: this.model.scheduleWindow
                    },
                    collection: {
                        times: this.collection.times,
                        workloadManagementStatus: this.collection.workloadManagementStatus
                    }
                });


                this.children.timeRangePickerView = new TimeRangePickerDialog({
                    model: {
                        timeRange: this.model.inmem.workingTimeRange,
                        user: this.model.user,
                        appLocal: this.model.appLocal,
                        application: this.model.application
                    },
                    collection: this.collection.times,
                    showPresetsRealTime:false,
                    showCustomRealTime:false,
                    showCustomDate:false,
                    showCustomDateTime:false,
                    showPresetsAllTime:true,
                    enableCustomAdvancedRealTime:false,
                    appendSelectDropdownsTo: '.modal:visible'
                });

                if (this.model.user.canUseAlerts()) {

                    this.deferredPdfAvailable = pdfUtils.isPdfServiceAvailable();

                    var alertActionsManagerModel = new ManagerViewModel();
                    alertActionsManagerModel.set('id', 'alert_actions');
                    this.deferredManagerAvailable = alertActionsManagerModel.binaryPromiseFetch({
                        data: {
                            app: this.model.application.get("app"),
                            owner: this.model.application.get("owner")
                        }
                    });
                    this.collection.alertActionUIs = new ModAlertsUICollection();
                    // TODO: Add fetch data options - currently doing and unbounded fetch
                    this.deferredAlertActionUIsCollection = this.collection.alertActionUIs.fetch({
                        data: {
                            app: this.model.application.get("app"),
                            owner: this.model.application.get("owner"),
                            count: 1000
                        }
                    });

                    // TODO: Add fetch data options - currently doing and unbounded fetch
                    if (!this.collection.alertActions) {
                        this.collection.alertActions = new ModAlertActionsCollection();
            
                        this.deferredAlertActionCollection = this.collection.alertActions.fetch({
                            data: {
                                app: this.model.application.get("app"),
                                owner: this.model.application.get("owner"),
                                search: 'disabled!=1'
                            },
                            addListInTriggeredAlerts: false
                        });
                    } else {
                        this.deferredAlertActionCollection = $.Deferred().resolve();
                    }

                    $.when(this.deferredPdfAvailable, this.deferredManagerAvailable, this.deferredAlertActionCollection)
                        .then(function(pdfAvailable, managerAvailable) {
                            this.children.actions = new TriggerActionsView({
                                model: {
                                    document: this.model.inmem,
                                    application: this.model.application
                                },
                                collection: {
                                    alertActions: this.collection.alertActions,
                                    alertActionUIs: this.collection.alertActionUIs
                                },
                                pdfAvailable: _.isArray(pdfAvailable) ? pdfAvailable[0] : pdfAvailable,
                                canViewAlertActionsManager: managerAvailable
                            });
                    }.bind(this));
                }

                this.model.inmem.workingTimeRange.on('applied', function() {
                    this.timeRangeDelegate.closeTimeRangePicker();
                }, this);
                this.model.inmem.on('change:scheduled_and_enabled', this.toggleChildren, this);
            },
            toggleChildren: function() {
                var action = this.model.inmem.get('scheduled_and_enabled') ? 'show' : 'hide';
                this.children.scheduleView.$el[action]();
                if (this.children.actions) {
                    this.children.actions.$el[action]();
                }
            },
            events: {
                'click .modal-btn-primary' : function(e) {
                    this.model.inmem.trigger('saveSchedule');
                    e.preventDefault();
                }
            },
            render: function() {
                $.when(this.deferredAlertActionCollection, this.deferredPdfAvailable, this.deferredAlertActionUIsCollection, this.deferredManagerAvailable).then(function() {
                    this.$el.html(Modal.TEMPLATE);

                    if (this.model.report.isNew()) {
                        this.$(Modal.HEADER_TITLE_SELECTOR).html(_("Schedule Report").t());
                    } else {
                        this.$(Modal.HEADER_TITLE_SELECTOR).html(_("Edit Schedule").t());
                    }

                    this.$(Modal.BODY_SELECTOR).remove();

                    this.$(Modal.FOOTER_SELECTOR).before(
                        '<div class="vis-area">' +
                            '<div class="slide-area">' +
                                '<div class="content-wrapper schedule-wrapper">' +
                                    '<div class="' + Modal.BODY_CLASS + '" >' +
                                    '</div>' +
                                '</div>' +
                                '<div class="timerange-picker-wrapper">' +
                                '</div>' +
                            '</div>' +
                        '</div>'
                    );

                    this.$visArea = this.$('.vis-area').eq(0);
                    this.$slideArea = this.$('.slide-area').eq(0);
                    this.$scheduleWrapper = this.$('.schedule-wrapper').eq(0);
                    this.$timeRangePickerWrapper = this.$('.timerange-picker-wrapper').eq(0);
                    this.$modalParent = $('.schedule-modal').eq(0);

                    this.children.flashMessage.render().prependTo(this.$(Modal.BODY_SELECTOR));
                    this.children.title.render().appendTo(this.$(Modal.BODY_SELECTOR));
                    this.children.scheduleView.render().appendTo(this.$(Modal.BODY_SELECTOR));
                    if (this.children.actions) {
                        this.children.actions.render().appendTo(this.$(Modal.BODY_SELECTOR));
                    }

                    this.children.timeRangePickerView.render().appendTo(this.$timeRangePickerWrapper);

                    this.timeRangeDelegate = new TimeRangeDelegate({
                        el: this.el,
                        $visArea: this.$visArea,
                        $slideArea: this.$slideArea,
                        $contentWrapper: this.$scheduleWrapper,
                        $timeRangePickerWrapper: this.$timeRangePickerWrapper,
                        $modalParent: this.$modalParent,
                        $timeRangePicker: this.children.timeRangePickerView.$el,
                        activateSelector: 'a.timerange-control',
                        backButtonSelector: 'a.btn.back'
                    });

                    this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                    this.$(Modal.FOOTER_SELECTOR).append('<a href="#" class="btn btn-primary modal-btn-primary">' + _('Save').t() + '</a>');
                    this.$(Modal.FOOTER_SELECTOR).append('<a href="#" class="btn back modal-btn-back pull-left">' + _('Back').t() + '</a>');
                    this.$('.btn.back').hide();

                    this.toggleChildren();
                }.bind(this));
                return this;
            }
        });
    }
);
