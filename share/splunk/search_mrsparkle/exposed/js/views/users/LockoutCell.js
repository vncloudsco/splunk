define([
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'splunk.util'
    ],
    function (
        $,
        _,
        module,
        BaseView,
        splunkUtils
    ) {

        return BaseView.extend({
            moduleId: module.id,
            className: "lockout-cell",

			render: function () {
                var html;

                if (!splunkUtils.normalizeBoolean(this.model.entity.entry.content.get("locked-out"))) {
                    html = _.template(this.enabledtemplate);
                } else {
                    html = _.template(this.disabledtemplate);
                }

                this.$el.html(html);

                return this;
            },
			
            enabledtemplate: '\
                <i class="icon-check enable-icon"></i> <span class="enable-text"><%= _("Active").t() %></span>\
            ',

            disabledtemplate: '\
                <i class="icon-lock disable-icon"></i> <span class="enable-text"><%= _("Locked").t() %></span>\
            '

        });
    });

	