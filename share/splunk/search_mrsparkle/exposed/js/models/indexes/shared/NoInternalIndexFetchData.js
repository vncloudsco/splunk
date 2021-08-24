/**
 * @author jszeto
 * @date 2/12/15
 *
 * FetchData to use for Indexes. Currently we have to pass in a search substring to filter out any indexes that
 * are virtual indexes.
 */
define([
        'underscore',
        'models/shared/EAIFilterFetchData',
        'util/splunkd_utils'
    ],
    function(
        _,
        EAIFilterFetchData,
        splunkdUtils
    ) {

        return EAIFilterFetchData.extend({

            getCalculatedSearch: function() {
                var searchString = EAIFilterFetchData.prototype.getCalculatedSearch.apply(this, arguments);

                var nameFilter = this.get('nameFilter');
                if(!_.isUndefined(nameFilter) && !_.isEmpty(nameFilter)){
                    searchString += ' AND ' + splunkdUtils.createSearchFilterString(nameFilter, ['name'], {});
                }

                if (searchString == "")
                    searchString = "isVirtual=0";
                else
                    searchString += " AND isVirtual=0";

                searchString += " AND isInternal=0";

                return searchString;
            }

        });

    });