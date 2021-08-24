import _ from 'underscore';
import Grid from 'views/shared/basemanager/Grid';

export default Grid.extend({
    moduleId: module.id,

    initialize(...args) {
        Grid.prototype.initialize.apply(this, args);

        _.extend(this.options, {
            // this is required to toggle the row expansion if
            // row was previously expanded before re-render
            tableRowToggle: this.children.tableRowToggle,
        });
    },
});
