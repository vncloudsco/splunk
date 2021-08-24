define(
    [
        'jquery',
        'module',
        'underscore',
        'views/Base',
        'views/shared/controls/ControlGroup',
        'views/shared/controls/SyntheticSelectControl',
        'uri/route',
        'splunk.util',
        './ScheduleSentence.pcss'
    ],
    function(
        $,
        module,
        _,
        BaseView,
        ControlGroup,
        SyntheticSelectControl,
        route,
        splunkUtil,
        css
    ){
        return BaseView.extend({
            moduleId: module.id,
            className: 'schedule-sentence',
            /**
            * @param {Object} options {
            *   model: {
            *       cron: <models.Cron>,
            *       application: <models.Application>
            *   }
            *   {String} lineOneLabel: (Optional) Label for the first line of the sentence. Defalult is none.
            *   {String} lineTwoLabel: (Optional) Label for the second line of the sentence. Defalult is none.
            * }
            */
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                var defaults = {
                    lineOneLabel: '',
                    lineTwoLabel: ''
                };

                _.defaults(this.options, defaults);

                var makeItems = function(num) {
                        var stringNum = num.toString();
                        return { label: stringNum, value: stringNum};
                    },
                    hourly = _.map(_.range(0, 46, 15), makeItems),
                    daily = _.map(_.range(24), function(num) {
                        return { label: num + ':00', value: num.toString()};
                    }),
                    monthly = _.map(_.range(1,32), makeItems);

                this.children.timeRange = new ControlGroup({
                    className: 'control-group',
                    controlType: 'SyntheticSelect',
                    controlOptions: {
                        ariaLabel: this.options.lineOneLabel || _('Schedule ').t(),
                        modelAttribute: 'cronType',
                        model: this.model.cron,
                        items: [
                            { label: _('Run every hour').t(), value: 'hourly' },
                            { label: _('Run every day').t(), value: 'daily' },
                            { label: _('Run every week').t(), value: 'weekly' },
                            { label: _('Run every month').t(), value: 'monthly' },
                            { label: _('Run on Cron Schedule').t(), value: 'custom' }
                        ],
                        save: false,
                        toggleClassName: 'btn',
                        labelPosition: 'outside',
                        elastic: true,
                        popdownOptions: $.extend(true, {}, this.options.popdownOptions)
                    },
                    label: this.options.lineOneLabel
                });

                this.children.hourly = new SyntheticSelectControl({
                    additionalClassNames: 'schedule_hourly',
                    modelAttribute: 'minute',
                    model: this.model.cron,
                    items: hourly,
                    save: false,
                    toggleClassName: 'btn',
                    labelPosition: 'outside',
                    elastic: true,
                    ariaLabel: _('Select how many minutes past the hour to schedule the alert').t(),
                    popdownOptions: $.extend(true, {}, this.options.popdownOptions)
                });

                this.children.weekly = new SyntheticSelectControl({
                    additionalClassNames: 'schedule_weekly',
                    modelAttribute: 'dayOfWeek',
                    model: this.model.cron,
                    items: [
                        { label: _('Monday').t(),    value: '1'  },
                        { label: _('Tuesday').t(),   value: '2'  },
                        { label: _('Wednesday').t(), value: '3'  },
                        { label: _('Thursday').t(),  value: '4'  },
                        { label: _('Friday').t(),    value: '5'  },
                        { label: _('Saturday').t(),  value: '6'  },
                        { label: _('Sunday').t(),    value: '0'  }
                    ],
                    save: false,
                    toggleClassName: 'btn',
                    labelPosition: 'outside',
                    ariaLabel: _('Select which day of the week the alert is scheduled').t(),
                    popdownOptions: $.extend(true, {}, this.options.popdownOptions)
                });

                this.children.monthly = new SyntheticSelectControl({
                    menuClassName: 'dropdown-menu-short',
                    additionalClassNames: 'schedule_monthly',
                    modelAttribute: 'dayOfMonth',
                    model: this.model.cron,
                    items: monthly,
                    save: false,
                    toggleClassName: 'btn',
                    labelPosition: 'outside',
                    ariaLabel: _('Select which day of the month the alert is scheduled').t(),
                    popdownOptions: $.extend(true, {}, this.options.popdownOptions)
                });

                this.children.daily = new SyntheticSelectControl({
                    menuClassName: 'dropdown-menu-short',
                    additionalClassNames: 'schedule_daily',
                    modelAttribute: 'hour',
                    model: this.model.cron,
                    items: daily,
                    save: false,
                    toggleClassName: 'btn',
                    labelPosition: 'outside',
                    ariaLabel: _('Select which hour of the day the alert is scheduled').t(),
                    popdownOptions: $.extend(true, {},
                         this.options.popdownOptions)
                });

                this.children.scheduleOptions = new ControlGroup({
                    controls: [
                        this.children.hourly,
                        this.children.weekly,
                        this.children.monthly,
                        this.children.daily
                    ],
                    controlsLayout: 'separate',
                    label: this.options.lineTwoLabel
                });

                var docRoute = route.docHelp(
                    this.model.application.get("root"),
                    this.model.application.get("locale"),
                    'learnmore.alert.scheduled'
                );
                this.children.cronSchedule = new ControlGroup({
                    controlType: 'Text',
                    controlOptions: {
                        modelAttribute: 'cron_schedule',
                        model: this.model.cron
                    },
                    label: _('Cron Expression').t(),
                    help: splunkUtil.sprintf(_('e.g. 00 18 *** (every day at 6PM). %s').t(),
                        '<a href="'+ docRoute +'" class="help" target="_blank" title="' + _("Splunk help").t() + '"' +
                        'aria-label="' + _("Learn more about cron schedule").t() +
                        '">' + _("Learn More").t() + '</a>')
                });

                this.activate();
            },
            timeRangeToggle: function() {
                this.children.hourly.$el.hide();
                this.children.daily.$el.hide();
                this.children.weekly.$el.hide();
                this.children.monthly.$el.hide();

                this.$preLabel.hide();
                this.$hourPostLabel.hide();
                this.$weeklyPreLabel.hide();
                this.$monthlyPreLabel.hide();
                this.$dailyPreLabel.hide();

                this.$customControls.css('display', 'none');

                switch(this.model.cron.get('cronType')){
                    case 'hourly':
                        this.children.scheduleOptions.$el.show();
                        this.children.hourly.$el.css('display', '');
                        this.$preLabel.css('display', '');
                        this.$hourPostLabel.css('display', '');
                        break;
                    case 'daily':
                        this.children.scheduleOptions.$el.show();
                        this.children.daily.$el.css('display', '');
                        this.$preLabel.css('display', '');
                        break;
                    case 'weekly':
                        this.children.scheduleOptions.$el.show();
                        this.children.weekly.$el.css('display', '');
                        this.children.daily.$el.css('display', '');
                        this.$weeklyPreLabel.css('display', '');
                        this.$dailyPreLabel.css('display', '');
                        break;
                    case 'monthly':
                        this.children.scheduleOptions.$el.show();
                        this.children.monthly.$el.css('display', '');
                        this.children.daily.$el.css('display', '');
                        this.$monthlyPreLabel.css('display', '');
                        this.$dailyPreLabel.css('display', '');
                        break;
                    case 'custom':
                        this.$customControls.css('display', '');
                        this.children.scheduleOptions.$el.hide();
                        break;
                }
            },
            startListening: function() {
                this.listenTo(this.model.cron, 'change:cronType', function() {
                    this.timeRangeToggle();
                    this.model.cron.setDefaults();
                });
            },
            render: function()  {
                this.$el.append(this.children.timeRange.render().el);
                this.$el.append(this.children.scheduleOptions.render().el);

                this.$preLabel = $(_.template(this.labelTemplate, {
                    labelClass: 'pre_label',
                    label: _("At ").t()
                }));
                
                this.$hourPostLabel = $(_.template(this.labelTemplate, {
                    labelClass: 'hour_post_label',
                    label: _(" minutes past the hour ").t()
                }));
                
                this.$weeklyPreLabel = $(_.template(this.labelTemplate, {
                    labelClass: 'weekly_pre_label',
                    label: _("On ").t()
                }));
                
                this.$monthlyPreLabel = $(_.template(this.labelTemplate, {
                    labelClass: 'monthly_pre_label',
                    label: _("On day ").t()
                }));
                
                this.$dailyPreLabel = $(_.template(this.labelTemplate, {
                    labelClass: 'daily_pre_label',
                    label: _(" at ").t()
                }));
                
                this.children.scheduleOptions.$('.schedule_hourly')
                    .before(this.$preLabel)
                    .after(this.$hourPostLabel);

                this.children.scheduleOptions.$('.schedule_weekly')
                    .before(this.$weeklyPreLabel);

                this.children.scheduleOptions.$('.schedule_monthly')
                    .before(this.$monthlyPreLabel);

                this.children.scheduleOptions.$('.schedule_daily')
                    .before(this.$dailyPreLabel);
                    
                this.$customControls = $('<div class="custom_time"></div>');
                this.$el.append(this.$customControls);
                this.$customControls.append(this.children.cronSchedule.render().el);

                this.timeRangeToggle();

                return this;
            },
            
            labelTemplate:
                '<span role="label" class="<%- labelClass %> input-label">\
                    <%- label %>\
                </span>'
        });
     }
 );
