define([
        'jquery',
        'underscore',
        'module',
        'views/shared/basemanager/ActionCell',
        './ActionCell.pcss'
    ],
    function (
        $,
        _,
        module,
        ActionCell
    ) {
        return ActionCell.extend({

            initialize: function() {
                ActionCell.prototype.initialize.apply(this, arguments);
                this.listenTo(this.model.deployTask.entry.content, 'change:state', this.handleUninstallState);
            },

            handleUninstallState: function() {
                var name = this.model.deployTask.entry.get('name');
                if (name) {
                    var taskState = this.model.deployTask.entry.content.get('state');
                    if (taskState === 'new' || taskState === 'running') {
                        this.uninstallDisabled = true;
                        this.$el.find('a.uninstall-app').addClass('disabled-action');
                        return;
                    }
                }

                this.uninstallDisabled = false;
                this.$el.find('a.uninstall-app').removeClass('disabled-action');
            },

            events: {
                'click a.uninstall-app': function(e) {
                    e.preventDefault();
                    this.model.controller.trigger("uninstallApp", this.model.entity);
                }
            },

            // This overrides the method in the base class
            render: function() {
                var html = this.compiledTemplate({
                    isExternal: this.model.entity.isExternal(),
                    canDelete: this.model.entity.canDelete(),
                    downloadLink: this.model.entity.getExportUrl(),
                    canSetup: this.model.appLocal && this.model.appLocal.canSetup(),
                    setupUrl: this.model.entity.getSetupUrl(),
                    appTemplate: this.model.entity.getTemplate()
                });

                this.$el.html(html);
                // Makes sure the state of uninstall is correct
                this.handleUninstallState();
                this.delegateEvents();
                return this;
            },

            template: '\
            <% if (canSetup) { %>\
                <a href="<%- setupUrl %>" class="setup-app"><%- _("Set up").t() %></a>\
            <% } if (!isExternal) { %>\
                <% if (canDelete) { %>\
                    <a href="#" class="uninstall-app"><%- _("Uninstall").t() %></a>\
                <% } if (!appTemplate) { %>\
                    <a href="<%- downloadLink %>" class="entity-action export-action"><%- _("Download").t() %></a>\
                <% } %>\
            <% } %>\
             '
        });
    }
);
