define(['underscore', 'models/SplunkDBase'], function(_, SplunkDBaseModel) {
    var Model = SplunkDBaseModel.extend({
        url: 'dfs/federated',
        
        formatInputs: function(ipAddress) {
            var name = this.entry.content.get('name');
            var serviceAccount = this.entry.content.get('splunk.serviceAccount');
            var app = this.entry.content.get('splunk.app');

            if (ipAddress) {
                var splitedIp = ipAddress.trim().split(':');
                this.entry.content.set('ip', splitedIp[0]);
                this.entry.content.set('splunk.port', splitedIp[1]);
            }

            if (name) {
                this.entry.content.set('name', name.trim());
            }
            if (serviceAccount) {
                this.entry.content.set('splunk.serviceAccount', serviceAccount.trim());
            }

            if (!app) {
                // Default splunk app should be search
                this.entry.content.set('splunk.app', 'search');
            } else {
                this.entry.content.set('splunk.app', app.trim() || 'search');
            }

            this.entry.content.set('type', 'splunk');
        },
        
        generateContent: function() {
            return {
                name: this.entry.get('name'),
                ip: this.entry.content.get('ip') + ":" + this.entry.content.get('splunk.port'),
                username: this.entry.content.get('splunk.serviceAccount'),
                federation: this,
                roles: [],
                type: this.entry.content.get('type'),
            };
        },
    });

    Model.Entry = Model.Entry.extend({});
    Model.Entry.Content = Model.Entry.Content.extend({
        validation: _.extend({}, Model.Entry.Content.prototype.validation, {
            ip: {
                fn: 'validateIp',
            },
            'splunk.port': {
                fn: 'validatePort',
            },
            name: {
                fn: 'invalidName',
            },
            'splunk.serviceAccount': {
                fn: 'invalidName',
            },
        }),
        validateIp: function(value, attr) {
            if (!value) {
                return _('Invalid IP address').t();
            }

            if (
                !/^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/.test(
                    value
                )
            ) {
                return _('Invalid IP address').t();
            }
        },
        validatePort: function(value, attr) {
            if (!value) {
                return _('Invalid port').t();
            }
            if (!(!isNaN(value) && String(Number(value)) === value && Number(value) >= 0 && Number(value <= 65535))) {
                return _('Invalid port').t();
            }
        },
        invalidName: function(value) {
            if (!value) {
                return _('Federated Provider Name or Username field should not be empty.').t();
            } 
            
            if (!/^[a-zA-Z0-9-_ ]{1,}$/.test(value)) {
                return _('Federated Provider Name or Username can only contain letters, numbers, dashes, and underscores.').t();
            }
        },
    });

    return Model;
});
