define(
    [
        'module',
        'jquery',
        'underscore',
        'backbone',
        'views/dashboard/Base',
        'views/shared/delegates/Popdown',
        'splunkjs/mvc/messages',
        'util/dashboard_utils',
        'splunk.util'
    ],
    function(module,
             $,
             _,
             Backbone,
             BaseDashboardView,
             PopdownView,
             Messages,
             DashboardUtils,
             SplunkUtil
         ) {
        return BaseDashboardView.extend({
            moduleId: module.id,
            initialize: function(options) {
                BaseDashboardView.prototype.initialize.apply(this, arguments);
                this.bindToComponentSetting('managerid', this.onManagerChange, this);
                this.model = _.extend({
                    primarySearchMessages: new Backbone.Model(),
                    secondarySearchMessages: new Backbone.Model()
                }, this.model);
                var debouncedRender = _.debounce(this.render);
                this.model.primarySearchMessages.on('change', debouncedRender, this);
                this.model.secondarySearchMessages.on('change', debouncedRender, this);
            },
            onManagerChange: function(managers) {
                // clean up listeners
                if (this.managers) {
                    _.each(this.managers, function(manager) {
                        this.stopListening(manager);
                    }, this);
                    this.managers = null;
                }
                if (managers) {
                    this.managers = managers;
                    _.each(this.managers, function(manager) {
                        if (manager.getType() === 'primary') {
                            this.primaryManager = manager;
                            if (this._shouldShowProgress()) {
                                this.model.primarySearchMessages.clear();
                            }
                            this.listenTo(manager, "search:progress search:done", this.onPrimarySearchProgress);
                        } else {
                            this.listenTo(manager, "search:start", _.partial(this.onSecondarySearchStart, manager));
                            this.listenTo(manager, "search:fail", _.partial(this.onSecondarySearchFail, manager));
                            this.listenTo(manager, "search:error", _.partial(this.onSecondarySearchError, manager));
                            this.listenTo(manager, 'search:cancelled', _.partial(this.onSecondarySearchCancelled, manager));
                        }
                        manager.replayLastSearchEvent(this);
                    }, this);
                }
            },
            onSecondarySearchStart: function(manager, state) {
                this.model.secondarySearchMessages.unset(manager.id);
            },
            onSecondarySearchCancelled: function(manager, state) {
                this.onSecondarySearchStart(manager, state);
            },
            onSecondarySearchError: function(manager, message, err) {
                var msg = Messages.getSearchErrorMessage(err) || message;
                msg = SplunkUtil.sprintf('[%s] %s', manager.getType(), msg);
                DashboardUtils.updateSearchMessage(this.model.secondarySearchMessages, manager.id, 'error', msg, {
                    reset: true
                });
            },
            onSecondarySearchFail: function(manager, state) {
                var msg = Messages.getSearchFailureMessage(state);
                msg = SplunkUtil.sprintf('[%s] %s', manager.getType(), msg);
                DashboardUtils.updateSearchMessage(this.model.secondarySearchMessages, manager.id, 'error', msg, {
                    reset: true
                });
            },
            onPrimarySearchProgress: function(properties) {
                var content = properties.content || {};

                // Pass this progress event if we are not showing progress and
                // the job is not done.
                if (!this._shouldShowProgress() && !content.isDone) {
                    return;
                }

                if (content.messages) {
                    var errMsgs = _(content.messages).chain().where({ 'type': 'ERROR' }).pluck('text').value();
                    var warnMsgs = _(content.messages).chain().where({ 'type': 'WARN' }).pluck('text').value();
                    this.model.primarySearchMessages.set('errors', errMsgs, { unset: _.isEmpty(errMsgs) });
                    this.model.primarySearchMessages.set('warnings', warnMsgs, { unset: _.isEmpty(warnMsgs) });
                }
            },
            getMessages: function() {
                var messages = {
                    errors: this.model.primarySearchMessages.get('errors') || [],
                    warnings: this.model.primarySearchMessages.get('warnings') || []
                };
                _.chain(this.model.secondarySearchMessages.toJSON()).values().each(function(msg) {
                    messages.errors = messages.errors.concat(msg.errors || []);
                    messages.warnings = messages.warnings.concat(msg.warnings || []);
                });
                return messages;
            },
            render: function() {
                var messages = this.getMessages();
                if (messages.errors.length > 0 || messages.warnings.length > 0) {
                    if (!this.$error) {
                        this.$error = $('<div class="error-details">' +
                                        '<a href="#" class="dropdown-toggle error-indicator"><i class="icon-warning-sign"></i></a>' +
                                        '<div class="dropdown-menu"><div class="arrow"></div>' +
                                            '<ul class="first-group error-list">' +
                                            '</ul>' +
                                        '</div>' +
                                        '</div>').appendTo(this.$el);
                    }
                    this.$error.find('.error-list').html(this.errorStatusTemplate(_.extend({ _:_, errors: null, warnings: null }, messages)));
                    this.children.errorPopdown = new PopdownView({ el: this.$error });
                    this.$error[messages.errors && messages.errors.length > 0 ? 'addClass' : 'removeClass']('severe');
                } else {
                    if (this.$error) {
                        this.$error.remove();
                        this.$error = null;
                    }
                    if (this.children.errorPopdown) {
                        this.children.errorPopdown.remove();
                    }
                }
                return this;
            },
            _shouldShowProgress: function() {
                var refreshDisplay = this.model.report.entry.content.get('dashboard.element.refresh.display');
                return refreshDisplay === 'none' ? !this.primaryManager.isRefresh() : true;
            },
            remove: function() {
                _(this.children).invoke('remove');
                _(this.model).invoke('off');
                return BaseDashboardView.prototype.remove.call(this);
            },
            errorStatusTemplate: _.template(
                    '<% _(errors).each(function(error){ %>' +
                        '<li class="error"><i class="icon-warning-sign"></i> <%- error %></li>' +
                    '<% }); %>' +
                    '<% _(warnings).each(function(warn){ %>' +
                        '<li class="warning"><i class="icon-warning-sign"></i> <%- warn %></li>' +
                    '<% }); %>')
        });
    }
);
