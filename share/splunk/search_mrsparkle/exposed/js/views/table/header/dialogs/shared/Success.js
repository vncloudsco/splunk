define(
    [
        'jquery',
        'underscore',
        'module',
        'models/datasets/PolymorphicDataset',
        'views/Base',
        'views/shared/Modal',
        'views/shared/documentcontrols/dialogs/permissions_dialog/Master',
        'uri/route',
        'util/string_utils'
    ],
    function(
        $,
        _,
        module,
        PolymorphicDataset,
        Base,
        Modal,
        PermissionsDialogView,
        route,
        stringUtil
    ) {
        return Base.extend({
            moduleId: module.id,

            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);
                this.listenTo(this.model.inmem, 'sync', this.render);
            },

            events: {
                'click a.permissions-link': function(e) {
                    e.preventDefault();
                    this.showPermissionsDialog();
                }
            },

            focus: function() {
                this.$('.btn-primary').focus();
            },

            showPermissionsDialog: function() {
                this.permissionsDialog = new PermissionsDialogView({
                    model: {
                        document: this.model.inmem,
                        nameModel: this.model.inmem.entry,
                        user: this.model.user,
                        serverInfo: this.model.serverInfo,
                        application: this.model.application
                    },
                    collection: this.collection.roles,
                    onHiddenRemove: true,
                    nameLabel: this.model.inmem.getDatasetDisplayType()
                });

                this.trigger('closeModal');
                this.permissionsDialog.render().appendTo($('body'));
                this.permissionsDialog.show();
            },

            render: function() {
                var canChangePerms = this.model.inmem.entry.acl.get('can_change_perms'),
                    routeToDatasets = route.datasets(
                        this.model.application.get('root'),
                        this.model.application.get('locale'),
                        this.model.application.get('app')
                    ),
                    routeToExplore = route.dataset(
                        this.model.application.get('root'),
                        this.model.application.get('locale'),
                        this.model.application.get('app'),
                        { data: this.model.inmem.getRoutingData() }
                    );

                this.$el.html(Modal.TEMPLATE);
                this.$(Modal.HEADER_TITLE_SELECTOR).html(this.options.title);
                this.$(Modal.BODY_SELECTOR).html(this.compiledTemplate({
                    _: _,
                    model: this.model.inmem,
                    canChangePerms: canChangePerms
                }));

                if (canChangePerms) {
                    this.$('span.save-table-success-message').text(_('You may now explore your table, change additional settings, continue editing it, or return to the listings page.').t());
                } else {
                    this.$('span.save-table-success-message').text(_('You may now explore your table, continue editing it, or return to the listings page.').t());
                    this.$('p.additional-settings').remove();
                }

                this.$(Modal.FOOTER_SELECTOR).append('<a href="' + routeToDatasets + '" class="btn done pull-left">' + _('Done').t() + '</a>');
                this.$(Modal.FOOTER_SELECTOR).append('<a href="' + routeToExplore + '" class="btn explore-dataset btn-primary pull-right">' + _('Explore Dataset').t() + '</a>');
                this.$(Modal.FOOTER_SELECTOR).append('<a href="#" class="btn continue-editing pull-right" data-dismiss="modal">' + _('Continue Editing').t() + '</a>');

                return this;
            },

            template: '\
                <p>\
                    <span class="save-table-success-message"></span>\
                </p>\
                <p class="additional-settings">\
                    <%- _("Additional Settings:").t() %>\
                    <ul>\
                        <% if (canChangePerms) { %>\
                            <li><a href="#" class="permissions-link"><%- _("Permissions").t() %></a></li>\
                        <% } %>\
                    </ul>\
                </p>\
            '
        });
    }
);

