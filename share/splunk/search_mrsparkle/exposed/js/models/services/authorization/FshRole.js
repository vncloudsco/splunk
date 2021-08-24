define(['underscore', 'models/services/authorization/Role'], function(_, RoleModel) {
    return RoleModel.extend({
        addProvider: function(newProvider) {
            var trimedProvider = newProvider.trim();
            var existedProviders = this.entry.content.get('federatedProviders');
            var providers = typeof existedProviders === 'object' ? existedProviders.join(',') : existedProviders || '';
            if (providers.indexOf(trimedProvider) === -1) {
                var providersValue = providers ? providers + ',' + trimedProvider : trimedProvider;
                this.entry.content.set('federatedProviders', providersValue);
            }
        },

        removeProvider: function(provider) {
            var currentProviders = String(this.entry.content.get('federatedProviders'));
            if (currentProviders) {
                var providersArr = currentProviders.split(',');
                var removedProviders = _.difference(providersArr, provider);
                if (removedProviders.length < providersArr.length) {
                    this.entry.content.set('federatedProviders', removedProviders.join(','));
                    return true;
                }
            }
            return false;
        },
    });
});
