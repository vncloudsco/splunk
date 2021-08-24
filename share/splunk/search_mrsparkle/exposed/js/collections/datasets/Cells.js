define(
    [
        'underscore',
        'collections/Base',
        'models/datasets/Cell'
    ],
    function (
        _,
        BaseCollection,
        CellModel
    ) {
        return BaseCollection.extend({
            model: CellModel,

            initialize: function() {
                BaseCollection.prototype.initialize.apply(this, arguments);
            },

            // Add a cell to the collection, by default using the comparator.
            // Unlike the Columns collection's addColumn, there's not a significant benefit to calling this
            // over Backbone's native add - it's really just for the sorting. Data summary needs this.
            addCell: function(values, options) {
                options = options || {};

                _.defaults(options, {
                    useComparator: true,
                    deleteComparator: true
                });

                var addedCell;

                if (options.useComparator) {
                    this.useComparator({
                        comparator: options.comparator
                    });
                }

                addedCell = this.add(values);

                if (options.deleteComparator) {
                    this.deleteComparator();
                }

                return addedCell;
            },

            // Enables the comparator for addition or sorting. Can pass your own comparator if you don't want the default.
            useComparator: function(options) {
                options = options || {};

                if (options.comparator) {
                    this.comparator = options.comparator;
                } else {
                    this.comparator = this.defaultComparator;
                }
            },

            deleteComparator: function() {
                delete this.comparator;
            },

            // Cell sorting is mostly relevant for data summary, where cells are top values.
            // Cells are sorted first by group - null, mismatched, matched. Then by percentage, high to low.
            defaultComparator: function(cellOne, cellTwo) {
                var cellOneIsMismatched = !!cellOne.getTypeMismatchMessage(),
                    cellTwoIsMismatched = !!cellTwo.getTypeMismatchMessage(),
                    cellOneIsNull = cellOne.isNull(),
                    cellTwoIsNull = cellTwo.isNull(),
                    cellOnePercentage = cellOne.getScaledPercentage(),
                    cellTwoPercentage = cellTwo.getScaledPercentage();

                if (cellOneIsNull) {
                    if (cellTwoIsNull) {
                        return cellOnePercentage < cellTwoPercentage ? 1 : -1;
                    } else {
                        return -1;
                    }
                } else if (cellOneIsMismatched) {
                    if (cellTwoIsNull) {
                        return 1;
                    } else if (cellTwoIsMismatched) {
                        return cellOnePercentage < cellTwoPercentage ? 1 : -1;
                    } else {
                        return -1;
                    }
                } else {
                    // NOTE: A cell that isNull will also report false for isMismatched, so it's important to check
                    // the null-ness first always.
                    if (cellTwoIsNull || cellTwoIsMismatched) {
                        return 1;
                    } else {
                        return cellOnePercentage < cellTwoPercentage ? 1 : -1;
                    }
                }
            },

            sync: function(method, model, options) {
                throw new Error('sync not allowed for the Cell collection');
            }
        });
    }
);
