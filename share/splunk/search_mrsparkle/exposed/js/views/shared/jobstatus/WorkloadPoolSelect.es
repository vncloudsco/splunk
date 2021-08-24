import _ from 'underscore';
import SyntheticSelectControl from 'views/shared/controls/SyntheticSelectControl';
import './WorkloadPoolSelect.pcss';

export default SyntheticSelectControl.extend({
    className: 'pull-left',
    moduleId: module.id,
    initialize(options = {}) {
        // eslint allows no params re-assignment, so copy params to a new var
        const extendedOptions = Object.assign(options, {
            items: options.workloadManagementStatus.getDropdownOptions(true),
            modelAttribute: 'workload_pool',
            menuWidth: 'narrow',
            toggleClassName: 'btn-pill dropdown-toggle-workload-pool',
            menuClassName: 'dropdown-menu-workload-pool',
            iconClassName: 'link-icon',
        });
        // different than other search properties, default value of workload pool is created by users.
        // there is no hard-coded value for default.
        // here, a brand new search, should have the default pool selected in the dropdown
        if (_.isUndefined(extendedOptions.model.get('workload_pool'))) {
            extendedOptions.model.set(
                'workload_pool',
                extendedOptions.workloadManagementStatus.getDefaultSearchPoolName(),
            );
        }
        SyntheticSelectControl.prototype.initialize.call(this, extendedOptions);
    },
});
