define(
[
    'jquery',
    'underscore',
    'module',
    'splunk.util',
    'models/Base',
    'util/indexes/AddEditIndexPanelConstants',
    'views/Base',
    'views/shared/Message',
    'views/shared/FlashMessages',
    'views/shared/token/BaseToken',
    'views/shared/react_buttons/Pencil',
    'views/shared/react_buttons/Trash',
    'views/shared/Modal',
    'views/indexes/shared/rollup/RollupSettings.pcss'
],
function(
    $,
    _,
    module,
    splunkutil,
    BaseModel,
    PANEL_CONSTANTS,
    BaseView,
    MessageView,
    FlashMessagesView,
    BaseToken,
    Pencil,
    Trash,
    Modal,
    css
){
    return BaseView.extend( /** @lends views.RollupSettings.prototype */ {
        moduleId: module.id,
        /**
         * @constructor
         * @memberOf views
         * @name RollupSettings
         * @extends {views.BaseView}
         * @description View to display rollup settings within the add/edit index modal
         *
         * @param {Object} options
         * @param {Object} options.model The model supplied to this class
         */
        initialize: function(options) {
            BaseView.prototype.initialize.call(this, options);
            var tokenText = this.getTokenText();
            if (tokenText) {
                var tokenStyle = {
                    border: 'none',
                    backgroundColor: 'Transparent',
                };
                var baseTokenModel = new BaseModel({
                    text: tokenText,
                    icons: [
                        new Pencil({
                            className: 'token-button token-button-edit',
                            style: tokenStyle,
                            onClick: this.handleEditClick.bind(this)
                        }),
                        new Trash({
                            className: 'token-button token-button-delete',
                            style: tokenStyle,
                            onClick: this.handleDeleteClick.bind(this)
                        })
                    ]
                });
                this.children.deleteToken = new BaseToken({
                    model: {
                        content: baseTokenModel
                    }
                });
            }
            this.children.flashMessagesView = new FlashMessagesView({
                model: this.model.rollup,
                helperOptions: {
                    removeServerPrefix: true,
                    postProcess: this.postProcess
                }
            });
            if (!this.model.rollup.get('hasEditCapability')) {
                this.children.messageView = new MessageView({
                    type: 'warning',
                    children: _("You cannot create or edit rollup policies for this index. Your role does not have the edit_metrics_rollup capability.").t()
                });
            }
        },
        handleNavToRollup: function(panelId) {
            var dfds = this.fetchRollupCollections();
            this.model.rollup.set('toRollupTransitioning', true);
            $.when.apply($, dfds).then(function() {
                this.model.rollup.updateRollupCollections({
                    collection: {
                        dimensions: this.collection.dimensions,
                        metrics: this.collection.metrics,
                        indexes: this.collection.indexes
                    }
                }, {});
                this.model.content.set({
                    toRollupTransitioning: false,
                    activePanelId: panelId
                });
            }.bind(this));
        },
        fetchRollupCollections: function() {
            var metricName = this.model.rollup.get('name');

            var metricsDfd = this.collection.metrics.fetch({
                data: {
                    filter: 'index=' + metricName,
                    count: 0
                }
            });
            var dimensionsDfd = this.collection.dimensions.fetch({
                data: {
                    filter: 'index=' + metricName,
                    metric_name: '*',
                    count: 0
                }
            });
            var metricIndexesDfd = this.collection.indexes.fetch({
                data: {
                    datatype: 'metric',
                    count: 0
                }
            });

            return [
                metricsDfd,
                dimensionsDfd,
                metricIndexesDfd
            ];
        },
        handleEditClick: function() {
            this.handleNavToRollup(PANEL_CONSTANTS.CONFIRM_EDIT_ROLLUP);
        },
        handleDeleteClick: function() {
            this.model.content.set('activePanelId', PANEL_CONSTANTS.CONFIRM_DELETE_ROLLUP);
        },
        events: {
            'click .add-policy-link': function(e) {
                e.preventDefault();
                this.handleNavToRollup(PANEL_CONSTANTS.ROLLUP_SETTINGS);
            }
        },
        showConfirmDeleteDialog: function() {
            this.children.confirmDeleteDialog = new Modal({
                model: {
                    content: this.model.content
                }
            });
            this.children.confirmDeleteDialog.render().appendTo($("body"));
        },
        getTokenText: function() {
            var rollupTimes = this.model.rollup.get('rollupTimes');
            if (!rollupTimes || !rollupTimes.length) {
                return null;
            }
            return rollupTimes.map(function(time, i) {
                var text;
                if (i === 0) {
                    text = 'Summarize data every ' + time;
                } else if (i === rollupTimes.length - 1) {
                    if (i === 0) {
                        return time;
                    } else {
                        text = 'and ' + time;
                    }
                } else {
                    text = time;
                }
                return i < rollupTimes.length - 2 ? text + ',' : text;
            }).join(' ');
        },
        render: function() {
            if (!this.el.innerHTML) {
                var template = _.template(this.template, {
                    _: _
                });
                this.$el.html(template);
                this.children.flashMessagesView.render().appendTo(this.$(".rollup-flash-messages-view-placeholder"));
                if (this.children.deleteToken) {
                    this.$('.delete-token-placeholder').append(this.children.deleteToken.render().el);
                }
                if (this.children.messageView) {
                    this.$('.message-view-placeholder').append(this.children.messageView.render().el);
                }
            }
            var rollupTimes = this.model.rollup.get('rollupTimes');
            var addPolicy = !rollupTimes || !rollupTimes.length;
            if (addPolicy) {
                this.$('.add-policy-link').show();
                this.$('.edit-policy-note').hide();
            } else {
                this.$('.add-policy-link').hide();
                this.$('.edit-policy-note').show();
            }
            return this;
        },
        template: '\
                <div><strong><%- _("Rollup Policy Setting").t() %></strong></div>\
                <span class="rollup-help-text"><%- _("Create a rollup policy to improve search performance and storage costs for high-volume metrics.").t() %></span>\
                <a href="/help?location=settings.metrics.rollup" class="external rollup-learn-more" target="_blank"><%= _("Learn More").t() %></a>\
                <div class="rollup-flash-messages-view-placeholder"></div>\
                <div class="message-view-placeholder"></div>\
                <div class="delete-token-placeholder"></div>\
                <a class="add-policy-link" href="#"><%- _("+ Create a new policy").t() %></a>\
        '
    });
});
