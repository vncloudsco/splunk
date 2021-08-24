define(['underscore', './ItemState'], function(_, ItemState) {

    return ItemState.extend({
        setState: function(dashboardComponent) {
            ItemState.prototype.setState.call(this, {
                theme: dashboardComponent.settings.get('theme') || 'light',
                label: dashboardComponent.settings.get('label'),
                description: dashboardComponent.settings.get('description'),
                evtmanagerid: dashboardComponent.settings.get('evtmanagerid')
            });
        }
    });

});
