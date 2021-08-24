define(
    [
        'underscore',
        'module',
        'views/Base',
        'views/shared/Modal',
        'uri/route'
    ],
    function(
        _,
        module,
        Base,
        Modal,
        route
    ) {
        return Base.extend({
            moduleId: module.id,

            initialize: function(options) {
                Base.prototype.initialize.apply(this, arguments);
            },

            render: function() {
                var routeToSchedule = route.report(
                        this.model.application.get('root'),
                        this.model.application.get('locale'),
                        this.model.application.get("app"),
                        {
                            data: {
                                dialog: 'schedule',
                                s: this.model.report.get('id')
                            }
                        }
                    );

                this.$el.html(Modal.TEMPLATE);

                this.$(Modal.HEADER_TITLE_SELECTOR).append(_('Report Has Been Created').t());
                this.$(Modal.BODY_SELECTOR).html(this.compiledTemplate({
                    _: _,
                    report: this.model.report,
                    routeToSchedule: routeToSchedule,
                    message: this.options.message
                }));
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_OK);

                return this;
            },

            template: '\
                <div>\
                    <%- message %>\
                </div>\
                <% if (!report.isNew()) { %>\
                    <div class="schedule-info">\
                        <span><%- report.getScheduleString() %></span>\
                        <a href="<%= routeToSchedule %>"><%- _("Edit").t() %></a>\
                    </div>\
                <% } %>\
                \
            '
        });
    }
);
