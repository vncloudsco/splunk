/**
 * Created by claral on 6/6/16.
 */
define(
[
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'views/monitoringconsole/splunk_health_check/Results',
    'views/monitoringconsole/splunk_health_check/TaskInfo',
    'contrib/text!views/monitoringconsole/splunk_health_check/Sidebar.html',
    'views/monitoringconsole/splunk_health_check/Sidebar.pcss'
], function(
    $,
    _,
    module,
    BaseView,
    ResultsView,
    TaskInfoView,
    Template,
    css
) {
    return BaseView.extend({
        moduleId: module.id,
        template: Template,
        className: 'sidebar',
        events: {
            'click .close': function(e) {
                this.trigger('hideResultsSidebar');
                e.preventDefault();
            }
        },

        setTask: function(task) {
            this.model.task = task;
        },

        render: function() {
            var title = '';
            if (this.model.task) {
                title = this.model.task.getTitle();
            }

            this.$el.html(this.compiledTemplate({
                title: title
            }));

            if (this.model.task) {
                if (this.children.taskInfo && this.children.results) {
                    this.children.taskInfo.detach();
                    this.children.results.detach();
                }

                this.children.taskInfo = new TaskInfoView({
                    model: this.model
                });
                this.$('.task-info-section').append(this.children.taskInfo.render().$el);

                if (this.model.task.isDone()) {
                    this.children.results = new ResultsView({
                        model: this.model,
                        showExpand: true
                    });
                    this.$('.task-info-results').append(this.children.results.render().$el);
                }
             }
            return this;
        }
    });
});