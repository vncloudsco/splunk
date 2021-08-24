define(
    [
        'underscore',
        'module',
        'views/Base',
        'uri/route'
    ],
    function(_, module, Base, route) {

        /**
         * @constructor
         * @param options {Object} {
         *     model: {
         *        report: <models.search.Report>
         *        appLocal: <models.services.AppLocal>
         *        application: <models.shared.Application>
         *        summary: <models.search.Summary>
         *    }
         * }
         */

        return Base.extend({
            moduleId: module.id,
            className:'no-stats-wrapper',
            events: {
                'click .view-fields': function(e) {
                    e.preventDefault();
                    this.model.report.set('openFirstFieldInfo', true);

                    this.model.report.entry.content.set({
                        'display.page.search.tab': 'events',
                        'display.page.search.showFields': '1'
                    });
                },
                'click .open-in-pivot-button': function(e) {
                    e.preventDefault();
                    this.model.report.trigger('openInPivot');
                }
            },
            activate: function() {
                if(this.active) {
                    return Base.prototype.activate.apply(this, arguments);
                }
                Base.prototype.activate.apply(this, arguments);
                this.render();
                return this;
            },
            startListening: function() {
                Base.prototype.startListening.apply(this, arguments);
                this.listenTo(this.model.summary, 'sync', this.render);
            },
            render: function() {
                var hasFieldSummary = this.model.summary.fields && this.model.summary.fields.length > 0,
                    userCanPivot = this.model.user.canPivot();

                this.$el.html(this.compiledTemplate({
                    showOpenInPivot: hasFieldSummary && userCanPivot,
                    moreDocRoute: route.docHelp(this.model.application.get("root"),
                        this.model.application.get("locale"),
                        'learnmore.search.transforming')
                }));
                return this;
            },
            template: '\
                    <div class="alert alert-info">\
                        <i class="icon-alert"></i>\
                        <%- _("Your search isn\'t generating any statistic or visualization results. Here are some possible ways to get results.").t() %>\
                    </div>\
                    <div class="no-stats">\
		                    <% if(showOpenInPivot) { %>\
		                        <div class="no-stats-column">\
	                            	<a href="" class="no-stats-link open-in-pivot-button">\
		                                <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                                            width="62px" height="62px" viewBox="0 0 62 62" enable-background="new 0 0 62 62" xml:space="preserve">\
                                            <path id="XMLID_685_" d="M59,0H14.9h-2h-10C1.3,0,0,1.4,0,3.1v10v2v44C0,60.7,1.3,62,2.9,62h9c1.7,0,3.1-1.3,3.1-2.9V15h44\
                                                c1.7,0,3-1.3,3-2.9v-9C62,1.4,60.7,0,59,0z M2,3.1C2,2.5,2.4,2,2.9,2H13v11H2V3.1z M13,59.1c0,0.6-0.5,0.9-1.1,0.9h-9\
                                                C2.4,60,2,59.6,2,59.1V15h11V59.1z M60,12.1c0,0.6-0.4,0.9-1,0.9H15V2h44c0.6,0,1,0.5,1,1.1V12.1z"/>\
                                            <polygon id="XMLID_444_" points="26.3,55.7 21.6,51 26.3,46.3 27.7,47.7 24.4,51 27.7,54.3 "/>\
                                            <polygon id="XMLID_447_" points="54.3,27.7 51,24.4 47.7,27.7 46.3,26.3 51,21.6 55.7,26.3 "/>\
                                            <path id="XMLID_528_" d="M23,52v-2c15,0,27-12,27-26h2C52,39,39,52,23,52z"/>\
                                        </svg>\
	                                    <h3><%- _("Pivot").t() %></h3>\
		                            </a>\
		                             <span>\
		                               <%- _("Build tables and visualizations using multiple fields and metrics without writing searches.").t() %>\
		                            </span>\
	                            </div>\
	                        <% } %>\
	                        <div class="no-stats-column">\
	                            <a href="" class="no-stats-link view-fields">\
	                            	<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                                        width="60px" height="62px" viewBox="0 0 60 62" enable-background="new 0 0 60 62" xml:space="preserve">\
                                            <path id="XMLID_680_" d="M39,60H4c-1,0-2-1-2-1.9V12h10V2h31.7C44.8,2,45,3,45,3.5V30c0.7-0.1,1.3-0.1,2-0.1V3.5\
                                            C47,1.4,45.7,0,43.7,0H10.9L0,10.5v47.6c0,2,1.9,3.9,4,3.9h39c0.3,0,0.6-0.1,1-0.2C42.2,61.5,40.5,60.9,39,60z M10,3.6V10H3.4\
                                            L10,3.6z"/>\
                                        <g id="XMLID_959_">\
                                            <rect id="XMLID_958_" x="11" y="17" width="25" height="2"/>\
                                        </g>\
                                        <g id="XMLID_957_">\
                                            <rect id="XMLID_956_" x="11" y="23" width="20" height="2"/>\
                                        </g>\
                                        <g id="XMLID_955_">\
                                            <rect id="XMLID_954_" x="11" y="29" width="23" height="2"/>\
                                        </g>\
                                        <g id="XMLID_953_">\
                                            <rect id="XMLID_952_" x="11" y="35" width="18" height="2"/>\
                                        </g>\
                                        <path id="XMLID_666_" d="M31.8,41H11v2h20.3C31.4,42.3,31.6,41.6,31.8,41z"/>\
                                        <path id="XMLID_798_" d="M49.8,45.8l-2.7-1.1c-0.2-0.1-0.3-0.3-0.2-0.5l1.7-4.5c0.2-0.7-0.2-1-0.6-0.5l-4.6,6.5\
                                            c-0.1,0.2,0,0.4,0.2,0.4l2.9,1.1c0.2,0.1,0.3,0.3,0.2,0.4l-1.7,4.7c-0.1,0.3,0,0.5,0.3,0.5c0.1,0,0.2,0,0.2-0.1l4.5-6.5\
                                            C50.1,46.1,50,45.9,49.8,45.8z"/>\
                                        <path id="XMLID_659_" d="M47,59c-7.2,0-13-5.8-13-13s5.8-13,13-13s13,5.8,13,13S54.2,59,47,59z M47,35.3c-5.9,0-10.7,4.8-10.7,10.7\
                                            S41.1,56.7,47,56.7S57.7,51.9,57.7,46S52.9,35.3,47,35.3z"/>\
                                    </svg>\
	                            	<h3><%- _("Quick Reports").t() %></h3>\
	                            </a>\
	                            <span>\
	                               <%- _("Click on any field in the events tab for a list of quick reports like \'Top Referrers\' and \'Top Referrers by time\'.").t() %>\
	                            </span>\
                            </div>\
	                        <div class="no-stats-column">\
			                    <a href="<%- moreDocRoute %>" class="no-stats-link" target="_blank" title="<%- _("Splunk transforming commands documentation").t() %>">\
                                    <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                                        width="50px" height="62px" viewBox="0 0 50 62" enable-background="new 0 0 50 62" xml:space="preserve">\
                                        <g id="XMLID_637_">\
                                            <path id="XMLID_638_" d="M7.9,50c-0.9,0-2.3,1-2.3,2H47v-2H7.9z"/>\
                                        </g>\
                                        <g id="XMLID_628_">\
                                            <path id="XMLID_633_" d="M7.9,57c-0.9,0-2.3-1-2.3-2H47v2H7.9z"/>\
                                        </g>\
                                        <path id="XMLID_571_" d="M49,62H8.5C4,62,0.3,58.4,0,54h0V10C0,4.5,4.5,0,10,0h37c1.7,0,3,1.3,3,3v41c0,1.7-1.3,3-3,3H8.5\
                                            C4.9,47,2,49.9,2,53.5S4.9,60,8.5,60H49V62z M10,2c-4.4,0-8,3.6-8,8v38c1.5-1.8,3.8-3,6.4-3v0H47c0.6,0,1-0.4,1-1V3c0-0.6-0.4-1-1-1H10z"/>\
                                        <g id="XMLID_897_">\
                                            <path id="XMLID_896_" d="M13.6,31.2l-1.2-2.4l11.3-5.6v-0.3l-11.3-5.6l1.2-2.4L25,20.5c0.8,0.4,1.3,1.2,1.3,2.1v0.8\
                                                c0,0.9-0.5,1.7-1.3,2.1L13.6,31.2z"/>\
                                        </g>\
                                        <g id="XMLID_895_">\
                                            <rect id="XMLID_894_" x="26" y="29" width="13" height="2"/>\
                                        </g>\
                                    </svg>\
			                        <h3><%- _("Search Commands").t() %> <i class="icon-external"></i></h3>\
		                        </a>\
		                        <span><%- _("Use a transforming search command, like timechart or stats, to summarize the data.").t() %></span>\
		                    </div>\
                    </div>\
            '
        });
    }
);
