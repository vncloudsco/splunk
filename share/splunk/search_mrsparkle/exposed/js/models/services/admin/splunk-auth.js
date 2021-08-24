define(
    [
        'underscore',
        'models/SplunkDBase'
    ],
    function(
        _,
        BaseModel
    ) {
        var SplunkAuthModel = BaseModel.extend({
            url: 'admin/Splunk-auth/',
            urlRoot: 'admin/Splunk-auth/',

            initialize: function() {
                BaseModel.prototype.initialize.apply(this, arguments);
            },
            // have same checks in backend code; need to make sure they are consistent
            validatePassword: function(value) {
                var validationResults = {
                    passLengthReq: (value.length >= this.entry.content.get('minPasswordLength')),
                    passDigitReq: (value.replace(/[^0-9]/g,"").length >= this.entry.content.get('minPasswordDigit')),
                    passLowercaseReq: (value.replace(/[^a-z]/g, "").length >= this.entry.content.get('minPasswordLowercase')),
                    passUppercaseReq: (value.replace(/[^A-Z]/g, "").length >= this.entry.content.get('minPasswordUppercase')),
                    passSpecialReq: (value.replace(/[^!-/:-@\[-`{-~]/g, "").length >= this.entry.content.get('minPasswordSpecial'))
                };
                return validationResults;
            }
        });

        SplunkAuthModel.Entry = BaseModel.Entry.extend({});

        // Hard coded max values need to stay consistent with those in src/framework/auth/SplunkAuthConfig.cpp 
        SplunkAuthModel.Entry.Content = BaseModel.Entry.Content.extend({
            validation: {
                minPasswordLength:  {
                    range: [1, 256],
                    pattern: 'digits',
                    msg: _("Minimum characters must be a number between 1 and 256").t()
                },
                minPasswordDigit:  {
                    range: [0, 256],
                    pattern: 'digits',
                    msg: _("Numeral must be a number between 0 and 256").t()
                },
                minPasswordLowercase:  {
                    range: [0, 256],
                    pattern: 'digits',
                    msg: _("Lowercase must be a number between 0 and 256").t()
                },
                minPasswordUppercase:  {
                    range: [0, 256],
                    pattern: 'digits',
                    msg: _("Uppercase must be a number between 0 and 256").t()
                },
                minPasswordSpecial:  {
                    range: [0, 256],
                    pattern: 'digits',
                    msg: _("Special character must be a number between 0 and 256").t()
                },
                expirePasswordDays: {
                    range: [0, 3650],
                    pattern: 'digits',
                    msg: _("Days until password expires must be a number between 0 and 3650").t()
                }, 
                expireAlertDays: {
                    range: [0, 120],
                    pattern: 'digits',
                    msg: _("Expiration alert in days must be a number between 0 and 120").t()
                },
                lockoutAttempts: {
                    range: [1, 64],
                    pattern: 'digits',
                    msg: _("Lockout attempts must be a number between 1 and 64").t()
                },
                lockoutThresholdMins: {
                    range: [1, 120],
                    pattern: 'digits',
                    msg: _("Lockout threshold in minutes must be a number between 1 and 120").t()
                },
                lockoutMins: {
                    range: [1, 1440],
                    pattern: 'digits',
                    msg: _("Lockout duration in minutes must be a number between 1 and 1440").t()
                },
                passwordHistoryCount: {
                    range: [1, 128],
                    pattern: 'digits',
                    msg: _("Password history count must be a number between 1 and 128").t()
                },
                constantLoginTime: {
                    range: [0.000,5.000],
                    pattern: 'number',
                    msg: _("Login time must be a number between 0 and 5").t()
                }
            }
        });
        return SplunkAuthModel;
    }
);
