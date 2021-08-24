/**
 * @author lbudchenko/jszeto
 * @date 2/9/14
 *
 * Represents a row in the table. The row contains links to perform
 * operations on the given index. The user can expand the row to see more details about the index
 */
define([
    'jquery',
    'underscore',
    'backbone',
    'module',
    'views/Base',
    'views/shared/controls/SyntheticCheckboxControl',
    'views/shared/delegates/RowExpandCollapse',
    'util/format_numbers_utils',
    'util/time',
    'splunk.util',
    'contrib/text!views/inputs/http/GridRow.html'
],
    function (
        $,
        _,
        Backbone,
        module,
        BaseView,
        SyntheticCheckboxControl,
        RowExpandCollapse,
        formatNumbersUtils,
        timeUtils,
        splunkUtils,
        template
        ) {

        return BaseView.extend({
            moduleId: module.id,
            tagName: "tr",
            className: "list-item",
            template: template,

            events: (function() {
                var events = {};
                events['click .cell-token'] = function(e) {
                    this.highlightToken(e.currentTarget);
                    e.preventDefault();
                };
                events['click .delete-action'] = function(e) {
                    this.model.controller.trigger("deleteEntity", this.model.entity);
                    e.preventDefault();
                };
                events['click .edit-action'] = function(e) {
                    this.model.controller.trigger("editEntity", this.model.entity);
                    e.preventDefault();
                };
                events['click .disable-action'] = function(e) {
                    this.model.controller.trigger('disableEntity', this.model.entity);
                    e.preventDefault();
                };
                events['click .enable-action'] = function(e) {
                    this.model.controller.trigger('enableEntity', this.model.entity);
                    e.preventDefault();
                };

                return events;
            })(),


            initialize: function (options) {
                BaseView.prototype.initialize.call(this, options);

                this.isStackmakr = splunkUtils.isStackmakr(this.model.dmcSettings.isEnabled(), this.model.serverInfo.isCloud());
                this.globallyDisabled = this.model.settings.get('ui.disabled') && !this.isStackmakr;

                this.listenTo(this.model.controller, "change:globalBlock", this.handleGlobalBlock);
            },

            highlightToken: function($cell) {
                var token = this.model.entity.entry.content.get('token'),
                    highlighted = _.template(this.highlightTemplate, {token: token});
                $($cell).html(highlighted);
                this.$('.token-highlight').focus().select();
                this.$('.token-highlight').blur(function() {
                    $($cell).text(token);
                });
            },

            controlActionsVisibility: function() {
                var canDelete = this.model.entity.canDelete(),
                    canEdit = this.model.entity.canEdit(),
                    canEnable = this.model.entity.canEnable(),
                    canDisable = this.model.entity.canDisable();

                if (this.model.serverInfo.isCloud() && !this.model.dmcSettings.isEnabled() && this.options.isCloudCluster) {
                    canDelete = false;
                    canEdit = false;
                    canEnable = false;
                    canDisable = false;
                }

                if (!canDelete) {
                    this.$el.find('.delete-action').replaceWith(function() {
                        return $('<span>').addClass('disabled-action').append($(this).contents());
                    });
                }
                if (!canEdit) {
                    this.$el.find('.edit-action').replaceWith(function() {
                        return $('<span>').addClass('disabled-action').append($(this).contents());
                    });
                }
                if (!canEnable || this.globallyDisabled) {
                    this.$el.find('.enable-action').replaceWith(function() {
                        return $('<span>').addClass('disabled-action').append($(this).contents());
                    });
                }
                if (!canDisable || this.globallyDisabled) {
                    this.$el.find('.disable-action').replaceWith(function() {
                        return $('<span>').addClass('disabled-action').append($(this).contents());
                    });
                }
            },

            handleGlobalBlock: function(model,enabled) {
                if (enabled) {
                    this.$el.find('a.entity-action').addClass('disabled-action');
                    this.$el.find('a.edit-action').addClass('disabled-action');
                } else {
                    this.$el.find('a.entity-action').removeClass('disabled-action');
                    this.$el.find('a.edit-action').removeClass('disabled-action');
                }
            },

            render: function () {
                var html = this.compiledTemplate({
                    globallyDisabled: this.globallyDisabled,
                    name: this.model.entity.getPrettyName(),
                    isDisabled: !this.model.entity.isEnabled(),
                    token: this.model.entity.entry.content.get("token"),
                    sourcetype: this.model.entity.entry.content.get("sourcetype"),
                    index: this.model.entity.entry.content.get("index") || _('Default').t(),
                    description: this.model.entity.entry.content.get("description")
                });

                this.$el.html(html);

                if (this.isStackmakr) {
                    this.handleGlobalBlock(null, this.model.controller.get('globalBlock'));
                }

                this.controlActionsVisibility();

                return this;
            },

            highlightTemplate: '<input class="token-highlight" type="text" readonly="readonly" value="<%- token %>"/>'

        });
    });

