define(
    [
        'jquery',
        'underscore',
        'backbone',
        'routers/ManagementconsoleBase',
        'models/managementconsole/DmcFetchData',
        'models/managementconsole/ChangesCollectionFetchData',
        'models/managementconsole/Task',
        'models/managementconsole/Deploy',
        'collections/managementconsole/Groups',
        'collections/managementconsole/Changes',
        'collections/managementconsole/topology/Instances',
        'collections/services/AppLocals',
        'collections/services/authorization/Roles',
        'views/managementconsole/apps/app_listing/PageController'
    ],
    function(
        $,
        _,
        Backbone,
        DmcBaseRouter,
        DmcFetchData,
        ChangesCollectionFetchData,
        TaskModel,
        DeployModel,
        GroupsCollection,
        ChangesCollection,
        InstancesCollection,
        AppsLocalCollection,
        RolesCollection,
        PageController
    ) {
        return DmcBaseRouter.extend({
            initialize: function(options) {
                DmcBaseRouter.prototype.initialize.call(this, options);
                this.setPageTitle(_('Apps').t());
                this.fetchAppLocals = true;

                this.model.metadata = new DmcFetchData({
                    sortKey: 'name',
                    sortDirection: 'asc',
                    count: '20',
                    offset: 0,
                    nameFilter: '',
                    query: '{"$and": [{"staged": false}, {"manageable": {"$ne": false}}]}'
                });

                this.initializeAppsLocal();
                this.initializeDeployTaskModel();
                this.initializeDeployModel();
                this.initializeRolesCollection();

                this.model.deployModel.on('serverValidated', function(success, context, messages) {
                    var netErrorMsg = _.find(messages, function(msg) {
                        return msg.type === 'network_error' || msg.text === 'Server error';
                    });
                    if (netErrorMsg) {
                        this.model.deployModel.entry.content.unset('taskId');
                        this.initializeDeployModel();
                    }
                }, this);
            },

            initializeAppsLocal: function() {
                this.collection.appsLocal = new AppsLocalCollection();
                this.deferreds.appsLocal = this.collection.appsLocal.fetch({
                    data: {
                        count: -1
                    }
                });
            },

            // Initialize deploy task model to keep track of the deploy action progress. No initial fetch
            initializeDeployTaskModel: function() {
                this.model.deployTask = new TaskModel();
                this.model.deployModel = new DeployModel();
            },

            // Initialize the deploy model - provide taskId for the last deployment
            initializeDeployModel: function() {
                this.model.deployModel.startPolling();

                this.listenTo(this.model.deployModel.entry.content, 'change:taskId', function(model, taskId) {
                    if (!this.model.deployTask.isPolling()) {
                        this.model.deployTask.entry.set('name', taskId);
                        this.model.deployTask.beginPolling().done(function() {
                            this.model.deployTask.trigger('syncApps');
                        }.bind(this));
                    }
                    this.model.deployTask.trigger('newTask');
                }.bind(this));
            },

            initializeRolesCollection: function() {
                this.collection.roles = new RolesCollection();
                this.deferreds.roles = this.collection.roles.fetch();
            },

            page: function(locale, app, page) {
                DmcBaseRouter.prototype.page.apply(this, arguments);

                $.when(
                    this.deferreds.pageViewRendered,
                    this.deferreds.user,
                    this.deferreds.appsLocal,
                    this.deferreds.roles
                ).done(_(function() {
                    this.pageController = new PageController({
                        model: this.model,
                        collection: this.collection
                    });

                    this.pageController.renderDfd.done(function() {
                        $('.preload').replaceWith(this.pageView.el);
                        this.pageView.$('.main-section-body').append(this.pageController.render().el);
                    }.bind(this));
                }).bind(this));
            }
        });
    }
);
