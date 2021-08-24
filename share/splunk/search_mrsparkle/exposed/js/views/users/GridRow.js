/**
 * @author cykao
 * @date 6/19/17
 *
 * Represents a row in the table. The row contains links to perform
 * operations on the given index. The user can expand the row to see more details about the index
 */
define(
    [
        'jquery',
        'underscore',
        'backbone',
        'module',
        'views/Base',
        './LockoutCell',
        'splunk.util'
    ],
    function (
        $,
        _,
        Backbone,
        module,
        BaseView,
        LockoutCellView,
        SplunkUtil
    ) {

        return BaseView.extend({
            moduleId: module.id,
            tagName: "tr",
            className: "list-item",

            events: {
                'click .view-capabilities-action': function (e) {
                    e.preventDefault();
                    window.location.href = SplunkUtil.make_url(
                        "manager/" +
                        this.model.application.get("app") +
                        "/auth/view_capabilities?users=" +
                        encodeURIComponent(this.model.entity.entry.get("name"))
                    );
                },
                'click .delete-action': function(e) {
                    this.model.controller.trigger("deleteEntity", this.model.entity);
                    e.preventDefault();
                },
                'click .clone-action': function(e) {
                    e.preventDefault();
                    this.model.controller.trigger("cloneEntity", this.model.entity);
                },
                'click .edit-action': function(e) {
                    this.model.controller.trigger("editEntity", this.model.entity);
                    e.preventDefault();
                },
                'click .unlock-action': function(e) {
                    this.model.entity.entry.content.set("locked-out", false);
                    this.model.entity.save(null, {
                        success: function (model, response) {
                            e.currentTarget.remove();
                        }
                    });
                    e.preventDefault();
                },
                'click .entity-edit-link': function(e) {
                    this.model.controller.trigger("editEntity", this.model.entity);
                    e.preventDefault();
                }
            },

            initialize: function (options) {
                BaseView.prototype.initialize.call(this, options);

                this.children.lockoutCell = new LockoutCellView({
                    model: this.model
                });
            },

            render: function () {
                var rolesText = (this.model.entity.entry.content.get('roles') || []).map(function(role) {
                    return _(role).t();
                }).join(', ');
                var html = this.compiledTemplate({
                    model: this.model.entity,
                    canDeleteSourcetype: this.model.entity.entry.links.has("remove"),
                    rolesText: rolesText,
                    canSeeActions: this.model.entity.entry.content.get("type") !== "LDAP" &&
                        this.model.entity.entry.content.get("type") !== "SAML" &&
                        this.model.entity.entry.content.get("type") !== "Scripted"
                });

                this.$el.html(html);

                this.children.lockoutCell.render().appendTo(this.$(".cell-lockout"));

                return this;
            },

            template: '\
            <td class="cell-name">\
                <a href="#" class="model-title entity-edit-link"><%- model.entry.get("name") %></a>\
            </td>\
            <td class="cell-actions">\
                <% if (canSeeActions) { %>\
                    <a href="#" class="view-capabilities-action"><%= _("View Capabilities").t() %></a>\
                    <a href="#" class="edit-action"><%= _("Edit").t() %></a>\
                    <a href="#" class="clone-action"><%= _("Clone").t() %></a>\
                    <% if(canDeleteSourcetype) { %>\
                    <a href="#" class="delete-action"><%= _("Delete").t() %></a>\
                    <% } %>\
                    <% if(model.entry.content.get("locked-out")) { %>\
                        <a href="#" class="entity-action unlock-action"><%= _("Unlock").t() %></a>\
                    <% } %>\
                <% } %>\
            </td>\
            <td class="cell-type"><%- _(model.entry.content.get("type") || "").t() %></td>\
            <td class="cell-realname"><%- model.entry.content.get("realname") %></td>\
            <td class="cell-email"><%- model.entry.content.get("email") %></td>\
            <td class="cell-tz"><%- _(model.entry.content.get("tz") || "").t() %></td>\
            <td class="cell-defaultApp"><%- _(model.entry.content.get("defaultApp") || "").t() %></td>\
            <td class="cell-defaultAppSourceRole"><%- _(model.entry.content.get("defaultAppSourceRole") || "").t() %></td>\
            <td class="cell-roles"><%- rolesText %></td>\
			<td class="cell-lockout"></div>\
			'
        }, {
            columns: [
                {
                    id: 'name',
                    title: _('Name').t()
                }, {
                    id: 'type',
                    title: _('Authentication system').t()
                }, {
                    id: 'realname',
                    title: _('Full name').t()
                }, {
                    id: 'email',
                    title: _('Email address').t()
                }, {
                    id: 'tz',
                    title: _('Time zone').t()
                }, {
                    id: 'defaultApp',
                    title: _('Default app').t()
                }, {
                    id: 'defaultAppSourceRole',
                    title: _('Default app inherited from').t()
                }, {
                    id: 'roles',
                    title: _('Roles').t()
                }, {
                    id: 'locked-out',
                    title: _('Status').t(),
                    tooltip: _('User lockout occurs per search head. See documentation for more details.').t()
                }
            ]
        });
    });
