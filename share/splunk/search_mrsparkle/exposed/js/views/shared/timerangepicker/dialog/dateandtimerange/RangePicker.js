define([
        "jquery",
        "underscore",
        "backbone",
        "module",
        "models/shared/DateInput",
        "models/shared/TimeRange",
        'views/Base',
        "views/shared/controls/DateControl",
        "views/shared/timerangepicker/dialog/dateandtimerange/timeinput/Master"
      ],
     function($, _, Backbone, module, DateInputModel, TimeRangeModel, Base, DateControl, TimeInput) {
        return Base.extend({
            moduleId: module.id,
            initialize: function(options) {
                Base.prototype.initialize.apply(this, arguments);

                this.canSetTime = this.options.canSetTime;

                if (this.canSetTime) {
                    this.children.earliestTimeInput = new TimeInput({
                        inputClassName: 'timerangepicker-earliest',
                        model: {
                            dateTime: this.model.earliestDateInput
                        },
                        legendLabel: _("Earliest").t()
                    });

                    this.children.latestTimeInput = new TimeInput({
                        inputClassName: 'timerangepicker-latest',
                        model: {
                            dateTime: this.model.latestDateInput
                        },
                        legendLabel: _("Latest").t()
                    });
                } else {
                    this.children.earliestTimeInput = new DateControl({
                        model: this.model.earliestDateInput,
                        inputClassName: "timerangepicker-earliest-date",
                        validate: true,
                        ariaLabel: _("Earliest Date").t()
                    });

                    this.children.latestTimeInput = new DateControl({
                        model: this.model.latestDateInput,
                        inputClassName: "timerangepicker-latest-date",
                        validate: true,
                        ariaLabel: _("Latest Date").t()
                    });
                }

                this.activate();
            },

            activate: function(options) {
                if (this.el.innerHTML) {
                    this.render();
                }
                return Base.prototype.activate.apply(this, arguments);
            },

            startListening: function() {
                this.listenTo(this.model.rangeSelector, 'change:range_type', this.render);
            },

            render: function() {
                var rangeType = this.model.rangeSelector.get('range_type') || 'between_dates';

                if (!this.el.innerHTML) {
                    var template = this.compiledTemplate({
                            _: _,
                            canSetTime: this.canSetTime
                        });
                    this.$el.html(template);

                    this.children.earliestTimeInput.render().prependTo(this.$('.earliest_picker'));
                    this.children.latestTimeInput.render().prependTo(this.$('.latest_picker'));
                }

                var latestClass = 'only-latest';

                if (rangeType === 'before_date') {
                    this.$('.time-between-dates').addClass(latestClass);
                    this.$('.earliest_picker').hide();
                    this.$('.up-to-now').hide();
                    this.$('.and').hide();
                    this.$('.latest_picker').show();
                    this.$('.latest_picker').find('.help-time').html(_("00:00:00").t());
                } else if (rangeType === 'after_date'){
                    this.$('.time-between-dates').removeClass(latestClass);
                    this.$('.earliest_picker').show();
                    this.$('.up-to-now').show();
                    this.$('.and').hide();
                    this.$('.latest_picker').hide();
                } else {
                    this.$('.time-between-dates').removeClass(latestClass);
                    this.$('.earliest_picker').show();
                    this.$('.up-to-now').hide();
                    this.$('.and').show();
                    this.$('.latest_picker').show();
                    this.$('.latest_picker').find('.help-time').html(_("24:00:00").t());
                }

                return this;
            },

            template: '\
                <div class="time-between-dates">\
                    <div class="earliest_picker col-1">\
                        <% if (!canSetTime) { %>\
                            <span class="help-block"><%- _("00:00:00").t() %></span>\
                        <% } %>\
                    </div>\
                    <label class="and control-label"><%- _("and").t() %></label>\
                    <div class="help-block up-to-now">(<%- _("up to now").t() %>)</div>\
                    <div class="latest_picker col-2">\
                        <% if (!canSetTime) { %>\
                            <span class="help-block help-time"><%- _("24:00:00").t() %></span>\
                        <% } %>\
                    </div>\
                </div>\
            '
        });
    }
);
