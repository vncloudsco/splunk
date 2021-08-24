define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'views/shared/FlashMessages',
    'models/clustering/Actions',
    'contrib/text!views/clustering/push/PushStatus.html',
    'util/time',
    'bootstrap.tooltip'
],
    function(
        $,
        _,
        module,
        BaseView,
        FlashMessagesView,
        ActionsModel,
        Template,
        timeUtils,
        bsTooltip
    ) {
        return BaseView.extend({
            moduleId: module.id,
            template: Template,
            initialize: function(options) {
                BaseView.prototype.initialize.call(this, options);
                this.children.flashMessages = new FlashMessagesView({ model: this.model.masterControl });
                this.model.pushModel.on('reset change', this.render, this);
            },
            getTitle: function() {
                switch (this.model.pushModel.get('lastRunAction')) {
                    case ActionsModel.actions.CHECK_RESTART:
                        return _('Last Validate and Check Restart: ').t();
                    case ActionsModel.actions.PUSH:
                        return _('Last Push: ').t();
                    case ActionsModel.actions.ROLLBACK:
                        return _('Last Rollback: ').t();
                    default:
                        return _('Bundle Information: ').t();
                }
                
            },
            render: function() {
                if (!this.model.masterInfo || !this.model.pushModel) {
                    return;
                }
                var activeBundle = this.model.masterInfo.entry.content.get('active_bundle');
                var latestBundle = this.model.masterInfo.entry.content.get('latest_bundle');
                var checkRestartBundle = this.model.masterInfo.entry.content.get('last_dry_run_bundle');
                var previousBundle = this.model.masterInfo.entry.content.get('previous_active_bundle');
                var timeLastPush = latestBundle && latestBundle.timestamp ? timeUtils.convertToLocalTime(latestBundle.timestamp) : _('N/A').t();
                var activeBundleId = activeBundle && activeBundle.checksum && activeBundle.checksum !== "" ? activeBundle.checksum : _('N/A').t();
                var latestBundleId = latestBundle && latestBundle.checksum && latestBundle.checksum !== "" ? latestBundle.checksum : _('N/A').t();
                var checkRestartBundleId = checkRestartBundle && checkRestartBundle.checksum && checkRestartBundle.checksum !== "" ? checkRestartBundle.checksum : _('N/A').t();
                var previousBundleId = previousBundle && previousBundle.checksum && previousBundle.checksum !== "" ? previousBundle.checksum : _('N/A').t();
    
                var html = this.compiledTemplate({
                    lastActionSuccess: this.model.pushModel.get('lastActionSuccess'),
                    timeLastPush: timeLastPush,
                    activeBundleId: activeBundleId,
                    latestBundleId: latestBundleId,
                    checkRestartBundleId: checkRestartBundleId,
                    previousBundleId: previousBundleId,
                    lastRunAction: this.model.pushModel.get('lastRunAction'),
                    restartRequired: this.model.pushModel.get('restartRequired'),
                    title: this.getTitle(),
                    actions: ActionsModel.actions
                });
                this.$el.html(html);
                this.$el.prepend(this.children.flashMessages.render().el);
                this.$('.tooltip-link').tooltip({animation:false, container: 'body'});
            }
            
        });

    });
