define(['underscore', './ItemState'], function(_, ItemState) {
    return ItemState.extend({
        idAttribute: 'id',
        setState: function(eventManager, options) {
            ItemState.prototype.setState.call(this, {
                events: eventManager.settings.get('events'),
                id: eventManager.id
            });
        }
    });
});