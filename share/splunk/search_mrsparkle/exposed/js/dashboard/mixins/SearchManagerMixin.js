define([
    'jquery',
    'underscore',
    'splunkjs/mvc'
], function($,
            _,
            mvc) {

    var SearchManagerMixin = {
        setupSearchManager: function(options) {
            options || (options = {});
            this.bindToComponentSetting(options.key || 'managerid', this.onSearchManagerChanged, this);
        },
        onSearchManagerChanged: function(managers, manager) {
            // should be implement by concrete module
        }
    };

    return SearchManagerMixin;
});