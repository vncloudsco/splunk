define([
    'jquery',
    'underscore',
    'module',
    'models/Base',
    'models/clustering/Actions',
    'views/Base',
    'views/clustering/push/PushStatus',
    'views/clustering/push/ActionProgress',
    'views/clustering/push/PushErrors',
    'views/clustering/push/peer_nodes/table/Master',
    'views/clustering/push/peer_nodes/TableControls',
    'views/clustering/push/system/Actions',
    'views/clustering/push/StatusMessage',
    'uri/route',
    'contrib/text!views/clustering/push/Master.html',
    './Master.pcss'
],
function(
    $,
    _,
    module,
    BaseModel,
    ActionsModel,
    BaseView,
    PushStatus,
    ActionProgressBar,
    PushErrors,
    StatusTableView,
    TableControls,
    ActionsView,
    StatusMessageView,
    route,
    Template,
    css
){
        return BaseView.extend({
            moduleId: module.id,
            template: Template,
            initialize: function(options) {
                BaseView.prototype.initialize.call(this, options);
                this.children.pushStatus = new PushStatus({
                    model: {
                        pushModel: this.model.pushModel,
                        masterInfo: this.model.masterInfo
                    }
                });

                this.children.validateProgress = new ActionProgressBar({
                    model: {
                        pushModel: this.model.pushModel,
                        masterInfo: this.model.masterInfo
                    },
                    peerActionTypeKey: 'peersValidated',
                    label: _('Peers Validated:').t()
                });

                this.children.restartProgress = new ActionProgressBar({
                    model: {
                        pushModel: this.model.pushModel,
                        masterInfo: this.model.masterInfo
                    },
                    peerActionTypeKey: 'peersRestarted',
                    label: _('Restarting Peer:').t()
                });

                this.children.reloadProgress = new ActionProgressBar({
                    model: {
                        pushModel: this.model.pushModel,
                        masterInfo: this.model.masterInfo
                    },
                    peerActionTypeKey: 'peersReloaded',
                    label: _('Peers Reloaded:').t()
                });

                this.children.checkRestartProgress = new ActionProgressBar({
                    model: {
                        pushModel: this.model.pushModel,
                        masterInfo: this.model.masterInfo
                    },
                    peerActionTypeKey: 'peersCheckRestarted',
                    label: _('Peers Checked For Restart:').t()
                });

                this.children.pushErrors = new PushErrors({
                    model: {
                        pushModel: this.model.pushModel
                    }
                });

                this.children.tableControls = new TableControls({
                    model: {
                        state: this.collection.peers.fetchData,
                        pushModel: this.model.pushModel
                    },
                    collection: {
                        peers: this.collection.peers
                    }
                });

                this.children.statusTableView = new StatusTableView({
                    model: {
                        state: this.collection.peers.fetchData,
                        pushModel: this.model.pushModel
                    },
                    collection: {
                        peers: this.collection.peers
                    }
                });

                this.children.actionsView = new ActionsView({
                    model: this.model
                });

                this.model.pushModel.on('action', function() {
                    if (this.children.statusMessage) {
                        this.children.statusMessage.remove();
                    }
                    this.children.statusMessage = new StatusMessageView({
                        model: {
                            masterInfo: this.model.masterInfo
                        }
                    });

                    this.children.pushStatus.$el.hide();
                    this.children.actionsView.disableButtons();
                    this.$('.section-bg').prepend(this.children.statusMessage.render().el);
                    this.children.statusMessage.$el.show();
                }, this);

                this.model.pushModel.on('change:state', function() {
                    /*
                    Toggle between status and progress views when progress begins or ends
                     */
                    var state = this.model.pushModel.get('state');
                    if (state !== 'idle') {
                        var lastRunAction = this.model.pushModel.get('lastRunAction');
                        if (lastRunAction === ActionsModel.actions.VALIDATE) {
                            this.children.validateProgress.reset();
                            this.children.validateProgress.$el.show();
                        } else if (lastRunAction === ActionsModel.actions.CHECK_RESTART) {
                            this.children.validateProgress.reset();
                            this.children.validateProgress.$el.show();
                            this.children.reloadProgress.reset();
                            this.children.reloadProgress.$el.show();
                            this.children.checkRestartProgress.reset();
                            this.children.checkRestartProgress.$el.show();
                        } else if (lastRunAction === ActionsModel.actions.ROLLBACK) {
                            this.children.validateProgress.reset();
                            this.children.validateProgress.$el.show();
                            this.children.reloadProgress.reset();
                            this.children.reloadProgress.$el.show();
                            if ((state) === 'restart') {
                                this.children.restartProgress.reset();
                                this.children.restartProgress.$el.show();
                            }
                        } else if (lastRunAction === ActionsModel.actions.PUSH) {
                            this.children.validateProgress.reset();
                            this.children.validateProgress.$el.show();
                            this.children.reloadProgress.reset();
                            this.children.reloadProgress.$el.show();
                            if ((state) === 'restart') {
                                this.children.restartProgress.reset();
                                this.children.restartProgress.$el.show();
                            }
                        }
                    } else {
                        setTimeout(function() {  // let user contemplate on the results for a second
                            this.children.pushStatus.$el.show();
                            this.children.validateProgress.$el.hide();
                            this.children.checkRestartProgress.$el.hide();
                            this.children.reloadProgress.$el.hide();
                            this.children.restartProgress.$el.hide();
                            if (this.children.statusMessage) {
                                this.children.statusMessage.$el.hide();
                            }
                            this.children.actionsView.enableButtons();
                        }.bind(this), 1000);
                    }
                }, this);

                this.model.pushModel.on('tick', function() {
                    if (_.isEmpty(this.model.pushModel.get('errors'))) {
                        this.children.pushErrors.$el.hide();
                    } else {
                        this.children.pushErrors.$el.show();
                    }
                }, this);
            },

            render: function() {
                var root = this.model.application.get('root'),
                    locale = this.model.application.get('locale'),
                    docLink = route.docHelp(root, locale, 'manager.clustering.bundle'),
                    learnMoreLink = route.docHelp(root, locale, 'learnmore.clustering.bundle');
                var html = this.compiledTemplate({
                    docLink: docLink,
                    learnMoreLink: learnMoreLink
                });
                this.$el.html(html);
                this.$('.section-header').append(this.children.actionsView.render().el);
                this.$('.section-bg').append(this.children.pushStatus.render().el);
                this.$('.section-bg').append(this.children.validateProgress.render().el);
                this.$('.section-bg').append(this.children.reloadProgress.render().el);
                this.$('.section-bg').append(this.children.checkRestartProgress.render().el);
                this.$('.section-bg').append(this.children.restartProgress.render().el);
                this.$('.section-bg').append(this.children.pushErrors.render().el);
                this.$('.section-bg').append(this.children.tableControls.render().el);
                this.$('.section-bg').append(this.children.statusTableView.render().el);
                this.children.validateProgress.$el.hide();
                this.children.reloadProgress.$el.hide();
                this.children.checkRestartProgress.$el.hide();
                this.children.restartProgress.$el.hide();
            }
        });

    });
