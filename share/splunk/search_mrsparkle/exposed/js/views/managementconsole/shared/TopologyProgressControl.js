
define(
    [
        'jquery',
        'underscore',
        'backbone',
        'module',
        'models/Base',
        'views/Base',
        'views/managementconsole/shared/TaskProgressDialog',
        './TopologyProgressControl.pcss'

    ],
    function(
        $,
        _,
        Backbone,
        module,
        BaseModel,
        BaseView,
        TaskProgressDialog,
        css
    ) {
        var STRINGS = {
            PROGRESS_MESSAGE: _('Updating deployment').t(),
            PROGRESS: _('Operation in progress').t(),
            LAST_UPDATE_STATUS: _('Last Deployment Status').t(),
            STATUS: _('Status').t()
        };

        var PROGRESS_BAR_DELAY = 1000;

        return BaseView.extend({
            moduleId: module.id,
            className: 'progress-control',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.onDeployTaskSuccessCB = this.options.onDeployTaskSuccessCB;

                // listen to newTask event from the task model
                this.listenTo(this.model.topologyTask, 'newTask', this.handleProgressButtonState);
                // listen to sync so that the progress can be shown
                this.listenTo(this.model.topologyTask, 'sync', this._taskSync);
            },

            events: {
                'click .task-progress.disabled': '_taskProgressDisabled',
                'click .task-progress.enabled': 'showProgressWindow'
            },

            render: function() {
                this.$el.html(this.compiledTemplate({
                    strings: STRINGS,
                    message: ''
                }));

                this.handleProgressButtonState();

                this.showStatusIcon(this.model.topologyTask.entry.content.get('state'));

                return this;
            },

            /**
             * @private
             * on sync update the progress bar. If the task failed or completed hide the progress bar
             */
            _taskSync: function() {
                var width = 0,
                    stages = this.model.topologyTask.entry.content.get('stages'),
                    count = 0;

                // In case there are no stages the progress bar should complete when the entire task is marked
                // as complete
                if (stages.length === 0) {
                    stages =  [this.model.topologyTask.entry.content.toJSON()];
                }

                _.each(stages, function(stage) {
                    if (stage.state === 'completed') {
                        count++;
                    }
                });

                width = Math.round((count/stages.length)*100);
                this.setProgress(width);

                var taskState = this.model.topologyTask.entry.content.get('state'),
                    runningStage = _.find(this.model.topologyTask.entry.content.get('stages'), function(stage) {
                    return stage.state === 'running';
                });

                if (width >= 100 || (taskState == 'completed' || taskState == 'failed')) {
                    _.delay(this.taskFinished.bind(this), PROGRESS_BAR_DELAY);
                } else {
                    this.hideStatusIcon();
                    this.showProgressBar();
                }
            },

            _taskProgressDisabled: function(e) {
                e.preventDefault();
            },

            // If no task exist then disable the progress button
            handleProgressButtonState: function() {
                if (this.model.topologyTask.entry.get('name')) {
                    this.$('.task-progress').removeClass('disabled').addClass('enabled');
                } else {
                    this.$('.task-progress').addClass('disabled').removeClass('enabled');
                }
            },

            taskFinished: function() {
                this.model.topologyTask.entry.unset('name');
                this.model.topologyTask.trigger('taskFinished');
                var taskState = this.model.topologyTask.entry.content.get('state');
                this.showStatusIcon(taskState);
                this.hideProgressBar();
            },

            hideProgressBar: function() {
                this.$('.progress-bar ').parent().hide();
                this.resetProgress();
                this.updateProgressString(STRINGS.LAST_UPDATE_STATUS);
            },

            showProgressBar: function() {
                this.updateProgressString(STRINGS.PROGRESS);
                this.$('.progress-bar ').parent().show();
            },

            updateProgressString: function(str) {
                this.$('.progress-string').html(str);
            },

            // sets the width of the progress bar
            setProgress : function(width) {
                if (width !== null && width === 0 ) {
                    width = 10;
                }
                this.$('.progress-bar ').width(width+'%');
            },

            showStatusIcon: function(status) {
                this.$('.status-icon').show();
                this.$('.status-icon').removeClass('icon-check-circle icon-positive icon-error icon-negative');
                if (status === 'completed') {
                    this.$('.status-icon').addClass('icon-check-circle icon-positive');
                } else if (status === 'failed'){
                    this.$('.status-icon').addClass('icon-error icon-negative');
                }
            },

            hideStatusIcon: function() {
                this.$('.status-icon').hide();
            },

            resetProgress: function() {
                this.setProgress(0);
            },

            /**
             * Show the progress window
             */
            showProgressWindow: function(e) {
                e.preventDefault();
                var dialog = new TaskProgressDialog({
                    model: {
                        task: this.model.topologyTask,
                        user: this.model.user
                    },
                    onHiddenRemove: true,
                    onDeployTaskSuccessCB: this.onDeployTaskSuccessCB
                });
                $('body').append(dialog.render().el);
                dialog.show();
            },

            template: '\
                <a href="#" class="btn-pill task-progress disabled pull-left">\
                    <span class="progress-string"><%- strings.LAST_UPDATE_STATUS %></span>\
                </a>\
                <div class="status-icon-section pull-left">\
                    <i class="status-icon icon-check-circle icon-positive"></i>\
                </div>\
                <div class="deployment-progress-bar pull-left">\
                    <div class="progress deployment-management-progress-bar " >\
                        <div class="progress-bar progress-striped active">\
                            <%- message %>\
                        </div>\
                    </div>\
                </div>\
            '
        });
    }
);
