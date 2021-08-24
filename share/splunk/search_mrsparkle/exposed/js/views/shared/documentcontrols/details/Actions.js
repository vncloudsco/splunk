define(
    [
        'underscore',
        'module',
        'views/Base',
        'uri/route',
        'splunk.i18n',
        'splunk.util',
        './Actions.pcss'
    ],
    function(_, module, Base, route, i18n, splunkUtil, css) {
        return Base.extend({
            moduleId: module.id,
            tagName: 'span',
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);
                this.actionsExpanded = true;
                this.activate();
            },
            startListening: function() {
                this.listenTo(this.model.document.entry.content, 'change:actions change:alert.track change:is_scheduled', this.debouncedRender);
            },
            events: {
                'click a': function(e) {
                    this.actionsExpanded = !this.actionsExpanded;
                    this.visibilty();
                    e.preventDefault();
                    e.stopPropagation();
                }
            },
            getAlertActions: function() {
                if (!this.model.document.entry.content.get('is_scheduled')) {
                    return [];
                }
                var actions = this.model.document.entry.content.get('actions'),
                    actionsArray = actions ? actions.split(',') : [],
                    activeActions = [];

                if (splunkUtil.normalizeBoolean(this.model.document.entry.content.get('alert.track'))) {
                    actionsArray.unshift('list');
                }
                _.each(actionsArray, function(activeAction) {
                    activeAction = activeAction.trim();
                    var alertAction = this.collection.alertActions.findByEntryName(activeAction);
                    if (alertAction) {
                        activeActions.push(alertAction);
                    }
                }, this);

                return activeActions;
            },
            visibilty: function() {
                var $expander = this.$('a.expand > i');
                if (this.actionsExpanded) {
                    $expander.addClass('icon-chevron-down');
                    $expander.removeClass('icon-chevron-right');
                    this.$('.action-item').show();
                    this.$('a.expand').attr('aria-label', _("Collapse").t());
                } else {
                    $expander.addClass('icon-chevron-right');
                    $expander.removeClass('icon-chevron-down');
                    this.$('.action-item').hide();
                    this.$('a.expand').attr('aria-label', _("Expand").t());
                }
            },
            render: function() {
                this.$el.html(this.compiledTemplate({
                    _: _,
                    splunkUtil: splunkUtil,
                    i18n: i18n,
                    alertActions: this.getAlertActions(),
                    applicationModel: this.model.application,
                    route: route
                }));
                this.visibilty();
            },
            template: '\
                <div><% if(alertActions.length) {%><a class="expand" aria-label="<%- _(\"Collapse\").t() %>" href="#"><i class="icon-chevron-down"></i></a><% } %><%- splunkUtil.sprintf(i18n.ungettext("%s Action", "%s Actions", alertActions.length), alertActions.length) %></div>\
                <% _.each(alertActions, function(alertAction) { %>\
                    <div class="action-item">\
                        <img alt="<%- _("Alert icon").t() %>" src="<%= route.alertActionIconFile(applicationModel.get("root"), applicationModel.get("locale"), alertAction.entry.acl.get("app"), {file: alertAction.entry.content.get("icon_path")}) %>">\
                        <span><%- _(alertAction.entry.content.get("label")).t() || _(alertAction.entry.get("name")).t() %></span>\
                    </div>\
                <% }); %>\
            '
        });
    }
);
