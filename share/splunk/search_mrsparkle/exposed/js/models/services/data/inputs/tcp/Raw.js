define(
    [
        'underscore',
        'models/services/data/inputs/BaseInputModel'
    ],
    function (
        _,
        BaseInputModel
    ) {
        return BaseInputModel.extend({
            url: "data/inputs/tcp/raw",
            checkInputExists: function() {
                var error = BaseInputModel.prototype.checkInputExists.apply(this);

                if (!error && this.get("ui.restrictToHost")) {
                    // Adding restrictToHost as part of the input name for existance check.
                    var name = this.get("ui.restrictToHost") + ":" + this.get('ui.name');
                    error = BaseInputModel.prototype.checkInputExists.call(this, name);
                }
                if (!error) {
                    return;
                }
                return _('Input with the same port number already exists.').t();
            },
            validation: {
                'ui.name': [
                    {
                        pattern: 'number',
                        msg: _('Port number is required').t(),
                        required: true
                    },
                    {
                        fn: 'checkInputExists'
                    }
                ],
                'ui.sourcetype': [
                    {
                        required: function() {
                            return (this.wizard.get('currentStep') === 'inputsettings') && (!this.get('ui.sourcetype'));
                        },
                        msg: _("Sourcetype value is required.").t()
                    }
                ],
                'ui.host': [
                    {
                        required: function() {
                            return (this.wizard.get('currentStep') === 'inputsettings') && (this.get('ui.connection_host') === 'none');
                        },
                        msg: _("Host value is required.").t()
                    }
                ]
            }
        });
    }
);