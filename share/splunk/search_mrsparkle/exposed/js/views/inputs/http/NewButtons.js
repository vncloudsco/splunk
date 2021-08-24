/**
 * @author lbudchenko
 * @date 8/13/14
 *
 */
define([
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'splunk.util'
    ],
    function (
        $,
        _,
        module,
        BaseView,
        utils
    ) {

        return BaseView.extend({
            moduleId: module.id,

            events: {
                'click .new-entity-button': function(e) {
                    e.preventDefault();
                    if (!$(e.currentTarget).is('.disabled')) {
                        this.model.controller.trigger("editEntity");
                    }
                },
                'click .global-settings-button': function(e) {
                    e.preventDefault();
                    this.model.controller.trigger("globalSettings");
                }
            },

            initialize: function (options) {
                BaseView.prototype.initialize.call(this, options);
                this.isStackmakr = utils.isStackmakr(this.model.dmcSettings.isEnabled(), this.model.serverInfo.isCloud());

                this.listenTo(this.model.controller, "globalSaved", this.checkTokensDisabled);
                this.listenTo(this.model.controller, "change:globalBlock", this.handleGlobalBlock);
            },

            checkTokensDisabled: function() {
                var disabled = this.model.settings.get('ui.disabled'),
                    $warningIcon = this.$('.tokens-disabled-warning');
                if (disabled && !this.model.serverInfo.isCloud()) {
                    var tooltipText = _("All the tokens are currently disabled. They can be enabled in the Global Settings.").t();
                    $warningIcon.tooltip({ animation: false, title: tooltipText, container: $warningIcon, placement: "bottom" });
                    $warningIcon.show();
                } else {
                    $warningIcon.hide();
                }
            },

            checkGlobalSettings: function() {
                if (this.model.serverInfo.isCloud()) {
                    this.$('.global-settings-button').hide();
                    if (!this.model.dmcSettings.isEnabled() && this.options.isCloudCluster) {
                        this.$('.new-entity-button').hide();
                    }
                }
            },

            handleGlobalBlock: function(model, enabled) {
                if (enabled) {
                    this.$el.find('a.new-entity-button').addClass('disabled');
                    this.$el.find('a.global-settings-button').addClass('disabled');
                } else {
                    this.$el.find('a.new-entity-button').removeClass('disabled');
                    this.$el.find('a.global-settings-button').removeClass('disabled');
                }
            },

            render: function () {
                var html = this.compiledTemplate({
                    entitySingular: this.options.entitySingular
                });

                this.$el.html(html);

                this.checkTokensDisabled();
                this.checkGlobalSettings();

                if (this.isStackmakr) {
                    this.handleGlobalBlock(null, this.model.controller.get('globalBlock'));
                }

                return this;
            },

            template: '\
            <div class="tokens-disabled-warning alert-error red-triangle-warning"><i class="icon-alert"/></div>\
            <a href="#" class="btn btn-secondary global-settings-button"><%- _("Global Settings").t() %></a>\
            <a href="#" class="btn btn-primary new-entity-button"><%- _("New ").t() + entitySingular %></a>'

        });
    });
