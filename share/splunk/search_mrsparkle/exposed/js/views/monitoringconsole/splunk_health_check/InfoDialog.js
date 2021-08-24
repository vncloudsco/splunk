/**
 * Created by claral on 6/29/16
 */

define([
    'jquery',
    'underscore',
    'backbone',
    'module',
    'views/monitoringconsole/splunk_health_check/Results',
    'views/monitoringconsole/splunk_health_check/TaskInfo',
    'views/shared/Modal',
    'views/monitoringconsole/splunk_health_check/InfoDialog.pcss'
],

    function(
        $,
        _,
        Backbone,
        module,
        ResultsView,
        TaskInfoView,
        Modal,
        css
        ) {

        return Modal.extend({
            moduleId: module.id,
            className: Modal.CLASS_NAME + ' info-dialog-modal modal-extra-wide',
            render: function() {
                var title = '';
                if (this.model.task) {
                    title = this.model.task.getTitle();
                }

                this.$el.html(Modal.TEMPLATE);
                this.$(Modal.HEADER_TITLE_SELECTOR).html(_.escape(title));
                this.$(Modal.BODY_SELECTOR).show();
                this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);

                if (this.model.task) {
                    this.children.taskInfo = new TaskInfoView({
                        model: this.model
                    });
                    this.$(Modal.BODY_FORM_SELECTOR).append(this.children.taskInfo.render().$el);

                    this.children.results = new ResultsView({
                        model: this.model,
                        showExpand: false
                    });
                    this.$(Modal.BODY_FORM_SELECTOR).append(this.children.results.render().$el);
                }

                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CLOSE);
                return this;
            }
        });
    });
