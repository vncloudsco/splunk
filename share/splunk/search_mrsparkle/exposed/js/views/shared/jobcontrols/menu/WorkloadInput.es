import _ from 'underscore';
import BaseView from 'views/Base';
import ControlGroup from 'views/shared/controls/ControlGroup';

export default BaseView.extend({
    /**
    * @param {Object} options {
        // reports, job activity, data model use workload_pool
        // report acceleration uses auto_summarize.workload_pool
    *    workloadPoolAttribute: 'workload_pool' || 'auto_summarize.workload_pool',
    *    isRunning: this.model.inmem.isRunning(),
    *    model: {
    *        user: <models.shared.User>
    *        inmem: <models.search.Job> // When report model is passed in isRunning method is undefined
             // data model uses entry.content.acceleration
             // everything else uses entry.content
    *        workloadPool: this.model.inmem.entry.content ||  this.model.inmem.entry.content.acceleration
    *    },
    *    collection: {
    *        workloadManagementStatus: <collections.services.admin.workload_management>
    *    },
    */
    moduleId: module.id,
    initialize(options = {}) {
        BaseView.prototype.initialize.call(this, options);

        if (!this.options.isRunning) {
            this.helpText = _('You can only select a workload pool for running jobs.').t();
        } else {
            this.helpText = _('Select a workload pool to allocate resources.').t();
        }
        // reset to empty value if pool doesn't exist
        if (this.model.user.canListAndSelectWorkloadPools(this.collection.workloadManagementStatus) &&
            !this.collection.workloadManagementStatus.poolIdExists(
            this.model.workloadPool.get(this.options.workloadPoolAttribute),
            )) {
            this.model.workloadPool.set(this.options.workloadPoolAttribute, '');
        }
        this.children.workloadPool = new ControlGroup({
            label: _('Workload Pool').t(),
            help: this.helpText || '',
            controlClass: 'input-append',
            controls: [{
                type: 'SyntheticSelect',
                options: {
                    modelAttribute: this.options.workloadPoolAttribute,
                    model: this.model.workloadPool,
                    items: this.collection.workloadManagementStatus.getDropdownOptions(this.options.includeEmptyOption),
                    toggleClassName: 'btn',
                    popdownOptions: { attachDialogTo: 'body' },
                },
            }],
        });
    },
    render() {
        if (!this.el.innerHTML) {
            this.$el.html(this.compiledTemplate());
            this.children.workloadPool.render().appendTo(this.$('.workloadPool-placeholder'));

            if (!this.model.user.canListAndSelectWorkloadPools(this.collection.workloadManagementStatus)) {
                this.$('.workloadPool-placeholder').hide();
            } else if (!this.options.isRunning) {
                this.$('.workloadPool-placeholder .dropdown-toggle').addClass('disabled');
            }
        }
        return this;
    },
    template: `
        <div class='workloadPool-placeholder'></div>
    `,
});
