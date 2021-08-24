define(['underscore', 'models/SplunkDBase'], function(_, SplunkDBaseModel) {
    var Model = SplunkDBaseModel.extend({
        url: 'storage/fshpasswords',
    });

    Model.Entry = Model.Entry.extend({});
    Model.Entry.Content = Model.Entry.Content.extend({
        validation: _.extend({}, Model.Entry.Content.prototype.validation, {
            provider: {
                fn: 'formatProvider',
            },
            password: {
                fn: 'nonEmpty',
            },
            name: {
                fn: 'formatName',
            },
        }),
        formatProvider: function(value) {
            var trimmedValue = value && value.trim();
            if (trimmedValue) {
                this.set('provider', trimmedValue);
            }
        },
        nonEmpty: function(value) {
            if (!value) {
                return _('Password field should not be empty.').t();
            }
        },
        formatName:  function(value) {
            var trimmedValue = value && value.trim();
            if (trimmedValue) {
                this.set('name', trimmedValue);
            }
        },
    });

    return Model;
});
