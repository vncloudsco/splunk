/**
 * Created by lrong on 11/3/15.
 */
define(
    [
        'jquery',
        'underscore',
        'backbone',
        'module',
        'models/managementconsole/Task',
        'views/shared/Modal',
        'views/managementconsole/shared/TaskDeployRetryDialog',
        'util/time'
    ],
    function(
        $,
        _,
        Backbone,
        module,
        TaskModel,
        Modal,
        TaskDeployRetryDialog,
        time_utils
    ) {
        var STATUS_SYMBOL_CLASSES = {
            "new": 'icon-star icon-neutral',
            "running": 'icon-gear icon-neutral',
            "completed": 'icon-check-circle icon-positive',
            "failed": 'icon-error icon-negative'
        };

        var STRINGS = {
            STATUS: _('Status').t(),
            TASK_ID: _('Deployment Task ID').t(),
            TASK_TIME_STAMP: _('Deployment Timestamp').t(),
            TASK_FAILED_MESSAGE: _('Your latest app deployment failed. Contact Splunk Support with a screenshot of this dialog for further assistance.').t()
        };


        var MODAL_CLOSE_BTN = '<a href="#" class="btn modal-btn-primary pull-left" data-dismiss="modal">' + _('Close').t() + '</a>';
        var MODAL_RETRY_BTN = '<a href="#" class="btn btn-primary modal-btn-primary retry-deploy" data-dismiss="modal">' + _('Retry').t() + '</a>';

        return Modal.extend({
            moduleId: module.id,
            className: [Modal.CLASS_NAME, 'task-progress-dialog'].join(' '),

            initialize: function(options) {
                Modal.prototype.initialize.apply(this, arguments);

                this.onDeployTaskSuccessCB = this.options.onDeployTaskSuccessCB;

                this.listenTo(this.model.task, 'sync', this.debouncedRender);
            },

            events: $.extend({}, Modal.prototype.events, {
                'click .retry-deploy': function(e) {
                    e.preventDefault();

                    var taskDeployRetryDialog = new TaskDeployRetryDialog({
                        model: {
                            task: this.model.task
                        },
                        onDeployTaskSuccessCB: this.onDeployTaskSuccessCB
                    });
                    this.$('body').append(taskDeployRetryDialog.render().el);
                    taskDeployRetryDialog.show();
                }
            }),

            render: function() {
                this.$el.html(Modal.TEMPLATE);
                this.$(Modal.HEADER_TITLE_SELECTOR).text(_('Last Deployment Status').t());
                this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);
                this._renderContent();
                this.$(Modal.FOOTER_SELECTOR).append(MODAL_CLOSE_BTN);

                if (this.model.task.isFailed() && this.model.user.hasCapability('dmc_deploy_apps')) {
                    this.$(Modal.FOOTER_SELECTOR).append(MODAL_RETRY_BTN);
                }

                return this;
            },

            convertDateFormat: function(utcTimeSeconds) {
                return time_utils.convertToLocalTime(utcTimeSeconds);
            },

            _renderContent: function () {
                this.$(Modal.BODY_FORM_SELECTOR).html(this.compiledTemplate({
                    STRINGS: STRINGS,
                    taskFailed: this.model.task.isFailed(),
                    statusSymbol: STATUS_SYMBOL_CLASSES[this.model.task.entry.content.get('state')],
                    statusLabel: this.model.task.getStatus(),
                    taskId: this.model.task.getTaskId(),
                    timeStamp: this.model.task.getTimeStamp()
                }));
            },

            template: '\
                <p>\
                    <div class="task-info-header ">\
                        <% if (taskFailed) { %>\
                            <p class="help-message"><i class="status-icon icon-warning icon-neutral"></i> <%- STRINGS.TASK_FAILED_MESSAGE %></p><br>\
                        <% } %>\
                        <h4><span><%- STRINGS.STATUS%></span>: <span><%- statusLabel %> <i class="status-icon <%- statusSymbol %>"></i></span></h4>\
                        <span><%- STRINGS.TASK_ID%></span>: <span><%- taskId %></span><br>\
                        <span><%- STRINGS.TASK_TIME_STAMP%>: </span><span><%- timeStamp %></span>\
                    </div>\
                </p>\
            '
        });
    }
);
