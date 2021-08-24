define(
    [
        'underscore',
        'module',
        'views/Base',
        'splunk.config',
        'uri/route'
    ],
    function(
        _,
        module,
        BaseView,
        config,
        route
    )
    {
        return BaseView.extend({
            moduleId: module.id,
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
            },
            render: function() {
                var root = (config.MRSPARKLE_ROOT_PATH.indexOf("/") === 0 ? 
                    config.MRSPARKLE_ROOT_PATH.substring(1) : 
                    config.MRSPARKLE_ROOT_PATH
                );

                this.$el.html(this.compiledTemplate({
                    _: _,
                    helpLink: route.docHelp(root, config.LOCALE, "app.splunk_monitoring_console.monitoringconsole_configure")
                }));
                return this;
            },
            template: '\
                <h2 class="section-title"><%- _("Setup").t() %></h2>\
                <p class="section-description">\
                    <%- _("Current topology of your Splunk Enterprise deployment.").t() %>\
                    <a class="external" href="<%- helpLink %>" target="_blank"><%- _("Learn more").t()%></a>\
                </p>\
            '
        });
    }
);
