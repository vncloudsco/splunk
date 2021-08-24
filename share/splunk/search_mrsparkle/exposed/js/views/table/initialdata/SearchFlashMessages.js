define(
    [
        'jquery',
        'module',
        'views/shared/FlashMessages',
        'splunk.util',
        'uri/route'
    ], 
    function(
        $,
        module,
        FlashMessages,
        splunkUtil,
        route
    ) {

        var FlashMessagesView = FlashMessages.extend({
            moduleId: module.id,

            render: function() {
                this.$el.empty();

                this.$el.append(this.compiledTemplate({
                    flashMessages: this.flashMsgCollection,
                    application: this.options.applicationModel,
                    splunkUtil: splunkUtil,
                    route: route
                }));
                (!this.flashMsgCollection.length) ? this.$el.hide() : this.$el.show();
                return this;
            },

            template: '\
                <% flashMessages.each(function(flashMessage){ %> \
                    <div class="alert alert-<%- flashMessage.get("type") %>">\
                        <i class="icon-alert"></i>\
                        <%= splunkUtil.getWikiTransform(_.unescape(flashMessage.get("html"))) %>\
                        <% if (flashMessage.get("help")) { %>\
                            <a href="<%- route.docHelp(application.get("root"), application.get("locale"), flashMessage.get("help")) %>"\
                            target="_blank">\
                                <%- _("Learn More").t() %>\
                                <i class="icon-external"></i>\
                            </a>\
                        <% } %>\
                    </div>\
                <% }); %> \
            '
        });

        return FlashMessagesView;
    }
);