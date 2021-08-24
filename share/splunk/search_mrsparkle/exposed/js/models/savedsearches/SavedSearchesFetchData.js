/**
 * @author claral
 * @date 10/31/2016
 *
 * FetchData to use for saved searches page.
 * Adding an itemType filter to the search string to allow filtering to only reports/alerts.
 */
define([
        'underscore',
        'models/shared/EAIFilterFetchData',
        'collections/search/Reports',
        'util/splunkd_utils'
    ],
    function(
        _,
        EAIFilterFetchData,
        ReportsCollection,
        splunkdUtils
    ) {

        return EAIFilterFetchData.extend({

            getCalculatedSearch: function() {
                var searchString = EAIFilterFetchData.prototype.getCalculatedSearch.apply(this, arguments);

                var itemType = this.get('itemType');
                if (itemType) {
                    if (!_.isEmpty(searchString)) {
                        searchString += ' AND ';
                    }
                    if (itemType === 'alerts') {
                        searchString += '(' + ReportsCollection.ALERT_SEARCH_STRING + ')';
                    } else if (itemType === 'federated_searches') {
                        searchString += '(' + ReportsCollection.REMOTE_DATASET_SEARCH_STRING + ')';
                    } else {
                        searchString += 'NOT (' + ReportsCollection.ALERT_SEARCH_STRING + ') AND NOT (' + ReportsCollection.REMOTE_DATASET_SEARCH_STRING + ')';
                    }
                }

                var nameFilter = this.get('nameFilter');
                if(!_.isUndefined(nameFilter) && !_.isEmpty(nameFilter)){
                    searchString += ' AND ' + splunkdUtils.createSearchFilterString(nameFilter, ['name', 'description', 'search'], {});
                }

                return searchString;
            },

            toJSON: function(options) {
                var json = EAIFilterFetchData.prototype.toJSON.apply(this, arguments);

                delete json.itemType;

                return json;
            }

        });

    });
