define(['underscore', 'models/SplunkDBase'], function(_, SplunkDBaseModel) {
    return SplunkDBaseModel.extend({
        url: 'authorization/roles',
        initialize: function() {
            SplunkDBaseModel.prototype.initialize.apply(this, arguments);
        },
    });
});
