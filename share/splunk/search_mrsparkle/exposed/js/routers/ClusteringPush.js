define(
    [
        'jquery',
        'underscore',
        'backbone',
        'routers/Base',
        'models/services/cluster/master/Control',
        'models/services/cluster/master/ValidateControl',
        'models/services/cluster/master/Rollback',
        'models/services/cluster/master/Info',
        'models/clustering/Actions',
        'models/services/cluster/master/Peer',
        'collections/services/cluster/master/Peers',
        'views/clustering/push/Master',
        'splunk.util'
    ],
    function(
        $,
        _,
        Backbone,
        BaseRouter,
        MasterControlModel,
        ValidateControlModel,
        RollbackModel,
        MasterInfoModel,
        ActionsModel,
        PeerModel,
        PeersCollection,
        ClusteringPushView,
        util
        ){
        return BaseRouter.extend({
            initialize: function() {
                BaseRouter.prototype.initialize.apply(this, arguments);
                this.enableAppBar = false;
                this.setPageTitle(_('Distribute Configuration Bundle').t());

                this.pushModel = new Backbone.Model();
                this.masterControl = new MasterControlModel();
                this.checkRestartControl = new ValidateControlModel();
                this.masterInfo = new MasterInfoModel();
                this.peers = new PeersCollection();
                this.rollbackModel = new RollbackModel();

                this.masterActiveBundle = null;
                this.masterLatestBundle = null;
                this.errors = [];
                this.validationProgress = [];
                this.restartProgress = [];
                this.reloadProgress = [];
                this.dryRunProgress = [];
                this.peersChecksumUpdated = [];  // to track peers have the updated checksum after every action.
                this.errorLabels = {
                    pushUnnecessary: _('Push Unnecessary').t(),
                    rollingRestartError: _('Rolling Restart Error').t()
                };

                this.deferreds.masterInfo = $.Deferred();
                this.deferreds.peers = $.Deferred();
    
                this.clusteringPushView = new ClusteringPushView({
                    model: {
                        application: this.model.application,
                        pushModel: this.pushModel,
                        masterInfo: this.masterInfo,
                        masterControl: this.masterControl
                    },
                    collection: {
                        peers: this.peers
                    }
                });

                // initial setup
                this.firstRun = true; // need it to stop the initial page load
                this.pushModel.set('inProgress', false); // if push is in progress at this moment
                this.pushModel.set('peersValidated', 0);
                this.pushModel.set('peersRestarted', 0);
                this.pushModel.set('peersReloaded', 0);
                this.pushModel.set('peersCheckRestarted', 0);

                this.peers.on('reset change', function() {
                    /*
                    Here we're going through all peers, counting as done those that have no errors and active=latest=master
                     */
                    if (!this.masterActiveBundle || !this.masterLatestBundle) {
                        return;
                    }
                    var i;
                    // initial reset of validationProgress array
                    if (this.validationProgress.length == 0) {
                        for (i=0; i<this.peers.length; i++) {
                            this.validationProgress[i] = false;
                        }
                    }
                    if (this.restartProgress.length == 0) {
                        for (i=0; i<this.peers.length; i++) {
                            this.restartProgress[i] = false;
                        }
                    }

                    if (this.reloadProgress.length == 0) {
                        for (i=0; i<this.peers.length; i++) {
                            this.reloadProgress[i] = false;
                        }
                    }

                    if (this.dryRunProgress.length == 0) {
                        for (i=0; i<this.peers.length; i++) {
                            this.dryRunProgress[i] = false;
                        }
                    }                    

                    if (this.pushModel.get('state') == 'validation') {
                        // while validation is on, repopulate the errors from zero
                        this.errors = [];
                    }

                    this.peers.each(function(peer, index) {
                        var activeBundleId = peer.entry.content.get('active_bundle_id'),
                            restartRequired = peer.entry.content.get('restart_required_for_applying_dry_run_bundle'),
                            _applyBundleStatus = peer.entry.content.get('apply_bundle_status'),
                            validationErrors = _applyBundleStatus.invalid_bundle.bundle_validation_errors,
                            label = peer.entry.content.get('label'),
                            status = this.getPeerState(peer),
                            bundleActionStatus = this.getPeerBundleStatus(peer);

                        if (util.normalizeBoolean(restartRequired)) {
                            this.pushModel.set('restartRequired', true);
                        }

                        if (!this.isActionComplete(this.validationProgress) || this.firstRun) {
                            if (validationErrors && validationErrors.length) {
                                this.errors.push({label: label, errors: validationErrors});
                            }
                            if (!this.firstRun &&
                                ((bundleActionStatus !== PeerModel.VALIDATING && status === PeerModel.PEER_STATUS_UP) ||
                                 (status !== PeerModel.PEER_STATUS_UP))) {
                                // Validation is complete if peer is done validating or is not up.
                                this.validationProgress[index] = true;
                            }
                        }

                        if (this.pushModel.get('state') === 'restart') {
                            if (status === PeerModel.PEER_STATUS_RESTARTING || status === PeerModel.PEER_STATUS_DOWN) {
                                this.restartProgress[index] = true;
                            }
                        }

                        if (this.isActionComplete(this.validationProgress) && bundleActionStatus !== PeerModel.RELOADING) {
                            this.reloadProgress[index] = true;

                            if (this.isActionComplete(this.reloadProgress) && bundleActionStatus !== PeerModel.CHECKING_RESTART) {
                                this.dryRunProgress[index] = true;
                            }
                        }
                        // this array is used to decide if polling the peers endpoint can be stopped.
                        this.peersChecksumUpdated[index] = (activeBundleId !== this.masterActiveBundle) ? false : true; 
                    }, this);

                    this.firstRun = false;
                    var peersValidated = this.getActionCount(this.validationProgress);
                    var peersRestarted = this.getActionCount(this.restartProgress);
                    var peersReloaded = this.getActionCount(this.reloadProgress);
                    var peersCheckRestarted = this.getActionCount(this.dryRunProgress);

                    if (peersValidated >= this.pushModel.get('peersValidated')) {
                        this.pushModel.set('peersValidated', peersValidated);
                    }
                    if (peersRestarted >= this.pushModel.get('peersRestarted')) {
                        this.pushModel.set('peersRestarted', peersRestarted);
                    }
                    if (peersReloaded >= this.pushModel.get('peersReloaded')) {
                        this.pushModel.set('peersReloaded', peersReloaded);
                    }
                    if (peersCheckRestarted >= this.pushModel.get('peersCheckRestarted')) {
                        this.pushModel.set('peersCheckRestarted', peersCheckRestarted);
                    }
                    this.pushModel.set('peersTotal', this.peers.length);
                    this.pushModel.set('errors', this.errors);
                    this.pushModel.trigger('tick');

                    if (this.pushModel.get('state') === 'idle' && 
                        this.isActionComplete(this.validationProgress) && this.peersChecksumUpdated.indexOf(false) === -1) {
                        this.peers.stopPolling();

                        this.pushModel.set('lastActionSuccess', this.isActionSuccessful());
                        this.pushModel.set('inProgress', false);
                    }
                }, this);    // end peers.on_change

                this.masterInfo.on('change', function() {
                    var _activeBundle = this.masterInfo.entry.content.get('active_bundle');
                    var _latestBundle = this.masterInfo.entry.content.get('latest_bundle');
                    if (!(_activeBundle && _latestBundle)) { return ; }

                    this.masterActiveBundle = _activeBundle.checksum;
                    this.masterLatestBundle = _latestBundle.checksum;
                    var _applyBundleStatus = this.masterInfo.entry.content.get('apply_bundle_status');
                    this.masterApplyBundleStatus = _applyBundleStatus.status;
                    this.masterValidationErrors = _applyBundleStatus.invalid_bundle.bundle_validation_errors_on_master;

                    var label = this.masterInfo.entry.content.get('label');

                    if (this.masterValidationErrors && this.masterValidationErrors.length) {
                        this.peers.stopPolling();
                        this.errors = [];
                        this.errors.push({label: label, errors: this.masterValidationErrors});
                        this.pushModel.set('lastActionSuccess', this.isActionSuccessful());
                        this.pushModel.set('inProgress', false);
                        this.pushModel.set('errors', this.errors);
                        this.pushModel.trigger('tick');
                    }
                    var state = this.getState();
                    this.pushModel.set('state', state);
                    this.pushModel.trigger('action');

                    if (state == 'idle') {
                        this.masterInfo.stopPolling();
                    }
                }, this);     // end of masterInfo.on_change

                this.pushModel.on(ActionsModel.actions.PUSH, function() {
                    /*
                    On user confirm, issue an apply command and start polling status endpoints until all peers
                    receive the bundle or report an error
                     */
                    this.pushModel.set('lastRunAction', ActionsModel.actions.PUSH);
                    this.cleanupPushModel();
                    
                    this.masterControl.save()
                        .done(function(){
                            this.monitorPushStatus();
                        }.bind(this))
                        .fail(function(respErr) {
                            var errorText = respErr.responseJSON.messages[0].text;
                            if (errorText.toLowerCase().indexOf('rolling restart') !== -1) {
                                this.handleFail(this.errorLabels.rollingRestartError, errorText);
                            } else {
                                this.handleFail(this.errorLabels.pushUnnecessary, errorText);
                            }
                        }.bind(this));
                }, this);

                this.pushModel.on(ActionsModel.actions.CHECK_RESTART, function() {
                    this.pushModel.set('lastRunAction', ActionsModel.actions.CHECK_RESTART);
                    this.cleanupPushModel();
                    
                    this.checkRestartControl.save({}, {
                        data: {
                            'check-restart': '1'
                        }
                    }).done(function(){
                            this.monitorPushStatus();
                        }.bind(this))
                        .fail(function(respErr) {
                            this.handleFail(_('Check Restart Unsuccessful').t(), respErr.responseJSON.messages[0].text);
                        }.bind(this));
                }, this);
    
                this.pushModel.on(ActionsModel.actions.ROLLBACK, function() {
                    /*
                     On user confirm, issue a rollback command and start polling status endpoints until all peers
                     rollback the bundle or return an error
                     */
                    this.pushModel.set('lastRunAction', ActionsModel.actions.ROLLBACK);
                    this.cleanupPushModel();
                    
                    this.rollbackModel.save()
                        .done(function(){
                            this.monitorPushStatus();
                        }.bind(this))
                        .fail(function(respErr) {
                            this.handleFail(_('Rollback Unsuccessful').t(), respErr.responseJSON.messages[0].text);
                        }.bind(this));
                }, this);
            },

            handleFail: function(errName, errText) {
                this.errors = [];
                this.errors.push({label: errName, errors: errText});
                this.pushModel.set('lastActionSuccess', false);
                this.pushModel.set('inProgress', false);
                this.pushModel.set('errors', this.errors);
                this.pushModel.set('state', 'idle');
                this.pushModel.trigger('tick');
                this.pushModel.trigger('change:state');
                this.peers.fetch();
                this.masterInfo.fetch();
            },

            getPeerState: function(peer) {
                return peer.entry.content.get('status');
            },

            getPeerBundleStatus: function(peer) {
                return peer.entry.content.get('apply_bundle_status').status;
            },

            getState: function() {
                var status = this.masterInfo.entry.content.get('apply_bundle_status').status;
                var validation = (status === "Bundle validation is in progress.");
                var creation = (status === "Bundle Creation is in progress.");
                var reload = (this.masterInfo.entry.content.get('apply_bundle_status').reload_bundle_issued ||
                              status === "Bundle dryrun reload is in progress. Waiting for all peers to return the status.");
                var restart = this.masterInfo.entry.content.get('rolling_restart_flag');

                return validation? 'validation': reload? 'reload': restart? 'restart': creation? 'creation': 'idle';
            },

            cleanupPushModel: function() {
                this.errors = [];
                this.pushModel.set('peersValidated', 0);
                this.pushModel.set('errors', {});
                this.pushModel.trigger('tick');
                this.validationProgress.splice(0); // Clears array
                this.reloadProgress.splice(0);
                this.dryRunProgress.splice(0);
                this.restartProgress.splice(0);
                this.pushModel.unset('restartRequired', {silent:true});
            },

            getActionCount: function(actionProgressArray) {
                return _.reduce(actionProgressArray, function(memo, item) {
                    return item ? memo+1 : memo;
                }, 0);
            },

            isActionComplete: function(actionProgressArray) {
                return _.reduce(actionProgressArray, function(memo, item) {
                    return memo && item;
                }, true);
            },

            isActionSuccessful: function() {
                var hasNoCriticalErrors = true;
                var hasNoPushUnnecessaryError = true;
                var hasNoRollingRestartError = true;

                _.each(this.errors, function(instance) {
                    var instanceErrors = instance['errors'];

                    if (instance['label'] === this.errorLabels.pushUnnecessary) {
                        hasNoPushUnnecessaryError = false;
                    } else if (instance['label'] === this.errorLabels.rollingRestartError) {
                        hasNoRollingRestartError = false;
                    }

                    if (!_.isArray(instanceErrors)) {
                        return;
                    }

                    _.each(instanceErrors, function(error) {
                        var isCriticalError = error.indexOf('[Critical]') !== -1;

                        if (isCriticalError) {
                            hasNoCriticalErrors = false;
                        }
                    });
                }, this);

                var applyBundleStatus = this.masterInfo.entry.content.get('apply_bundle_status');
                var hasNoInvalidBundle =true;
                if (applyBundleStatus.invalid_bundle && applyBundleStatus.invalid_bundle.checksum) {
                    hasNoInvalidBundle = false;
                }

                return (this.masterActiveBundle === this.masterLatestBundle) &&
                    hasNoCriticalErrors && hasNoPushUnnecessaryError && hasNoInvalidBundle && hasNoRollingRestartError;
            },

            monitorPushStatus: function() {
                this.pushModel.set('state', 'validation');
                this.pushModel.set('inProgress', true);
                this.masterInfo.startPolling({ delay: 1000 });
                this.peers.startPolling({
                        'delay': 500,
                        'data': {
                            'count': this.peers.paging.get('perPage')
                        }
                });
            },

            page: function(locale, app, page) {
                BaseRouter.prototype.page.apply(this, arguments);
    
                // Initial fetch of master info and peer data
                this.masterInfo.fetch({
                    data: {},
                    success: function(model, response) {
                        this.deferreds.masterInfo.resolve();
                    }.bind(this),
                    
                    error: function(model,response) {
                        this.deferreds.masterInfo.resolve();
                    }.bind(this)
                });
                this.peers.fetch({
                    data: {
                        count: 10
                    },
                    success: function(model, response) {
                        this.deferreds.peers.resolve();
                    }.bind(this),

                    error: function(model,response) {
                        this.deferreds.peers.resolve();
                    }.bind(this)
                });

                this.deferreds.pageViewRendered.done(function() {
                    $('.preload').replaceWith(this.pageView.el);
                    $.when(this.deferreds.masterInfo, this.deferreds.peers).then(function() {
                        this.monitorPushStatus();
                        this.pageView.$('.main-section-body').append(this.clusteringPushView.render().el);
                    }.bind(this));
                }.bind(this));
            }
        });
    }
);
