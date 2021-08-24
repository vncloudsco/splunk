define([
        'jquery',
        'underscore',
        'backbone',
        'module',
        'models/managementconsole/DmcBase',
        'models/managementconsole/App',
        'views/shared/basemanager/GridRow'
    ],
    function (
        $,
        _,
        Backbone,
        module,
        DmcBaseModel,
        AppModel,
        BaseManagerGridRow
    ) {
        return BaseManagerGridRow.extend({
            moduleId: module.id,
            tagName: "tr",
            className: "list-item",

            initialize: function() {
                BaseManagerGridRow.prototype.initialize.apply(this, arguments);

                this.model = this.model || {};
                this.appsLocalMap = this.options.appsLocalMap;
                this.model.appLocal = this.appsLocalMap[this.model.entity.entry.get('name')];

                this.syncAppsLocal = this.options.syncAppsLocal.bind(this);

                if (!_.isUndefined(this.model.appLocal)) {
                    this.listenTo(this.model.appLocal, 'sync', this.render);
                }

                this.listenTo(this.model.deployTask.entry.content, 'change:state', this.handleDeployTaskChange);
                this.listenTo(this.collection.appsLocal, 'syncAppsLocal', this.syncAppsLocal);
                this.collection.entities.on('sync', this.render);
            },

            events: $.extend({}, BaseManagerGridRow.prototype.events, {
                'click .toggle-update-checking': function(e) {
                    e.preventDefault();

                    // delegate event to the page controller
                    this.model.controller.trigger('toggleUpdateChecking', this.model.entity);
                },
                'click .toggle-visibility': function(e) {
                    e.preventDefault();

                    // delegate event to the page controller
                    this.model.controller.trigger('toggleVisibility', this.model.entity);
                },
                'click .toggle-status': function(e) {
                    e.preventDefault();

                    // delegate event to the page controller
                    this.model.controller.trigger('toggleStatus', this.model.entity);
                },
                'click .edit-permissions-link': function(e) {
                    e.preventDefault();

                    this.model.controller.trigger('editPermissions', this.model.entity);
                },
                'click .update-available-link': function(e) {
                    e.preventDefault();

                    this.model.controller.trigger('updateApp', this.model.entity);
                }
            }),

            handleDeployTaskChange: function() {
                if (this.model.deployTask.inProgress()) {
                    this.$('.toggle-status').addClass('disabled-action');
                } else {
                    this.$('.toggle-status').removeClass('disabled-action');
                }
            },

            // This overrides the method in the base class
            prepareTemplate: function() {
                var rowIsEnabled = !_.isUndefined(this.model.appLocal),
                    isExternal = this.model.entity.isExternal(),
                    isIndexerOnly = this.model.entity.isIndexerOnly(),
                    isPrivate = this.model.entity.isPrivate(),
                    isShCluster = this.model.ShClusterConfig.isEnabled(),
                    appTemplate = this.model.entity.getTemplate(),
                    canEdit = this.model.entity.canEdit(),
                    checkForUpdates = !!this.model.appLocal && this.model.appLocal.getCheckForUpdates(),
                    template = BaseManagerGridRow.prototype.prepareTemplate.apply(this, arguments),
                    nameHTML = _.template(this.nameTemplate)({
                        rowIsEnabled: rowIsEnabled,
                        name: this.model.entity.entry.content.get('@label') || this.model.entity.entry.get('name'),
                        canLaunch: this.model.appLocal && this.model.appLocal.canLaunch(),
                        launchUrl: this.model.entity.getLaunchUrl()
                    }),
                    actionsHTML = _.template(this.actionsTemplate)({
                        rowIsEnabled: rowIsEnabled,
                        isExternal: isExternal
                    }),
                    updateCheckingHTML = _.template(this.updateCheckingTemplate)({
                        rowIsEnabled: rowIsEnabled,
                        isPrivate: isPrivate,
                        appTemplate: appTemplate,
                        checkForUpdates: checkForUpdates
                    }),
                    visibilityHTML = _.template(this.visibilityTemplate)({
                        rowIsEnabled: rowIsEnabled,
                        isIndexerOnly: isIndexerOnly,
                        isShCluster: isShCluster,
                        isVisible: this.model.appLocal && this.model.appLocal.getVisibility()
                    }),
                    permissionsHTML = _.template(this.permissionsTemplate)({
                        rowIsEnabled: rowIsEnabled,
                        isIndexerOnly: isIndexerOnly,
                        sharingName: this.model.appLocal && this.model.appLocal.getSharingName()
                    }),
                    statusHTML = _.template(this.statusTemplate)({
                        rowIsEnabled: rowIsEnabled,
                        isExternal: isExternal,
                        isIndexerOnly: isIndexerOnly,
                        canEdit: canEdit,
                        entityAllowsDisable: this.model.entity && !!this.model.entity.getDisableLink(),
                        entityAllowsEnable: this.model.entity && !!this.model.entity.getEnableLink(),
                        appAllowsDisable: this.model.appLocal && this.model.appLocal.appAllowsDisable(),
                        appAllowsEnable: this.model.appLocal && this.model.appLocal.appAllowsEnable(),
                        isEntityDisabled: this.model.entity && this.model.entity.isDisabled(),
                        isDisabled: this.model.appLocal && this.model.appLocal.isDisabled()
                    }),
                    dependenciesHTML = _.template(this.dependenciesTemplate)({
                        rowIsEnabled: rowIsEnabled,
                        dependencies: this.model.entity.getPrettyPackageDependenciesString()
                    }),
                    splunkBaseHTML = _.template(this.splunkBaseTemplate)({
                        rowIsEnabled: rowIsEnabled,
                        isPrivate: isPrivate,
                        isExternal: isExternal,
                        appTemplate: appTemplate,
                        splunkBaseUrl: this.model.appLocal && this.model.appLocal.entry.content.get('details')
                    });
                    // if appLocal does not exist, then app does not exist locally
                    // and we assume that deploy for this app is currently in progress.
                    // therefore, add css styling class 'disabled' for the row
                    if (!rowIsEnabled && !isIndexerOnly) {
                        this.$el.addClass('disabled');
                    } else {
                        if (this.$el.hasClass('disabled')) {
                            this.$el.removeClass('disabled');
                        }
                    }

                    return $.extend(true, template, {
                        name: this.model.entity.entry.content.get('@label') || this.model.entity.entry.get('name'),
                        folderName: this.model.entity.entry.get('name'),
                        version: this.model.entity.getVersion(),
                        hasUpdate: this.model.entity.hasUpdate(),
                        isIndexerOnly: isIndexerOnly,
                        canEdit: canEdit,
                        checkForUpdates: checkForUpdates,
                        nameHTML: nameHTML,
                        actionsHTML: actionsHTML,
                        updateCheckingHTML: updateCheckingHTML,
                        visibilityHTML: visibilityHTML,
                        permissionsHTML: permissionsHTML,
                        statusHTML: statusHTML,
                        dependenciesHTML: dependenciesHTML,
                        splunkBaseHTML: splunkBaseHTML
                    });
                },

                render: function() {
                    var isExpanded = this.$el.next('tr.more-info').is(':visible');
                    BaseManagerGridRow.prototype.render.apply(this, arguments);

                    // if row was previously expanded -> remove the expanded class
                    // and toggle row expansion. This is required because re-rendering
                    // the row shrinks it.
                    if (isExpanded) {
                        this.$el.removeClass('expanded');
                        this.options.tableRowToggle.toggleRow(this.$el, false);
                    }

                    // need to disable deploy actions if deploy is already
                    // in progress
                    this.handleDeployTaskChange();

                    return this;
                },

                nameTemplate: '\
                <% if (rowIsEnabled && canLaunch) { %> \
                    <a href="<%- launchUrl %>" class="launch-app"><%- name %></a> \
                <% } else { %> \
                    <%- name %> \
                <% } %> \
                ',
                actionsTemplate: '\
                <% if (rowIsEnabled && !isExternal) { %> \
                    <div class="action-cell-placeholder"></div>\
                <% } %> \
                ',
                updateCheckingTemplate: '\
                <% if (rowIsEnabled && !isPrivate && !appTemplate) { %> \
                    <% if (checkForUpdates) { %> \
                        <%- _("Yes").t() %> <span class="splPipe">|</span><a href="#" class="toggle-update-checking"><%- _("No").t() %></a> \
                    <% } else { %> \
                            <a href="#" class="toggle-update-checking"><%- _("Yes").t() %></a> <span class="splPipe">|</span><%- _("No").t() %> \
                    <% } %> \
                <% } else { %> \
                    <%- _("N/A").t() %> \
                <% } %> \
                ',
                visibilityTemplate: '\
                <% if (isIndexerOnly) { %> \
                    <%- _("Hidden").t() %> \
                <% } else if (rowIsEnabled) { %> \
                    <% if (!isShCluster) { %> \
                        <% if (isVisible) { %> \
                            <%- _("Visible").t() %> <span class="splPipe">|</span><a href="#" class="toggle-visibility"><%- _("Hide").t() %></a> \
                        <% } else { %> \
                            <a href="#" class="toggle-visibility"><%- _("Show").t() %></a> <span class="splPipe">|</span><%- _("Hidden").t() %> \
                        <% } %> \
                    <% } else { %> \
                        <% if (isVisible) { %> \
                            <%- _("Yes").t() %> \
                        <% } else { %> \
                            <%- _("No").t() %> \
                        <% } %> \
                    <% } %> \
                <% } else { %> \
                    <%- _("N/A").t() %> \
                <% } %> \
                ',
                permissionsTemplate: '\
                <% if (isIndexerOnly || !rowIsEnabled) { %> \
                    <%- _("N/A").t() %> \
                <% } else { %> \
                    <%- sharingName %> <span class="splPipe">|</span><a href="#" class="edit-permissions-link"><%- _("Permissions").t() %></a> \
                <% } %> \
                ',
                statusTemplate: '\
                <% if (isExternal && isIndexerOnly) { %> \
                    <%- _("N/A").t() %> \
                <% } else if (rowIsEnabled) { %> \
                    <% if (((isDisabled && appAllowsEnable) || (isEntityDisabled && entityAllowsEnable)) && (canEdit || isExternal)) { %> \
                        <a href="#" class="toggle-status"><%- _("Enable").t() %></a> <span class="splPipe">|</span><%- _("Disabled").t() %> \
                    <% } else if (((!isDisabled && appAllowsDisable) || (!isEntityDisabled && entityAllowsDisable)) && (canEdit || isExternal)) { %> \
                        <%- _("Enabled").t() %> <span class="splPipe">|</span><a href="#" class="toggle-status"><%- _("Disable").t() %></a>\
                    <% } else { %> \
                        <%- (isDisabled ? _("Disabled").t() : _("Enabled").t()) %> \
                    <% } %> \
                <% } else { %> \
                    <%- _("Deploying").t() %> \
                <% } %> \
                ',
                dependenciesTemplate: '\
                <% if (dependencies) { %> \
                    <%- dependencies %> \
                <% } %> \
                ',
                splunkBaseTemplate: '\
                <% if (isPrivate) { %> \
                    <%- _("Uploaded").t() %> \
                <% } else if (appTemplate) {%> \
                    <%- _("Template").t() %> \
                <% } else if (splunkBaseUrl) { %> \
                    <a href="<%- splunkBaseUrl %>" target=_blank ><%- _("Splunkbase").t() %> <i class="icon-external"></i></a> \
                <% } else {%> \
                    <%- _("Splunk").t() %> \
                <% } %> \
                ',
                // This overrides the method in the base class
                template: '\
                <td class="expands">\
                    <a href="#"><i class="icon-triangle-right-small"></i></a>\
                </td>\
                <td class="cell-name app-name" title="<%- name %>">\
                    <%= nameHTML %> \
                </td>\
                <td class="cell-actions">\
                    <%= actionsHTML %> \
                </td>\
                <td class="cell-folder-name" title="<%- folderName %>">\
                    <%- folderName %>\
                </td>\
                <td class="cell-version">\
                    <%- version %>\
                    <% if (checkForUpdates && hasUpdate && canEdit) { %> \
                        &nbsp;(<a href="#" class="update-available-link"><%- _("Update Available").t() %></a>)\
                    <% } %> \
                </td>\
                <td class="cell-update-checking" >\
                    <%= updateCheckingHTML %> \
                </td> \
                <td class="cell-visibility"> \
                    <%= visibilityHTML %> \
                </td> \
                <td class="cell-sharing"> \
                    <%= permissionsHTML %> \
                </td> \
                <td class="cell-status"> \
                    <%= statusHTML %> \
                </td> \
                <td class="cell-dependencies">\
                    <%= dependenciesHTML %>\
                </td> \
                <td class="cell-appOrigin">\
                    <%= splunkBaseHTML %>\
                </td>'
            }, {
            columns: [
                {
                    id: '@label',
                    title: _('Name').t(),
                    noSort: true
                },
                {
                    id: 'name',
                    title: _('Folder Name').t(),
                    noSort: false
                },
                {
                    id: '@version',
                    title: _('Version').t(),
                    noSort: true
                },
                {
                    id: 'checkForUpdates',
                    title: _('Check for Updates').t(),
                    noSort: true
                },
                {
                    id: 'visible',
                    title: _('Visibility').t(),
                    noSort: true
                },
                {
                    id: 'sharing',
                    title: _('Sharing').t(),
                    noSort: true
                },
                {
                    id: 'status',
                    title: _('Status').t(),
                    noSort: true
                },
                {
                    id: '@dependencies',
                    title: _('Dependencies').t(),
                    noSort: true
                },
                {
                    id: 'appOrigin',
                    title: _('App Origin').t(),
                    noSort: true
                }
            ]
        });
    });
