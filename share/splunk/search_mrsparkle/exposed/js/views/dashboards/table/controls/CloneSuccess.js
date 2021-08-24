define(['jquery', 'underscore', 'module', 'views/shared/Modal','uri/route','views/shared/documentcontrols/dialogs/permissions_dialog/Master','views/dashboards/table/controls/SchedulePDF','models/services/ScheduledView'],
        function($, _, module, Modal, route, PermissionsDialog, SchedulePDF, ScheduledViewModel){

    return Modal.extend({
        moduleId: module.id,
        events: $.extend({}, Modal.prototype.events, {
            'click .edit-perms': function(e) {
                e.preventDefault();
                var model = this.model, roles = this.collection.roles;
                _.defer(function(){
                    var permissionsDialog = new PermissionsDialog({
                        model: {
                            document: model.dashboard,
                            nameModel: model.dashboard.entry.content,
                            user: model.user,
                            serverInfo: model.serverInfo
                        },
                        collection: roles,
                        nameLabel:  "Dashboard",
                        nameKey: 'label',
                        onHiddenRemove: true
                    });

                    $("body").append(permissionsDialog.render().el);
                    permissionsDialog.show();
                });

                this.hide();
                this.remove();
            },
            'click .schedule-pdf': function(e) {
                e.preventDefault();
                var model = this.model;
                var createDialog = function() {
                    var schedulePDF = new SchedulePDF({
                        model: {
                            scheduledView: model.scheduledView,
                            dashboard: model.dashboard,
                            application: model.application,
                            appLocal: model.appLocal
                        },
                        onHiddenRemove: true
                    });
                    $("body").append(schedulePDF.render().el);
                    schedulePDF.show();
                };
                if(!this.model.scheduledView) {
                    var scheduledView = model.scheduledView = new ScheduledViewModel(),
                        dfd = scheduledView.findByName(this.model.dashboard.entry.get('name'), this.model.application.get('app'), this.model.application.get('owner'));
                    dfd.done(createDialog);
                } else {
                    _.defer(createDialog);
                }
                this.hide();
                this.remove();
            }
        }),
        focus: function() {
            this.$el.find('.btn-primary').focus();
        },
        render: function() {
            this.$el.html(Modal.TEMPLATE);
            this.$(Modal.HEADER_TITLE_SELECTOR).html(_("Dashboard has been cloned.").t());
            this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);

            var link = route.page(this.model.application.get("root"), this.model.application.get("locale"),
                    this.model.dashboard.entry.acl.get("app"), this.model.dashboard.entry.get('name'));
            var canChangePerms = this.model.dashboard.entry.acl.get('can_change_perms');
            var canSchedule = this.model.user.canSchedulePDF() && this.model.dashboard.isDashboard();
            this.$(Modal.BODY_FORM_SELECTOR).append(_.template(this.messageTemplate, {
                dashboardLink: link,
                canChangePerms: canChangePerms,
                canSchedule: canSchedule
            }));

            var editLink;
            var editButtonText;
            if (!this.model.dashboard.isHTML()) {
                editLink = link + '/edit';
                editButtonText = _('Edit Panels').t();
            } else {
                editLink = route.managerEdit(
                    this.model.application.get('root'),
                    this.model.application.get('locale'),
                    this.model.dashboard.entry.acl.get('app'),
                    ['data', 'ui', 'views', this.model.dashboard.entry.get('name')],
                    this.model.dashboard.id,
                    { data: { ns: this.model.dashboard.entry.acl.get('app'),
                        redirect_override: link }
                    }
                );
                editButtonText = _('Edit HTML').t();
            }

            this.$(Modal.FOOTER_SELECTOR).append(_.template(this.buttonTemplate, {
                dashboardLink: link,
                editLink: editLink,
                editButtonText: editButtonText,
                _: _
            }));

            this.$(Modal.FOOTER_SELECTOR).append('');
            return this;
        },
        buttonTemplate: '<a href="<%= editLink %>" class="btn edit-panels"><%- editButtonText  %></a>' +
                        '<a href="<%= dashboardLink %>" class="btn btn-primary modal-btn-primary"><%- _("View").t() %></a>',
        messageTemplate: '<p><%- _("You may now view your dashboard, change additional settings, or edit the panels.").t() %></p>' +
                        '<p><% if(canChangePerms || canSchedule){ %>' +
                                '<%- _("Additional Settings").t() %>:' +
                                '<ul>' +
                                    '<% if(canChangePerms) { %><li><a href="#" class="edit-perms"><%- _("Permissions").t() %><% } %></a></li>' +
                                    '<% if(canSchedule) { %><li><a href="#" class="schedule-pdf"><%- _("Schedule PDF Delivery").t() %><% } %></a></li>' +
                                '</ul>' +
                            '<% } %>' +
                        '</p>'
    });

});
