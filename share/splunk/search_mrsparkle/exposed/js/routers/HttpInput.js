/**
 * This the router for the page at manager/system/http-input.
 */

define(
    [
        'jquery',
        'underscore',
        'backbone',
        'routers/Base',
        'models/managementconsole/DmcSettings',
        'models/managementconsole/Task',
        'models/managementconsole/Deploy',
        'views/inputs/http/PageController'
    ],
    function(
        $,
        _,
        Backbone,
        BaseRouter,
        DMCSettingsModel,
        TaskModel,
        DeployModel,
        PageController
        ) {
        return BaseRouter.extend({

            initialize: function(options) {
                BaseRouter.prototype.initialize.apply(this, arguments);
                this.enableAppBar = false;
                this.fetchAppLocals = true;

                this.isCloudCluster = _.isObject(options) ? !!options.isCloudCluster : false;

                // The controller model is passed down to all subviews and serves as the event bus for messages between
                // the controller and views.
                this.model.controller = new Backbone.Model();
                this.model.dmcSettings = new DMCSettingsModel();

                this.deferreds.dmcSettings = this.model.dmcSettings.fetch();
                this.deferreds.dmcSettings.done(function() {
                    if (this.model.dmcSettings.isEnabled()) {
                        this.initializeDeployTaskModel();
                        this.initializeDeployModel();

                        this.listenTo(this.model.controller, 'actionSuccess', function(action, entity) {
                            // upon successful completion of an entity action, disable all the actions
                            this.enableGlobalBlock();
                        });
                    }
                }.bind(this));
            },

            // Initialize deploy task model to keep track of the deploy action progress. No initial fetch
            initializeDeployTaskModel: function() {
                this.model.deployTask = new TaskModel();

                this.listenTo(this.model.deployTask.entry.content, 'change:state', function() {
                    this.handleDeployTaskChange();
                });
            },

            // Initialize the deploy model - provide taskId for the last deployment
            initializeDeployModel: function() {
                this.model.deployModel = new DeployModel();
                this.model.deployModel.startPolling();

                this.listenTo(this.model.deployModel.entry.content, 'change:taskId', function(model, taskId) {
                    this.model.deployTask.entry.set('name', taskId);
                    this.model.deployTask.beginPolling();
                    this.model.deployTask.trigger('newTask');
                }.bind(this));
            },

            handleDeployTaskChange: function() {
                if (this.model.deployTask.hasState() && this.model.deployTask.inProgress()) {
                    this.enableGlobalBlock();
                } else {
                    this.disableGlobalBlock();
                }
            },

            enableGlobalBlock: function() {
                this.model.controller.set('globalBlock', true);
            },

            disableGlobalBlock: function() {
                this.model.controller.set('globalBlock', false);
                this.model.controller.trigger('refreshEntities');
            },

            page: function(locale, app, page) {
                BaseRouter.prototype.page.apply(this, arguments);

                this.setPageTitle(_('HTTP Event Collector').t());

                $.when(this.deferreds.pageViewRendered, this.deferreds.dmcSettings)
                    .done(_(function() {
                        $('.preload').replaceWith(this.pageView.el);

                        if (this.inputController) {
                            this.inputController.detach();
                        }
                        this.inputController = new PageController({
                            isCloudCluster: this.isCloudCluster,
                            model: this.model,
                            collection: this.collection
                        });
                        this.pageView.$('.main-section-body').append(this.inputController.render().el);
                    }).bind(this));
            }
        });
    }
);
