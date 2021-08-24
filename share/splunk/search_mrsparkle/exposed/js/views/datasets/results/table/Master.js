define(
    [
        'module',
        'jquery',
        'underscore',
        'backbone',
        'views/Base',
        'views/shared/TableHead',
        'views/shared/delegates/TableRowToggle',
        'views/datasets/results/table/TableRow',
        'views/datasets/results/table/MoreInfo',
        'views/shared/delegates/TableDock',
        'splunk.util'
    ],
    function(
        module,
        $,
        _,
        Backbone,
        BaseView,
        TableHeadView,
        TableRowToggleView,
        TableRow,
        MoreInfo,
        TableDock,
        splunkUtils
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'table-padded',

            /**
             * @param {Object} options {
             *      model: {
             *          state: <Backbone.Model>
             *          application: <models.Application>,
             *          uiPrefs: <models.services.admin.UIPrefs>
             *          userPref: <models.services.data.UserPref>
             *          user: <models.services.authentication.User>
             *          appLocal: <models.services.AppLocal>
             *          serverInfo: <models.services.server.ServerInfo>
             *          rawSearch: <Backbone.Model>
             *      }
             *      collection: {
             *          datasets: <collections.Datasets>,
             *          roles: <collections.services.authorization.Roles>,
             *          apps: <collections.services.AppLocals>
             *      }
             * }
             */
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.children.tableRowToggle = new TableRowToggleView({ el: this.el, collapseOthers: true });

                this.tableHeaders = [];
                this.tableHeaders.push({ label: _('i').t(), ariaLabel: _('More Info').t(), className: 'col-info', html: '<i class="icon-info"></i>' });
                this.tableHeaders.push({ label: _('Title').t(), sortKey: 'displayName' });
                this.tableHeaders.push({ label: _('Dataset Type').t(), sortKey: 'dataset.type,eai:type,displayName', className: 'col-type' });
                this.tableHeaders.push({ label: _('Accelerated').t(), ariaLabel: _('Acceleration').t(), sortKey: 'accelerated,displayName', className: 'col-accelerate', html:'<i class="icon-lightning"></i>'});
                this.tableHeaders.push({ label: _('Actions').t(), className: 'col-actions' });
                this.tableHeaders.push({ label: _('Owner').t(), sortKey: 'eai:acl.owner,displayName', className: 'col-owner' });
                if (this.model.user.canUseApps()) {
                    this.tableHeaders.push({ label: _('App').t(), sortKey: 'eai:acl.app,displayName', className: 'col-app' });
                }
                this.tableHeaders.push({ label: _('Sharing').t(), sortKey: 'eai:acl.sharing,displayName', className: 'col-sharing' });

                this.children.head = new TableHeadView({
                    model: this.model.state,
                    columns: this.tableHeaders
                });
                this.children.rows = this.rowsFromCollection();

                this.children.tableDock = new TableDock({ el: this.el, offset: 42, dockScrollBar: false, defaultLayout: 'fixed', flexWidthColumn: 1 });
            },

            startListening: function() {
                this.listenTo(this.collection.datasets, 'reset', this.renderRows);
            },

            rowsFromCollection: function() {
                var currentApp = this.model.application.get('app'),
                    alternateApp = currentApp !== 'system' ? currentApp : 'search',
                    searchApp = _.find(this.collection.apps.models, function(app) {
                        return app.entry.get('name') === 'search';
                    }),
                    collection,
                    clonedModels;

                if (alternateApp === 'search' && searchApp && splunkUtils.normalizeBoolean(searchApp.entry.content.get("disabled"))) {
                    this.collection.apps.sortWithString(this.model.userPref.entry.content.get('appOrder'));
                    alternateApp = this.collection.apps.models[0].entry.get('name');
                }

                return _.flatten(
                    this.collection.datasets.map(function(model, i) {
                        return [
                            new TableRow({
                                model: {
                                    dataset: model,
                                    application: this.model.application,
                                    state: this.model.state,
                                    user: this.model.user,
                                    appLocal: this.model.appLocal,
                                    serverInfo: this.model.serverInfo
                                },
                                collection: {
                                    roles: this.collection.roles,
                                    apps: this.collection.apps
                                },
                                index: i,
                                alternateApp: alternateApp
                            }),
                            new MoreInfo({
                                model: {
                                    dataset: model,
                                    application: this.model.application,
                                    user: this.model.user,
                                    appLocal: this.model.appLocal,
                                    serverInfo: this.model.serverInfo
                                },
                                collection: {
                                    roles: this.collection.roles,
                                    apps: this.collection.apps
                                },
                                index: i,
                                alternateApp: alternateApp,
                                colSpan: this.tableHeaders.length - 1
                            })
                        ];
                    }, this)
                );
            },

            _render: function() {
                _(this.children.rows).each(function(row){
                    row.activate({deep:true}).render().appendTo(this.$('.dataset-listings'));
                }, this);
                this.children.tableDock.update();
            },

            renderRows: function() {
                _(this.children.rows).each(function(row) {
                    row.remove();
                }, this);
                this.children.rows = this.rowsFromCollection();
                this._render();
            },

            render: function() {
                if (!this.el.innerHTML) {
                    this.$el.append(this.compiledTemplate({}));
                    this.children.head.render().prependTo(this.$('> .table-chrome'));
                }
                this._render();
                return this;
            },

            template: '\
                <table class="table table-chrome table-striped table-row-expanding table-listing">\
                <tbody class="dataset-listings"></tbody>\
                </table>\
            '
        });
    }
);
