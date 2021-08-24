define(
    [
        'module',
        'jquery',
        'underscore',
        '../Base',
        'views/shared/PopTart',
        'util/pdf_utils',
        'controllers/dashboard/helpers/DashboardV2Helper',
        './ExportMenu',
        './EditMenu.pcssm'
    ],
    function (module,
        $,
        _,
        BaseDashboardView,
        PopTartView,
        PDFUtils,
        DashboardV2Helper,
        ExportMenu,
        css) {

        var defaults = {
            button: true,
            showOpenActions: true,
            deleteRedirect: false
        };

        var OtherMenu = PopTartView.extend({
            className: 'dropdown-menu other-menu',
            initialize: function () {
                PopTartView.prototype.initialize.apply(this, arguments);
                _.defaults(this.options, defaults);
                this._menuModel = {
                    allowEditPermission: this.model.view.entry.acl.get('can_change_perms') && this.model.view.entry.acl.canWrite(),
                    allowConvertToHTML: this.model.view.isSimpleXML() && !this.model.serverInfo.isLite() && this.model.view.entry.acl.canWrite() && this.model.user.canEditViewHtml(),
                    allowClone: !this.model.view.isHTML() || this.model.user.canEditViewHtml(),
                    allowMakeHome: !this.model.serverInfo.isLite() && this.model.view.isSimpleXML() && !(this.model.userPref.entry.content.get('display.page.home.dashboardId') === this.model.view.get('id')),
                    allowDelete: this.model.view.entry.acl.canWrite() && this.model.view.entry.acl.get('removable'),
                    allowConvertToV2: false,
                };

                if (DashboardV2Helper.isV2Supported(this.collection.apps)) {
                    DashboardV2Helper.convertV1ToV2({
                        simplexml: this.model.view.getXMLContent(),
                    }).done(function (data) {
                        if (data.canFullyConvert) {
                            this._menuModel.allowConvertToV2 = true;
                            this.render();
                        }
                    }.bind(this)).fail(function () {
                        // do nothing, because open in v2 is an optional feature
                    }.bind(this));
                }
            },
            events: {
                'click a.edit-perms': function (e) {
                    e.preventDefault();
                    this._triggerControllerEvent('action:edit-permission');
                },
                'click a.convert-to-html': function (e) {
                    e.preventDefault();
                    this._triggerControllerEvent('action:convert-html');
                },
                'click a.clone': function (e) {
                    e.preventDefault();
                    this._triggerControllerEvent('action:clone');
                },
                'click a.make-home': function (e) {
                    e.preventDefault();
                    this._triggerControllerEvent('action:make-home');
                },
                'click a.delete': function (e) {
                    e.preventDefault();
                    this._triggerControllerEvent('action:delete');
                },
                'click a.convert-to-v2': function (e) {
                    e.preventDefault();
                    this._triggerControllerEvent('action:open-in-v2');
                },
            },
            _triggerControllerEvent: function () {
                this.model.controller.trigger.apply(this.model.controller, arguments);
                this.hide();
            },
            render: function () {
                this.$el.html(PopTartView.prototype.template_menu);
                this.$el.append(this.compiledTemplate(this._menuModel));
                return this;
            },
            isEmpty: function () {
                return !_.some(_.values(this._menuModel));
            },
            template: '\
                    <ul class="first-group">\
                        <% if(allowEditPermission) { %>\
                        <li><a href="#" class="edit-perms"><%- _("Edit Permissions").t() %></a></li>\
                        <% } %>\
                        <% if (allowConvertToHTML) { %>\
                        <li><a href="#" class="convert-to-html"><%- _("Convert to HTML").t() %></a></li>\
                        <% } %>\
                    </ul>\
                    <ul class="second-group">\
                        <% if (allowClone) { %>\
                        <li><a href="#" class="clone"><%- _("Clone").t() %></a></li>\
                        <% } %>\
                        <% if (allowMakeHome) { %>\
                        <li><a href="#" class="make-home"><%- _("Set as Home Dashboard").t() %></a></li>\
                        <% } %>\
                        <% if(allowDelete) { %>\
                        <li><a href="#" class="delete"><%- _("Delete").t() %></a></li>\
                        <% } %>\
                        <% if(allowConvertToV2) { %>\
                        <li><a href="#" class="convert-to-v2"><%- _("Open in Dashboard App (beta)").t() %></a></li>\
                        <% } %>\
                    </ul>\
            '
        });

        return BaseDashboardView.extend({
            moduleId: module.id,
            viewOptions: {
                register: false
            },
            className: 'dashboard-menu pull-right',
            initialize: function () {
                BaseDashboardView.prototype.initialize.apply(this, arguments);
            },
            events: {
                'click a.edit-btn': function (e) {
                    e.preventDefault();
                    this.model.controller.trigger('mode:edit');
                },
                'click a.edit-other': function (e) {
                    e.preventDefault();
                    this.children.otherMenu = new OtherMenu({
                        model: this.model,
                        collection: this.collection,
                    });
                    this.children.otherMenu.once('hide', this.children.otherMenu.remove);
                    $('body').append(this.children.otherMenu.render().$el);
                    var $btn = $(e.currentTarget);
                    $btn.addClass('active');
                    this.children.otherMenu.show($btn);
                    this.children.otherMenu.once('hide', function () {
                        $btn.removeClass('active');
                    });

                }
            },
            render: function () {
                var menuModel = {
                    canWrite: this.model.view.entry.acl.canWrite()
                };
                this.$el.html(this.compiledTemplate(menuModel));

                if (this.model.page == null || !this.model.page.get('hideExport')) {
                    if (this.children.exportMenu) {
                        this.children.exportMenu.remove();
                        this.children.exportMenu = null;
                    }
                    this.children.exportMenu = new ExportMenu({
                        model: this.model,
                        collection: {
                            apps: this.collection.appLocalsUnfilteredAll
                        }
                    });
                    this.children.exportMenu.render().$el.appendTo(this.$('.dashboard-export-container'));
                }
                return this;
            },

            template: '\
            <span class="dashboard-view-controls">\
                <% if(canWrite) { %>\
                    <a class="btn edit-btn" href="#"><%- _("Edit").t() %></a>\
                <% } %>\
                <div class="dashboard-export-container ' + css.exportButtonContainer + '"></div>\
                <a aria-label="<%- _("more").t() %>" class="btn edit-other" href="#">...</a>\
            </span>\
        '
        });
    }
);
