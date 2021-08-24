define(
    [
        'underscore',
        'module',
        'views/Base',
        'util/splunkd_utils',
        'splunk.util'
    ],
    function(_, module, Base, splunkDUtils, splunkUtil) {
        return Base.extend({
            moduleId: module.id,
            tagName: 'span',
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);
                this.activate();
            },
            activate: function(options) {
                if (this.active) {
                    return Base.prototype.activate.call(this, options);
                }
                Base.prototype.activate.call(this, options);
                if (this.el.innerHTML) {
                    this.render();
                }
                return this;
            },
            startListening: function() {
                this.listenTo(this.model.report.entry.acl, 'change:sharing change:owner', this.debouncedRender);
            },
            render: function() {
                var sharing = this.model.report.entry.acl.get("sharing"),
                    owner = this.model.report.entry.acl.get("owner"),
                    canUseApps = this.model.user.canUseApps();

                if (sharing == 'app' && !canUseApps) {
                    sharing = 'system';
                }

                var permissionString = splunkDUtils.getPermissionLabel(sharing, owner);

                this.$el.html(this.compiledTemplate({
                    permissionString: permissionString
                }));
                return this;
            },
            template: '\
               <%- permissionString %>\
            '
        });
    }
);
