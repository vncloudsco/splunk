define(
    [
        'underscore',
        'jquery',
        'models/search/Report',
        'models/shared/Cron',
        'models/shared/TimeRange',
        'util/validation',
        'splunk.util'
    ],
    function(
        _,
        $,
        ReportModel,
        CronModel,
        TimeRangeModel,
        ValidationUtils,
        splunkUtil
    ) {
        var ScheduledReportModel = ReportModel.extend({
            initialize: function() {
                ReportModel.prototype.initialize.apply(this, arguments);
            },

            initializeAssociated: function() {
                ReportModel.prototype.initializeAssociated.apply(this, arguments);
                var RootClass = this.constructor;
                this.associated = this.associated || {};
                
                this.cron = this.cron || new RootClass.Cron();
                this.associated.cron = this.cron;
                
                this.workingTimeRange = this.workingTimeRange || new RootClass.WorkingTimeRange({enableRealTime:false});
                this.associated.workingTimeRange = this.workingTimeRange;
            },

            setFromSplunkD: function(payload, options) {
                ReportModel.prototype.setFromSplunkD.apply(this, arguments);
                this.transposeFromSavedsearch();
            },

            parse: function(response) {
                var parsedResponse = ReportModel.prototype.parse.apply(this, arguments);
                this.transposeFromSavedsearch();
                return parsedResponse;
            },

            sync: function(method, model, options) {
                options = $.extend(true, {}, options || {});
                if (method === 'create' || method === 'update') {
                    
                    // transposeToSavedsearch is called below and sets values on the entry content
                    // save the original values to set back on the mode if there is an error.
                    var cloneContent = model.entry.content.clone().toJSON(),
                        error = options.error;
                        
                    options.error = function () {
                        model.entry.content.set(cloneContent);
                        if (error) {
                            error.apply(this, arguments);
                        }
                    };
                    
                    this.transposeToSavedsearch();
                }

                return ReportModel.prototype.sync.apply(this, arguments);
            },

            validate: function(attrs, setOptions) {
                var errors = _.extend({}, ReportModel.prototype.validate.apply(this, arguments), this.entry.content.validate());

                if (this.get('scheduled_and_enabled')) {
                    _.extend(errors, this.cron.validate());
                } else {
                    this.cron.clearErrors();
                }

                if (_.isEmpty(errors)) {
                    return undefined;
                } else {
                    return errors;
                }
            },

            transposeToSavedsearch: function() {
                if (this.get('scheduled_and_enabled')) {
                    // SPL-109045: Set dispatchAs to owner if report is scheduled.
                    this.entry.content.set({
                        'is_scheduled': 1,
                        'disabled': 0,
                        'cron_schedule': this.cron.getCronString(),
                        'dispatchAs': 'owner',
                        'dispatch.earliest_time': this.workingTimeRange.get('earliest'),
                        'dispatch.latest_time':this.workingTimeRange.get('latest')
                    });

                    this.transposeActionsToSavedsearch();

                } else {
                    this.entry.content.set('is_scheduled', 0);
                }
            },

            transposeActionsToSavedsearch: function() {
                if (this.entry.content.get('action.email')) {
                    var sendResults = splunkUtil.normalizeBoolean(this.entry.content.get('action.email.sendpdf')) ||
                            splunkUtil.normalizeBoolean(this.entry.content.get('action.email.sendcsv')) ||
                            splunkUtil.normalizeBoolean(this.entry.content.get('action.email.inline'));
                    this.entry.content.set('action.email.sendresults', +sendResults);
                }

                var actions = [];

                _.each(this.entry.content.attributes, function(value, attr) {
                    if (value == true) {
                        var actionName = attr.match(/^action.([^\.]*)$/);
                        if (actionName) {
                            actions.push(actionName[1]);
                        }
                    }
                });

                this.entry.content.set('actions', actions.join(', '));
            },

            transposeFromSavedsearch: function() {
                this.set({
                    scheduled_and_enabled: !this.entry.content.get('disabled') && this.entry.content.get('is_scheduled')
                });
                this.cron.setFromCronString(this.entry.content.get('cron_schedule') || '0 6 * * 1');

                this.workingTimeRange.save({
                    'earliest': this.entry.content.get('dispatch.earliest_time'),
                    'latest': this.entry.content.get('dispatch.latest_time')
                });
            },
            unsetUnselectedActionArgs: function () {
                var removedAttr = {};
                _.each(this.entry.content.attributes, function(value, attr) {
                    var match = attr.match(/^action.([^\.]*)\./);
                    if (match && !this.entry.content.get('action.' + match[1])) {
                        removedAttr[attr] = value;
                        this.entry.content.unset(attr);
                    }
                }.bind(this));
                return removedAttr;
            }
        },
        {
            Cron: CronModel,
            WorkingTimeRange: TimeRangeModel
        });

        // break the shared reference to Entry
        ScheduledReportModel.Entry = ScheduledReportModel.Entry.extend({});
        // now we can safely extend Entry.Content
        ScheduledReportModel.Entry.Content = ScheduledReportModel.Entry.Content.extend({
            validation: {
                'action.script.filename': {
                    fn: 'validateScriptFilename'
                },
                'action.email.to': {
                    fn: 'validateEmailTo'
                },
                'action.lookup.filename': {
                    fn: 'validateLookupFilename'
                }
            },
            validateScriptFilename: function(value, attr, computedState) {
                if (computedState['action.script']) {
                    if (_.isUndefined(value) || $.trim(value).length === 0) {
                        return _('A file name is required if script action is enabled').t();
                    }

                    if (!ValidationUtils.isValidFilename(value)) {
                       return _("Script file name cannot contain '..', '/', or '\\'").t();
                    }
                }
            },
            validateEmailTo: function(value, attr, computedState) {
                 if (computedState['action.email']) {
                    if (_.isUndefined(value) || $.trim(value).length === 0) {
                        return _('An email address is required if email action is enabled').t();
                    }

                    if (!ValidationUtils.isValidEmailList(value)) {
                        return _('One of the email addresses is invalid').t();
                    }
                 }
            },
            validateLookupFilename: function(value, attr, computedState) {
                if (splunkUtil.normalizeBoolean(computedState['action.lookup'])) {
                    if ((_.isUndefined(value) || $.trim(value).length === 0)) {
                        return _('A file name is required if lookup action is enabled').t();
                    }
                    if (!/.*\.csv$/.test(value) || !ValidationUtils.isValidFilename(value)) {
                        return _("Lookup file name must end with .csv and cannot contain '..', '/', or '\\'").t();
                    }
                }
            }
        });
        return ScheduledReportModel;
    }
);