/**
 * @author jszeto
 * @date 6/11/13
 *
 * Displays the summary information for a TSIDX namespace
 *
 * Inputs:
 *
 *     model {models/services/summarization/TStatsSummarization}
 */

define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'views/shared/FlashMessages',
    'splunk.util',
    'util/time',
    'splunk.i18n',
    'util/format_numbers_utils',
    'util/splunkd_utils',
    'views/data_model_manager/components/AccelerationInfo.pcss'

],
    function(
        $,
        _,
        module,
        BaseView,
        FlashMessagesView,
        splunkUtils,
        time_utils,
        i18n,
        numUtils,
        splunkDUtils,
        css
        ) {

        return BaseView.extend({
            tagName: 'dl',
            className: "list-dotted",
            moduleId: module.id,
            detailedInfo: false,

            initialize: function(options) {
                BaseView.prototype.initialize.call(this, options);

                this.model.on("change", this.debouncedRender, this);
                this.children.flashMessagesView = new FlashMessagesView();
            },

            formattedTimeString: function(timestr) {
                if (!timestr) {
                    return '';
                }
                return i18n.format_datetime_microseconds(
                    time_utils.jsDateToSplunkDateTimeWithMicroseconds(time_utils.isoToDateObject(timestr))
                );
            },

            events: {
                'click a.detailed-info-toggle': function(e) {
                    e.preventDefault();
                    this.detailedInfo = !this.detailedInfo;
                    this.debouncedRender();
                },
                'click a.overall-tooltip': function(e) {
                    e.preventDefault();
                },
                'click a.p50-tooltip': function(e) {
                    e.preventDefault();
                },
                'click a.p90-tooltip': function(e) {
                    e.preventDefault();
                }
            },

            render: function() {
                var accessCount = this.model.entry.content.get('summary.access_count'),
                    accessDateString = this.model.entry.content.get('summary.access_time'),
                    accessDate = accessCount===0 || accessDateString === undefined ? "-": this.formattedTimeString(accessDateString),
                    updatedString = this.model.entry.content.get('summary.mod_time'),
                    updatedDate = updatedString === undefined ? "-": this.formattedTimeString(updatedString),
                    lastStartString = this.model.entry.content.get('summary.latest_dispatch_time'),
                    lastStartDate = lastStartString === undefined ? "-": this.formattedTimeString(lastStartString),
                    html = this.compiledTemplate({
                        summary: this.model.entry.content,
                        summarySizeString: numUtils.bytesToFileSize(this.model.entry.content.get("summary.size")),
                        lastAccessed: accessDate,
                        lastUpdated: updatedDate,
                        lastStart: lastStartDate,
                        sourceGUID: this.model.get("source_guid"),
                        sprintf: splunkUtils.sprintf,
                        detailedInfo: this.detailedInfo
                    });

                this.$el.html(html);
                //add a warning message if we don't detect any existing summaries and we have a source guid set
                if (this.model.get("source_guid") && this.model.entry.content.get("summary.buckets") === 0) {
                    this.children.flashMessagesView.flashMsgHelper.addGeneralMessage("no_summaries_for_source_guid_message",
                        { type: splunkDUtils.WARNING,
                          html: _("Summaries for the data model at the specified source GUID are not found. " +
                                  "Verify that the data model at the source GUID is accelerated.").t()});
                } else {
                    this.children.flashMessagesView.flashMsgHelper.removeGeneralMessage("no_summaries_for_source_guid_message");
                }
                this.$('.flash-messages-placeholder').append(this.children.flashMessagesView.render().el);

                this.$('a.overall-tooltip').tooltip({animation:false,
                    title: "Ideally, summarization searches should take a uniform amount of time to complete. " +
                    "If these values are significantly different, the environment may be unhealthy or the system " +
                    "might be overloaded.",
                    container: 'body'});

                this.$('a.p50-tooltip').tooltip({animation:false, title: "The 50th percentile of summarization searches. " +
                    "50% of summarization searches have taken less time than this value.", container: 'body'});

                this.$('a.p90-tooltip').tooltip({animation:false, title: "The 90th percentile of summarization searches. " +
                    "90% of summarization searches have taken less time than this value.", container: 'body'});

                return this;
            },

            template: '\
                <% if (summary.get("summary.id")) { %>\
                    <div class="flash-messages-placeholder"></div>\
                    <% if (sourceGUID) { %>\
                        <dt><%- _("Source GUID").t() %></dt>\
                        <dd><%- sourceGUID %></dd>\
                    <% } %>\
                    <dt><%- _("Status").t() %></dt>\
                    <dd><% if (summary.get("summary.complete")) { %>\
                            <%- sprintf(_("%s%% Completed").t(), (summary.get("summary.complete")*100).toFixed(2)) %>\
                        <% } else { %>\
                            <%- _("Building").t() %>\
                        <% } %>\
                    </dd>\
                    <dt><%- _("Access Count").t() %></dt>\
                    <dd><%- sprintf(_("%s. Last Access: %s").t(), \
                    summary.get("summary.access_count"), lastAccessed) %></dd>\
                    <dt><%- _("Size on Disk").t() %></dt>\
                    <dd><%- summarySizeString %></dd>\
                    <dt><%- _("Summary Range").t() %></dt>\
                    <dd><%- sprintf(_("%s second(s)").t(), summary.get("summary.time_range")) %></dd>\
                    <dt><%- _("Buckets").t() %></dt>\
                    <dd><%- summary.get("summary.buckets") %></dd>\
                    <dt><%- _("Updated").t() %></dt>\
                    <dd><%- lastUpdated %></dd>\
                    <div class="detailed-info-toggle-container">\
                    <% if (detailedInfo) { %>\
                        <a href="#" class="detailed-info-toggle"><i class="toggle icon-chevron-down"></i><span class="detailed-info-heading"><%- _("Detailed Acceleration Information").t() %></span></a>\
                            <div>\
                                <h4><%- _("Runtime statistics - Last Run").t() %></h4>\
                                <dt><%- _("SID").t() %></dt>\
                                <dd><%- summary.get("summary.last_sid") ? summary.get("summary.last_sid") : "-"  %></dd>\
                                <dt><%- _("Start Time").t() %></dt>\
                                <dd><%- lastStart %></dd>\
                                <dt><%- _("Run Time").t() %></dt>\
                                <dd><%- sprintf(_("%s second(s)").t(), summary.get("summary.latest_run_duration")) %></dd>\
                                <% if (summary.get("summary.last_error")) { %>\
                                    <div><i class="alert-error icon-alert"></i><span class="info-text"><%- _("Some errors were detected in the latest run of the summarization search:").t() %></span></div>\
                                    <dt><%- _("Errors").t() %></dt>\
                                    <dd><%- summary.get("summary.last_error") %></dd>\
                                <% } %>\
                            </div>\
                            <div>\
                                <h4><%- _("Runtime statistics - Overall").t() %><a href="#" class="overall-tooltip tooltip-link"><%- _("?").t() %></a></h4>\
                                <div class=info-text>\
                                    <% if (summary.get("summary.run_stats")) {%>\
                                        <%- sprintf(_("Aggregate statistics are calculated on the runtime of the past %s summarization runs.").t(), Object.keys(summary.get("summary.run_stats")).length) %>\
                                    <% } else { %>\
                                        <%- _("No acceleration searches have run so far.").t() %>\
                                    <% } %>\
                                </div>\
                                <dt><%- _("Average").t() %></dt>\
                                <dd><%- sprintf(_("%s second(s)").t(), summary.get("summary.average_time")) %></dd>\
                                <dt><%- _("p50").t() %><a href="#" class="p50-tooltip tooltip-link"><%- _("?").t() %></a></dt>\
                                <dd><%- sprintf(_("%s second(s)").t(), summary.get("summary.p50")) %></dd>\
                                <dt><%- _("p90").t() %><a href="#" class="p90-tooltip tooltip-link"><%- _("?").t() %></a></dt>\
                                <dd><%- sprintf(_("%s second(s)").t(), summary.get("summary.p90")) %></dd>\
                            <% } else { %>\
                                <a href="#" class="detailed-info-toggle"><i class="toggle icon-chevron-right"></i><span class="detailed-info-heading"><%- _("Detailed Acceleration Information").t() %></span></a>\
                            <% } %>\
                        </div>\
                    </div>\
                 <% } %>\
            '
        });
    });
