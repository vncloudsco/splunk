define(
    [
        'jquery',
        'underscore',
        'backbone',
        'collections/services/data/ui/Views',
        'models/search/Dashboard'
    ],
    function ($, _, Backbone, ViewsCollection, DashboardModel) {
        return ViewsCollection.extend({
            model: DashboardModel,
            initialize: function () {
                ViewsCollection.prototype.initialize.apply(this, arguments);
            },
            sync: function (method, collection, options) {
                options = options || {};
                options.data = options.data || {};
                // the reason we have this fabulous long search is because we need to support different kinds of dashboard definition formats:
                // SimpleXML dashboard rootNode is <dashboard> or <form>
                // AdvancedXML dashbaord rootNode is <view isDashboard="true">
                // HTML dashboard rootNode is <html>
                // UDF dashboard rootNode is <dashboard version="2"> which we don't support as of Pinkie Pie release
                var baseSearch = '(isDashboard=1 AND ((rootNode="dashboard" AND version=1) OR rootNode="form" OR rootNode="view" OR rootNode="html") AND isVisible=1)';
                if (!options.data.search) {
                    options.data.search = baseSearch;
                } else {
                    options.data.search = '(' + baseSearch + ' AND ' + options.data.search + ')';
                }
                return ViewsCollection.prototype.sync.call(this, method, collection, options);
            },
            fetchSafe: function (options) {
                var defaults = {
                    data: {
                        sort_dir: 'asc',
                        sort_key: 'label',
                        sort_mode: 'natural',
                        count: 1000,
                        digest: '1'
                    }
                };

                $.extend(true, defaults, options || {});

                var eaiApp = defaults.data["eai:acl.app"] || '*';
                delete defaults.data["eai:acl.app"];

                var baseSearch = '(eai:acl.can_write="1" AND (NOT name="pdf_activity") AND eai:acl.app="' + eaiApp + '")';
                if (options && options.data && options.data.search) {
                    defaults.data.search = '(' + baseSearch + ' AND ' + options.data.search + ')';
                } else {
                    defaults.data.search = baseSearch;
                }
                return this.fetch(defaults);
            }
        });
    }
);
