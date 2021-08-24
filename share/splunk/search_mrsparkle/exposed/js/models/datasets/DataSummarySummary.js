define([
        'underscore',
        'models/services/search/jobs/Summary',
        'util/math_utils'
    ],
    function(
        _,
        SummaryModel,
        mathUtil
    ) {
        return SummaryModel.extend({
            initialize: function() {
                SummaryModel.prototype.initialize.call(this, arguments);
            },

            extractTopResults: function(columnName) {
                var fieldSummary = this.fields.get(columnName);
                if (fieldSummary) {
                    var totalCount = fieldSummary.get('count'),
                        results = fieldSummary.get('modes'),
                        parsedResults,
                        count,
                        name,
                        percentage;

                    parsedResults = _.map(results, function(result) {
                        count = result.count;
                        name = result.value;
                        percentage = mathUtil.convertToTwoDecimalPercentage(count, totalCount);

                        return {
                            name: name,
                            percentage: percentage
                        };
                    }, this);

                    return parsedResults;
                } else {
                    return [];
                }
            }
        });

    });
