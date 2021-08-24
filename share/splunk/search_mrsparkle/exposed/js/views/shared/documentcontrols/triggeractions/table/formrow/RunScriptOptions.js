define(
    [
        'underscore',
        'backbone',
        'module',
        'views/Base',
        'views/shared/controls/ControlGroup',
        'views/shared/controls/Control',
        'uri/route',
        'splunk.util'
    ],
    function(_,
        Backbone,
        module,
        Base,
        ControlGroup,
        Control,
        route,
        splunkUtil
    ) {
        var DeprecationNotice = Base.extend({
            className: 'alert alert-warning',
            render: function() {
                this.$el.html(this.compiledTemplate({
                    helpLink: route.docHelp(
                        this.model.application.get("root"),
                        this.model.application.get("locale"),
                        'learnmore.scripted.custom.alert.conversion'
                    )
                }));
                return this;
            },
            template: '' +
                    '<i class="icon-alert"></i> ' +
                    '<%- _("The run a script alert action is officially deprecated. Create a custom alert action to package a custom script instead.").t() %> ' +
                    '<a href="<%- helpLink %>" target="_blank" title="<%- _("Splunk Help").t() %>">' +
                        '<%- _("Learn more").t() %> <i class="icon-external"></i>' +
                    '</a>'
        });

        return Base.extend({
            moduleId: module.id,
            /**
             * @param {Object} options {
             *     model: {
             *         document: <models.search.Report>,
             *         application: <models.Application>
             *     }
             * }
             */
            tagName: 'form',
            className: 'form-vertical',
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);
                this.children.deprecationWarning = new DeprecationNotice({
                    model: {
                        application: this.model.application
                    }
                });
                this.children.scriptFile = new ControlGroup({
                    className: 'control-group control-group-run-script',
                    controlType: 'Text',
                    controlOptions: {
                        modelAttribute: 'action.script.filename',
                        model: this.model.document.entry.content
                    },
                    label: _('File name').t(),
                    help: splunkUtil.sprintf(_('Located in %s or %s').t(), '$SPLUNK_HOME/bin/scripts', '$SPLUNK_HOME/etc/'+ this.model.application.get('app') + '/bin/scripts')
                });
            },
            render: function()  {
                this.children.deprecationWarning.render().appendTo(this.$el);
                this.children.scriptFile.render().appendTo(this.$el);
                return this;
            }
        });
});
