define(
        [
            'jquery',
            'underscore',
            'module',
            'models/shared/ScheduleWindow',
            'views/Base',
            'views/shared/ScheduleSentence',
            'views/shared/controls/ControlGroup',
            'views/shared/jobcontrols/menu/WorkloadInput',
            'splunk.i18n',
            'splunk.util'
        ],
        function(
            $,
            _,
            module,
            ScheduleWindowModel,
            Base,
            ScheduleSentence,
            ControlGroup,
            WorkloadInput,
            i18n,
            splunkUtil
        ) {
        return Base.extend({
            moduleId: module.id,
            className: 'form form-horizontal form-complex',
            /**
            * @param {Object} options {
            *        model: {
            *            application: <models.Application>
            *            inmem: <models.Report>,
            *            user: <models.services.admin.User>,
            *            scheduleWindow: <models.shared.ScheduleWindow>
            *        },
            *        collection: {
            *           times: <collections.services.data.ui.Times>,
            *           workloadManagementStatus: <collections.services.admin.workload_management> (Optional.)
            *        },
            * }
            **/
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);
                if (!_.isEmpty(this.collection) && !_.isEmpty(this.collection.workloadManagementStatus) && !_.isEmpty(this.model.user)) {
                    this.children.workloadInput = new WorkloadInput({
                        workloadPoolAttribute: 'workload_pool',
                        isRunning: true,
                        includeEmptyOption: true,
                        model: {
                            inmem: this.model.inmem,
                            user: this.model.user,
                            workloadPool: this.model.inmem.entry.content
                        },
                        collection: {
                            workloadManagementStatus: this.collection.workloadManagementStatus
                        }
                    });
                }

                this.children.scheduleSentence = new ScheduleSentence({
                    model: {
                        cron: this.model.inmem.cron,
                        application: this.model.application
                    },
                    lineOneLabel: _('Schedule').t(),
                    popdownOptions: {
                        attachDialogTo: '.modal:visible',
                        scrollContainer: '.modal:visible .modal-body:visible'
                    }
                });

                if (this.model.user.canEditSearchScheduleWindow()) {
                    var scheduleWindowItems = [];
                    _.each(ScheduleWindowModel.VALUE_OPTIONS, function(value) {
                        var item = {};
                        item.value = value;
                        if (item.value === 'auto') {
                            item.label = _('Auto').t();
                        } else {
                            var valueAsInt = parseInt(value, 10);
                            if (valueAsInt === 0) {
                                item.label = _('No window').t();
                            } else {
                                if (valueAsInt < 60) {
                                    item.label = splunkUtil.sprintf(i18n.ungettext('%s minute', '%s minutes', valueAsInt), valueAsInt);
                                } else {
                                    var hours = parseInt(valueAsInt/60, 10);
                                    item.label = splunkUtil.sprintf(i18n.ungettext('%s hour', '%s hours', hours), hours);
                                }
                            }
                        }
                        scheduleWindowItems.push(item);
                    });

                    scheduleWindowItems.push({label: _('Custom').t(), value: 'custom'});

                    this.children.scheduleWindow = new ControlGroup({
                        className: 'control-group',
                        controlType: 'SyntheticSelect',
                        controlOptions: {
                            modelAttribute: 'schedule_window_option',
                            model: this.model.scheduleWindow,
                            items: scheduleWindowItems,
                            toggleClassName: 'btn',
                            popdownOptions: {
                                attachDialogTo: '.modal:visible',
                                scrollContainer: '.modal:visible .modal-body:visible'
                            }
                        },
                        tooltip: _('Let report run at any time within a window that opens at its scheduled run time, ' +
                            'to improve efficiency when there are many concurrently scheduled reports. The “Auto” ' +
                            'setting automatically determines the best window width for the report.').t(),
                        label: _('Schedule Window').t()
                    });

                    this.children.customWindow = new ControlGroup({
                        controlType: 'Text',
                        controlOptions: {
                            additionalClassNames: 'custom-window',
                            modelAttribute: 'custom_window',
                            model: this.model.scheduleWindow
                        },
                        label: _('Custom Window').t()
                    });
                }

                if (this.model.user.canEditSearchSchedulePriority()) {
                    var schedulePriorityItems = [
                        { label: _('Default').t(), value: 'default'},
                        { label: _('Higher').t(), value: 'higher'},
                        { label: _('Highest').t(), value: 'highest'}
                    ];
                    this.children.schedulePriority = new ControlGroup({
                        className: 'control-group',
                        controlType: 'SyntheticSelect',
                        controlOptions: {
                            modelAttribute: 'schedule_priority',
                            model: this.model.inmem.entry.content,
                            items: schedulePriorityItems,
                            toggleClassName: 'btn',
                            popdownOptions: {
                                attachDialogTo: '.modal:visible',
                                scrollContainer: '.modal:visible .modal-body:visible'
                            }
                        },
                        tooltip: _('Raise the scheduling priority of a report. Set to “Higher” to prioritize it above ' +
                            'other searches of the same scheduling mode, or “Highest” to prioritize it above other ' +
                            'searches regardless of mode. Use with discretion.').t(),
                        label: _('Schedule Priority').t()
                    });
                }

                //event listeners
                this.model.inmem.workingTimeRange.on('applied', function() {
                    this.setLabel();
                }, this);
                this.model.inmem.workingTimeRange.on('change:earliest_epoch change:latest_epoch change:earliest change:latest', _.debounce(this.setLabel, 0), this);

                this.listenTo(this.model.scheduleWindow, 'change:schedule_window_option', this.toggleCustomWindow);
            },
            toggleCustomWindow: function() {
                if (this.children.scheduleWindow){
                if (this.model.scheduleWindow.get('schedule_window_option') === 'custom') {
                    this.children.customWindow.$el.show();
                } else {
                    this.children.customWindow.$el.hide();
                        }
                }
            },
            setLabel: function() {
                var timeLabel = this.model.inmem.workingTimeRange.generateLabel(this.collection.times);
                this.$el.find("span.time-label").text(timeLabel);
            },
            render: function() {
                this.children.scheduleSentence.render().appendTo(this.$el);

                this.$el.append('<div class="control-group timerange" style="display: block;"><label class="control-label">' + _('Time Range').t() + '</label></div>');
                this.$('div.timerange').append('<div class="controls"><a href="#" class="btn timerange-control"><span class="time-label"></span><span class="icon-triangle-right-small"></span></a></div>');

                this.children.schedulePriority && this.children.schedulePriority.render().appendTo(this.$el);
                if (this.children.scheduleWindow) {
                    this.children.scheduleWindow.render().appendTo(this.$el);
                    this.children.customWindow.render().appendTo(this.$el);
                    this.$('.custom-window').append('<span class="custom-window-text">'+_('minutes').t()+'</span>');
                }
                if (this.children.workloadInput) this.children.workloadInput.render().appendTo(this.$el);

                this.setLabel();
                this.toggleCustomWindow();

                return this;
            }
        });
    }
);
