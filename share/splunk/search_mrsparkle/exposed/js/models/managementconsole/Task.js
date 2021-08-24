/**
 * Created by lrong on 10/28/15.
 */
define(
    [
        'jquery',
        'underscore',
        'backbone',
        'models/managementconsole/DmcBase',
        'util/time'
    ],
    function(
        $,
        _,
        Backbone,
        DmcBaseModel,
        timeUtil
    ) {
        var TASK_STATE_LABELS = {
            "new": _('New').t(),
            "running": _('Running').t(),
            "completed": _('Completed').t(),
            "failed": _('Failed').t()
        };

        var STATES = {
            'new': 'new',
            'failed': 'failed',
            'completed': 'completed',
            'running': 'running'
        };

        var getLabelFromStatus = function(status) {
            return TASK_STATE_LABELS[status];
        };

        return DmcBaseModel.extend(
            {
                urlRoot: '/services/dmc/tasks',
                POLLING_DELAY: 1000,

                hasState: function() {
                    return !_.isUndefined(STATES[this.getState()]);
                },

                getState: function() {
                    return this.entry.content.get('state');
                },

                getTaskId: function() {
                    return this.entry.content.get('taskId');
                },

                getTimeStamp: function() {
                    return timeUtil.convertToLocalTime(this.entry.content.get('createdAt'));
                },

                getStatus: function() {
                    return TASK_STATE_LABELS[this.entry.content.get('state')];
                },

                isNewState: function() {
                    return this.getState() === STATES['new'];
                },

                isFailed: function() {
                    return this.getState() === STATES['failed'];
                },

                isCompleted: function() {
                    return this.getState() === STATES['completed'];
                },

                isRunning: function() {
                    return this.getState() === STATES['running'];
                },

                inProgress: function() {
                    var name = this.entry.get('name');
                    // must have a taskId and have a valid in progress state
                    return !!((name && this.hasState()) && !(this.isCompleted() || this.isFailed()));
                },

                beginPolling: function() {
                    var dfd = $.Deferred(),
                        firstPoll = true;
                    this.startPolling({
                        condition: function() {
                            // continue polling if status is not complete and
                            // has not failed
                            var continuePolling = firstPoll || this.inProgress();
                            firstPoll = false;
                            if (!continuePolling) {
                                // deploy task failed -> execute fail CB
                                if (this.isFailed()) {
                                    dfd.reject();
                                }
                                // deploy task completed -> execute success CB
                                dfd.resolve();
                            }
                            return continuePolling;
                        }.bind(this),
                        delay: this.POLLING_DELAY
                    });
                    return dfd;
                },

                getConfirmation: function() {
                    return $.get(this.url() + '/confirmation');
                },

                postConfirmation: function(confirmationId, choice, input) {
                    var url = this.url() + '/confirmation/' + confirmationId + '/result',
                        data = choice === 'canceled' ? {canceled: true} : {choice: choice};

                    if(input) {
                        data.input = input;
                    }

                    return $.ajax({
                        type: 'POST',
                        url: url,
                        data: JSON.stringify(data),
                        contentType: 'application/json'
                    });
                }
             },
            {
                getLabelFromStatus: getLabelFromStatus
            }
        );
    }
);
