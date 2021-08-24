define(
    [
        'underscore',
        'jquery',
        'backbone',
        'routers/ManagementconsoleBase',
        'models/managementconsole/ChangesCollectionFetchData',
        'collections/managementconsole/Changes',
        'views/managementconsole/audit_logs/Master'
    ],
    function(
        _,
        $,
        Backbone,
        DmcBaseRouter,
        ChangesCollectionFetchData,
        ChangesCollection,
        AuditLogsView
    ) {
        return DmcBaseRouter.extend({
            initialize: function() {
                DmcBaseRouter.prototype.initialize.apply(this, arguments);
                this.setPageTitle(_('Install Log').t());
                this.enableFooter = false;
                this.collection = this.collection || {};
                this.deferreds = this.deferreds || {};
                this.children = this.children || {};

                this._initializeChangesCollection('changes');
            },

            page: function(locale, app, page) {
                DmcBaseRouter.prototype.page.apply(this, arguments);

                $.when(
                    this.deferreds.pageViewRendered, 
                    this.deferreds.changes,
                    this.deferreds.application,
                    this.deferreds.appLocal,
                    this.deferreds.user
                ).done(function() {
                    $('.preload').replaceWith(this.pageView.el);

                    this.children.table = new AuditLogsView({
                        model: {
                            appLocal: this.model.appLocal,
                            user: this.model.user,
                            application: this.model.application
                        },
                        collection: { 
                            changes: this.collection.changes
                        }
                    });
                    
                    this.pageView.$('.main-section-body').append(this.children.table.render().$el);
                }.bind(this));
            },

             _initializeChangesCollection: function(name, options) {
                var fetchData = new ChangesCollectionFetchData(
                    $.extend(
                        true,
                        {
                            count: 25,
                            offset: 0,
                            sortKey: 'name',
                            sortDirection: 'desc',
                            query: '{}',
                            type: ['app'],
                            state: 'deployed',
                            timeRange: ChangesCollection.TIME_RANGE.lastWeek
                        },
                        options
                    )
                );

                this.collection[name] = new ChangesCollection(null, {
                    fetchData: fetchData
                });

                this.deferreds[name] = this.collection[name].fetch();
            }
        });
    }
);