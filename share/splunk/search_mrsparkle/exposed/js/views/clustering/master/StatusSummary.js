define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'views/shared/FlashMessages',
    'views/clustering/master/components/ProgressBar/Master',
    'views/clustering/master/components/CollapsibleMessages/Master',
    'contrib/text!views/clustering/master/StatusSummary.html',
    'splunk.util',
    'util/splunkd_utils',
    'uri/route',
    './StatusSummary.pcss'
],
function(
    $,
    _,
    module,
    BaseView,
    FlashMessagesView,
    ProgressBarView,
    CollapsibleMessagesView,
    StatusSummaryTemplate,
    splunkUtil,
    splunkDUtils,
    route,
    css
){
    return BaseView.extend({
        moduleId: module.id,
        template: StatusSummaryTemplate,
        initialize: function(options){
            BaseView.prototype.initialize.call(this, options);

            this.children.flashMessages = new FlashMessagesView({
                className: 'message-single'
            });
            
            this.children.progressBar = new ProgressBarView({
                model: this.model.restartClusterStatus
            });
    
            this.children.collapsibleMessages = new CollapsibleMessagesView({
                model: this.model.restartClusterStatus
            });

            this.model.masterGeneration.on('change reset', function(){
                this.debouncedRender();
            }, this);

            this.model.indexesStatusSummary.on('change reset', function(){
                this.debouncedRender();
            }, this);

            this.model.peersStatusSummary.on('change reset', function(){
                this.debouncedRender();
            }, this);

            this.model.masterInfo.on('change reset', function(){
                if (this.model.masterInfo.entry.content.get('maintenance_mode')){

                    var root = this.model.application.get('root'),
                        locale = this.model.application.get('locale'),
                        docLink = route.docHelp(root, locale, 'manager.clustering.maintenancemode'),
                        restartMsg = '';
    
                    if (this.model.masterInfo.entry.content.get('rolling_restart_or_upgrade')) {
                        if (!this.model.masterInfo.entry.content.get('rolling_restart_flag')) {
                            restartMsg = _('A rolling upgrade of cluster peers is in progress.').t();
                        } else {
                            restartMsg = _('A rolling restart of cluster peers was initiated').t();
                            if (this.model.masterInfo.entry.content.get("controlled_rolling_restart_flag")) {
                                restartMsg += _(" in 'shutdown' mode and requires manual intervention.").t();
                            }
                            // If the cluster status polling hasn't been setup yet, start polling
                            !this.model.restartClusterStatus.ticker &&
                            this.model.restartClusterStatus.startPolling({
                                delay: 5000
                            });
                        }
                    } else {
                        this.clearRestartStatus();
                    }
                    
                    var errMessage = _('This cluster is in maintenance mode. ').t()+ '\n' + restartMsg + ' <a href="'+docLink+'" class="external" target="_blank">'+_('Learn more.').t()+'</a>';
                    
                    this.children.flashMessages.flashMsgHelper.addGeneralMessage('cluster_maint_mode',
                        {
                            type: splunkDUtils.WARNING,
                            html: errMessage
                        }
                    );
                } else {
                    this.children.flashMessages.flashMsgHelper.removeGeneralMessage('cluster_maint_mode');
                    this.clearRestartStatus();
                }
            }, this);
        },
        clearRestartStatus: function() {
            if (this.model.restartClusterStatus.ticker) {
                this.model.restartClusterStatus.stopPolling();
                this.children.progressBar.remove();
                this.children.collapsibleMessages.remove();
            }
        },
        render: function(){
            var pendingLastReason = this.model.masterGeneration.entry.content.get('pending_last_reason'),
                searchFactorMet = this.model.masterGeneration.entry.content.get('search_factor_met'),
                repFactorMet = this.model.masterGeneration.entry.content.get('replication_factor_met'),
                isClusterSearchable = (typeof pendingLastReason == 'undefined') ? pendingLastReason : (pendingLastReason === ''),
                isSearchFactorMet = (typeof searchFactorMet == 'undefined') ? searchFactorMet : splunkUtil.normalizeBoolean(searchFactorMet),
                isRepFactorMet = (typeof repFactorMet == 'undefined') ? repFactorMet : splunkUtil.normalizeBoolean(repFactorMet);

            var html = this.compiledTemplate({
                isClusterSearchable:  isClusterSearchable,
                isSearchFactorMet: isSearchFactorMet,
                isReplicationFactorMet: isRepFactorMet,
                numSearchablePeers: this.model.peersStatusSummary.get('numSearchable'),
                numNotSearchablePeers:  this.model.peersStatusSummary.get('numNotSearchable'),
                numSearchableIndexes: this.model.indexesStatusSummary.get('numSearchable'),
                numNotSearchableIndexes: this.model.indexesStatusSummary.get('numNotSearchable')
            });
            this.$el.html(html);
            this.$el.prepend(this.children.flashMessages.render().el);
    
            if (this.model.restartClusterStatus.ticker) {
                this.children.progressBar.render()
                    .$el.appendTo(this.$el.find('.restart-progress'));
                this.children.collapsibleMessages.render()
                    .$el.appendTo(this.$el.find('.status-messages'));
            }
            
            return this;
        }
    });
});
