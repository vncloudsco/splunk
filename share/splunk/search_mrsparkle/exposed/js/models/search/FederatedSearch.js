define(
    [
        'underscore',
        'models/search/Report'
    ],
    function(
        _,
        ReportModel
    ) {
        var Model = ReportModel.extend({
            initialize: function() {
                ReportModel.prototype.initialize.apply(this, arguments);
            },
        });
        Model.Entry = Model.Entry.extend({});
        Model.Entry.Content = Model.Entry.Content.extend({
            validation: _.extend({}, Model.Entry.Content.prototype.validation, {
                'federated.provider': {
                    fn: 'validateFederatedProvider'
                }
            }),
            validateFederatedProvider: function(value, attr, computedState) {
                if (!value) {
                    return _('Federated Provider field is required.').t();
                }
            }
        });
        return Model;
    }
);
