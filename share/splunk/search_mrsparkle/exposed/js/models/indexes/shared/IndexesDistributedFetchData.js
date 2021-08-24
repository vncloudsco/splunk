define([
        'underscore',
        'models/shared/fetchdata/EAIFetchData'
    ],
    function(
        _,
        EAIFetchData
    ) {
        return EAIFetchData.extend({
            toJSON: function(options) {
                var json = EAIFetchData.prototype.toJSON.apply(this, arguments);
                var search = [];
                search.push("| eventcount");
                search.push("summarize=false");
                if (json.hasOwnProperty("searchFilterString")) {
                    search.push(json.searchFilterString);
                }
                else {
                    search.push("index=*");
                }
                search.push("| dedup index");
                search.push("| rename index as name");
                search.push("| fields name");
                json.search = search.join(" ");
                return json;
            }
        });
    });
