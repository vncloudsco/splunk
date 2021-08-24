define(
    [
        'jquery',
        'underscore',
        'backbone',
        "module",
        "views/Base",
        "views/shared/timerangepicker/dialog/advanced/timeinput/Master",
        "views/shared/FlashMessages",
        "models/services/search/TimeParser",
        "models/shared/TimeRange",
        'uri/route',
        'util/console',
        'util/time'
    ],
    function($, _, Backbone, module, Base, TimeInput, FlashMessages, TimeParserModel, TimeRangeModel, route, console, time_utils) {
        return Base.extend({
            moduleId: module.id,
            className: 'accordion-inner form advanced-container',
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);

                this.label = _("Advanced").t();

                this.model.workingRange = new TimeRangeModel();
                this.model.earliestTimeParser = new TimeParserModel();
                this.model.latestTimeParser = new TimeParserModel();

                this.syncInternals();

                this.children.earliestTimeInput = new TimeInput({
                    model: {
                        working: this.model.workingRange,
                        timeParser: this.model.earliestTimeParser
                    },
                    label: _("Earliest").t(),
                    blankValue: '0',
                    modelAttribute: "earliest",
                    additionalClass: "col-1",
                    isLatest: false
                });

                this.children.latestTimeInput = new TimeInput({
                    model: {
                        working: this.model.workingRange,
                        timeParser: this.model.latestTimeParser
                    },
                    label: _("Latest").t(),
                    blankValue: '',
                    modelAttribute: "latest",
                    additionalClass: "col-2",
                    isLatest: true
                });

                this.children.flashMessages = new FlashMessages({
                    model: {
                        workingRange: this.model.workingRange,
                        earliestTimeParser: this.model.earliestTimeParser,
                        latestTimeParser: this.model.latestTimeParser
                    }
                });

                this.activate();
            },
            syncInternals: function() {
                this.model.workingRange.set($.extend(true, {
                    enableRealTime: this.options.enableCustomAdvancedRealTime
                }, this.model.timeRange.toJSON()));

                this.model.earliestTimeParser.set({
                    key: time_utils.stripRTSafe(this.model.timeRange.get("earliest"), false),
                    value: this.model.timeRange.get("earliest_iso")
                });

                this.model.latestTimeParser.set({
                    key: time_utils.stripRTSafe(this.model.timeRange.get("latest"), true),
                    value: this.model.timeRange.get("latest_iso")
                });
            },
            startListening: function() {
                this.listenTo(this.model.timeRange, 'change:earliest change:latest prepopulate', _.debounce(function() {
                    this.model.workingRange.set({
                        'earliest': this.model.timeRange.get('earliest'),
                        'latest': this.model.timeRange.get('latest')
                    });
                 }, 0));

                this.listenTo(this.model.workingRange, 'validated', function(validated, model, error_payload){
                    if (!validated) {
                        this.enableApply();
                    }
                });

                this.listenTo(this.model.earliestTimeParser, "serverValidated", function(valid, model, response, option) {
                    this.earliest_errored = !valid;
                    if (this.earliest_errored){
                        this.disableApply();
                    } else if (!this.latest_errored) {
                        this.enableApply();
                    }
                });

                this.listenTo(this.model.latestTimeParser, "serverValidated", function(valid, model, response, option) {
                    this.latest_errored = !valid;
                    if (this.latest_errored){
                        this.disableApply();
                    } else if (!this.earliest_errored) {
                        this.enableApply();
                    }
                });
            },
            activate: function(options) {
                if (this.active) {
                    return Base.prototype.activate.apply(this, arguments);
                }
                this.syncInternals();
                return Base.prototype.activate.apply(this, arguments);
            },
            deactivate: function(options) {
                if (!this.active) {
                    return Base.prototype.deactivate.apply(this, arguments);
                }
                Base.prototype.deactivate.apply(this, arguments);

                this.model.workingRange.fetchAbort();
                this.model.workingRange.clear({setDefaults: true});
                this.model.earliestTimeParser.fetchAbort();
                this.model.earliestTimeParser.clear({setDefaults: true});
                this.model.latestTimeParser.fetchAbort();
                this.model.latestTimeParser.clear({setDefaults: true});

                return this;
            },
            remove: function() {
                Base.prototype.remove.apply(this, arguments);
                _.chain(this.model).omit(['appLocal', 'application', 'timeRange']).each(function(model){
                    model.deepOff();
                    model.fetchAbort();
                });
             },
            supportsRange: function() {
                return true; //supports anything
            },
            events: {
                "click .apply": function(event) {
                    if ($(event.currentTarget).hasClass("disabled")) {
                        event.preventDefault();
                        return;
                    }

                    var that = this,
                        earliest = this.children.earliestTimeInput.$('input').val() || '0',
                        latest = this.children.latestTimeInput.$('input').val() || '';

                    this.disableApply();

                    this.model.workingRange.save(
                            {
                                earliest: earliest,
                                latest: latest
                            },
                            {
                                success: function(model) {
                                    that.enableApply();
                                    var latest_date = model.get('latest_date'),
                                        latest_js_date = latest_date ? (new Date(latest_date.getTime())) : latest_date;
                                    that.model.timeRange.set({
                                        'earliest': model.get('earliest'),
                                        'latest': model.get('latest'),
                                        'earliest_epoch': model.get('earliest_epoch'),
                                        'latest_epoch': model.get('latest_epoch'),
                                        'earliest_iso': model.get('earliest_iso'),
                                        'latest_iso': model.get('latest_iso'),
                                        'earliest_date': new Date(model.get('earliest_date').getTime()),
                                        'latest_date': latest_js_date
                                    });
                                    that.model.timeRange.trigger("applied");
                                },
                                error: function(model, error) {
                                    that.enableApply();
                                }
                            }
                    );
                    event.preventDefault();
                }
            },
            enableApply: function() {
                this.$("#apply_" + this.cid).removeClass('disabled');
            },
            disableApply: function() {
                this.$("#apply_" + this.cid).addClass('disabled');
            },
            render: function() {
                var docRoute = route.docHelp(
                    this.model.application.get("root"),
                    this.model.application.get("locale"),
                    'learnmore.timerange.picker'
                );
                var template = _.template(this.template, {
                    _: _,
                    cid: this.cid,
                    docRoute: docRoute
                });
                this.$el.html(template);
                this.children.flashMessages.render().insertBefore(this.$(".control-group-container"));
                this.children.earliestTimeInput.render().appendTo(this.$(".control-group-container"));
                this.children.latestTimeInput.render().appendTo(this.$(".control-group-container"));

                return this;
            },
            template: '\
                    <div class="control-group-container"></div>\
                    <div class="apply-button-wrapper">\
                        <a href="<%- docRoute %>" target="_blank" title="<%- _("Splunk help").t() %>" class="btn-documentation"><%- _("Documentation").t() %> <i class="icon-external"></i></a>\
                        <button class="apply btn" id="apply_<%- cid %>"><%- _("Apply").t() %></button>\
                    </div>\
            '
    });
}
);
