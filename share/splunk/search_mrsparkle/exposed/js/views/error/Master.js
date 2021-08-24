define(
    [
        'underscore',
        'jquery',
        'views/Base',
        'models/shared/Error',
        'uri/route',
        'splunk.util',
        'contrib/text!./Master.html',
        './Master.pcss'
    ],
    function(
        _,
        $,
        Base,
        ErrorModel,
        route,
        splunkUtils,
        template,
        css
    ) {
        return Base.extend({
            render: function() {
                var root = this.model.application.get("root"),
                    locale = this.model.application.get("locale"),
                    home = route.home(root, locale),
                    back = document.referrer,
                    isLight = this.model.serverInfo && this.model.serverInfo.isLite(),
                    returnLink = back || home,
                    returnMessage = back ? _("go back.").t() : _("go to Splunk Homepage.").t();

                this.$el.html(this.compiledTemplate({
                    _:_,
                    splunkUtils: splunkUtils,
                    status: (this.model.error.get("status")) ? _(this.model.error.get("status")).t() : "",
                    message: (this.model.error.get("message")) ? _(this.model.error.get("message")).t() : "",
                    brandClass: isLight ? 'brand-light' : 'brand-enterprise'
                }));
                if (this.model.error.get("learnmore")) {
                    var docUrl = route.docHelp(root, locale, this.model.error.get("learnmore"));
                    this.$(".error-message > p")
                        .append(splunkUtils.sprintf(_('<a href="%s" target="_blank" title="Splunk help">Learn more <i class="icon-external"></i></a> ').t(), docUrl))
                        .append(splunkUtils.sprintf(_('Click <a class="return-to-splunk-home" href="' + returnLink + '">here</a> to %s').t(), returnMessage));
                } else {
                    this.$(".error-message > p").append(
                        splunkUtils.sprintf(_('Click <a class="return-to-splunk-home" href="' + returnLink + '">here</a> to %s').t(), returnMessage)
                    );
                }
                return this;
            },
            template: template
        });
    }
);
