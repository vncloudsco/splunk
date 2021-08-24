define(
    [
        'underscore',
        'module',
        'views/shared/jobstatus/Count',
        'util/time',
        'splunk.i18n',
        'splunk.util'
    ],
    function(
        _,
        module,
        BaseCount,
        time_utils,
        i18n,
        splunkUtil
    ){
        return BaseCount.extend({
            className: 'summary-count status',
            moduleId: module.id,
            initialize: function(options) {
                BaseCount.prototype.initialize.apply(this, arguments);
            },
            
            template: '\
                <% if (!model.isNew()) { %>\
                    <% if (model.isDone()) { %>\
                        <i class="icon-check"></i>\
                        <% if (isEvents) { %>\
                            <%= splunkUtil.sprintf(i18n.ungettext("%s event", "%s events", eventCount), \'<span class="number">\' + eventCount + \'</span>\') %>\
                        <% } else { %>\
                            <%= splunkUtil.sprintf(i18n.ungettext("%s result", "%s results", eventCount), \'<span class="number">\' + eventCount + \'</span>\') %>\
                        <% } %>\
                        <%if (model.entry.content.get("isFinalized")) { %>\
                            <% if (earliest_date) { %>\
                                <%- splunkUtil.sprintf(_("(Partial results for %s to %s)").t(), i18n.format_datetime_microseconds(time_utils.jsDateToSplunkDateTimeWithMicroseconds(earliest_date)), i18n.format_datetime_microseconds(time_utils.jsDateToSplunkDateTimeWithMicroseconds(latest_date))) %>\
                            <% } else { %>\
                                <%- splunkUtil.sprintf(_("(Partial results for before %s)").t(), i18n.format_datetime_microseconds(time_utils.jsDateToSplunkDateTimeWithMicroseconds(latest_date))) %>\
                            <% } %>\
                        <% } else { %>\
                            <% if (earliest_date) { %>\
                                <%- splunkUtil.sprintf(_("(%s to %s)").t(), i18n.format_datetime_microseconds(time_utils.jsDateToSplunkDateTimeWithMicroseconds(earliest_date)), i18n.format_datetime_microseconds(time_utils.jsDateToSplunkDateTimeWithMicroseconds(latest_date))) %>\
                            <% } else { %>\
                                <%- splunkUtil.sprintf(_("(before %s)").t(), i18n.format_datetime_microseconds(time_utils.jsDateToSplunkDateTimeWithMicroseconds(latest_date))) %>\
                            <% } %>\
                        <% } %>\
                        <% if (eventCount == 0) {%>\
                            <% if (earliest_date) { %>\
                                <div class="warning-no-results"><i class="icon-alert"></i><%- _("No results found. Try expanding the time range.").t() %></div>\
                            <% } else { %>\
                                <div class="warning-no-results"><i class="icon-alert"></i><%- _("No results found.").t() %></div>\
                            <% } %>\
                        <% } %>\
                    <% } else if (model.isRunning()) { %>\
                        <%= splunkUtil.sprintf(i18n.ungettext("%s of %s event matched", "%s of %s events matched", scanCount), \'<span class="number">\' + eventCount + \'</span>\', \'<span class="number">\' + scanCount + \'</span>\') %>\
                    <% } else if (model.entry.content.get("isPaused")) { %>\
                        <i class="icon-warning icon-warning-paused"></i><%- _("Your search is paused.").t() %>\
                    <% } else { %>\
                        <%- progress %>\
                    <% } %>\
                <% } %>\
            '
        });
    }
);