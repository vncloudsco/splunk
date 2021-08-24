define(
    [
        'jquery',
        'underscore',
        'views/Base',
        'module',
        'uri/route',
        'util/general_utils',
        'splunk.util',
        'bootstrap.tooltip'
    ],
    function(
        $,
        _,
        BaseView,
        module,
        route,
        GeneralUtils,
        splunkUtil,
        _bootstrapTooltip
    ) {
    return BaseView.extend({
        moduleId: module.id,
        tagName: 'tr',
        className: function() {
            return 'active-action ' + (this.isExpandable() ? 'expandable' : 'disabled');
        },
        attributes: function() {
            return {
                'data-name': this.model.selectedAlertAction.entry.get('name')
            };
        },
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);

            this.listenTo(this.model.selectedAlertAction, 'remove', this.remove);
        },
        events: {
            'click a.remove-action': function(e) {
                var name = this.model.selectedAlertAction.entry.get('name');
                if (name === 'list') {
                    this.model.document.entry.content.set('alert.track', false);
                } else {
                    this.model.document.entry.content.set('action.' + name, false);
                }
                this.collection.unSelectedAlertActions.add(
                    this.collection.selectedAlertActions.remove(this.model.selectedAlertAction));
                this.model.selectedAlertAction.set('isExpanded', false);
                e.preventDefault();
            },
            'click td.action-title': function(e) {
                if (this.isExpandable()) {
                    this.model.document.trigger('toggleRow', $(e.currentTarget.parentElement), true);
                }
                e.preventDefault();
            },
            'expand': function(e) {
                this.model.selectedAlertAction.set('isExpanded', true);
            },
            'collapse': function() {
                this.model.selectedAlertAction.set('isExpanded', false);
            }
        },
        isExpandable: function() {
            var isCustomAction = GeneralUtils.normalizeBoolean(this.model.selectedAlertAction.entry.content.get('is_custom'));
            return !isCustomAction || this.model.alertActionUI != null;
        },
        removeTooltip: function() {
            this.$('.expands').tooltip('destroy');
        },
        remove: function(){
            this.removeTooltip();
            return BaseView.prototype.remove.apply(this, arguments);
        },
        render: function() {
            var actionName = this.model.selectedAlertAction.entry.get('name');
            var isExpandable = this.isExpandable();
            var actionLabel = this.model.selectedAlertAction.entry.content.get('label') || actionName;
            this.removeTooltip();
            this.$el.html(this.compiledTemplate({
                _: _,
                actionName: actionName,
                actionLabel: _(actionLabel).t(),
                isExpanded: this.model.selectedAlertAction.get('isExpanded') && isExpandable,
                isExpandable: isExpandable,
                iconPath: route.alertActionIconFile(this.model.application.get('root'),
                    this.model.application.get('locale'),
                    this.model.selectedAlertAction.entry.acl.get('app'),
                    {file: this.model.selectedAlertAction.entry.content.get('icon_path')}),
                collapseAriaLabel: splunkUtil.sprintf(_('Collapse row to exit editing of %s action').t(), actionLabel),
                expandAriaLabel: splunkUtil.sprintf(_('Expand row to edit %s action').t(), actionLabel),
                removeAriaLabel: splunkUtil.sprintf(_('Remove %s action').t(), actionLabel)
            }));

            if (!isExpandable) {
                this.$('.expands').tooltip({
                    animation: false,
                    title: _('This alert action does not require any user configuration.').t(),
                    container: 'body'
                });
            }
            return this;
        },
        template: '\
        <td class="expands<%- isExpandable ? \'\' : \' disabled\' %>" <% if (isExpanded) { %> rowspan="2" <% } %> <% if (isExpandable) { %> tabindex="0" <% } %>>\
            <a aria-label="<%- isExpanded? collapseAriaLabel: expandAriaLabel %>">\
                <i class="<%- isExpanded ? \'icon-triangle-down-small\' : \'icon-triangle-right-small\' %>">\
                </i>\
            </a>\
        </td>\
        <td class="action-title"><img src="<%= iconPath %>"><%- actionLabel %></td>\
        <td class="action-actions">\
            <a class="remove-action pull-right" href="#"\
                aria-label="<%- removeAriaLabel %>">\
                <%- _("Remove").t() %>\
            </a>\
        </td>\
    '
    });
});
