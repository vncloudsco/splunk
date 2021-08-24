define(
    [
        'underscore',
        'models/services/authorization/FshRole',
        'collections/services/authorization/Roles'
    ],
    function(
        _,
        RoleModel,
        RolesCollection
    ) {
        return RolesCollection.extend({
            model: RoleModel,
            parse: function(response, options) {
                if (response && response.entry) {
                    response.entry = response.entry.filter(function(entry) {
                        var capabilities = entry.content.capabilities;
                        var importedCapabilities = entry.content.imported_capabilities;
                        var allCapabilities = _.union(capabilities, importedCapabilities);
                        var hasSearch = allCapabilities.indexOf('fsh_search') > -1;
                        var hasManage = allCapabilities.indexOf('fsh_manage') > -1;
                        if (options.fshSearchAndManage) {
                            return hasSearch && hasManage;
                        } else if (options.fshSearchOrManage) {
                            return hasSearch || hasManage;
                        } else if (options.fshSearch) {
                            return hasSearch;
                        } else if (options.fshManage) {
                            return hasManage;
                        }
                        return false;
                    });
                }
                return RolesCollection.prototype.parse.call(this, response);
            },
            getNameItems: function() {
                return this.map(function(model) {
                    var name = model.entry.get('name');
                    return {
                        label: name,
                        value: name,
                    };
                });
            },
            getRolesByProvider: function(provider) {
                return this.filter(function(model) {
                    var currentProviders = String(model.entry.content.get('federatedProviders'));
                    if (currentProviders) {
                        var providersArr = currentProviders.split(',');
                        return providersArr.indexOf(provider) > -1;
                    }
                    return false;
                });
            },
            addRolesToTable: function(table) {
                var rows = table.reduce(function(map, row) {
                    // eslint-disable-next-line no-param-reassign
                    map[row.name] = row;
                    return map;
                }, {});

                this.forEach(function(model) {
                    var providers = model.entry.content.get('federatedProviders');
                    String(providers).split(',').forEach(function(federation) {
                        if (rows[federation]) {
                            rows[federation].roles.push(model.entry.get('name'));
                        }
                    });
                });

                return rows;
            },
        });
    }
);