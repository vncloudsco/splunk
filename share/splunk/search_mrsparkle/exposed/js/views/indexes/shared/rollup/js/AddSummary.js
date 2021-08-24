define(
[
    'jquery',
    'underscore',
    'module',
    'util/indexes/RollupUtils',
    'views/Base',
    'views/shared/Message',
    'views/indexes/shared/rollup/js/Summary',
    'views/indexes/shared/rollup/AddSummary.pcss'
],
function(
    $,
    _,
    module,
    RollupUtils,
    BaseView,
    Message,
    Summary,
    css
){
    return BaseView.extend( /** @lends views.AddSummary.prototype */ {
        moduleId: module.id,
        className: 'rollup-add-summary',
        /**
         * @constructor
         * @memberOf views
         * @name AddSummary
         * @extends {views.BaseView}
         * @description View for the summary section of the metric rollup general policy
         *
         * @param {Object} options
         * @param {Object} options.model The model supplied to this class
         * @param {Object} options.collection The collection supplied to this class
         */
        initialize: function(options) {
            BaseView.prototype.initialize.call(this, options);
            var numOfSummaries = this.model.rollup.get('tabs')[0].summaries.length;
            this.summaryElements = [];
            this.summaryId = numOfSummaries + 1;
            if (numOfSummaries < 1) {
                this.createSummaryModel();
            }
            this.children.duplicateSummariesError = new Message({
                fill: true,
                type: 'error',
                children: _("You cannot create rollup summaries with identical index and time period combinations.").t()
            });
            this.setAriaAttributes();
            this.startListening();
        },
        setAriaAttributes: function() {
            this.$el.attr({
                role: 'group',
                'aria-label': _('General policy add summary').t()
            });
        },
        startListening: function() {
            this.listenTo(this.model.rollup, 'change:tabs', this.render);
            this.listenTo(this.model.rollup, 'change:duplicateSummaryError', this.updateDuplicateErrorElement);
            this.listenTo(this.model.rollup, 'change:verifyTimeType', function() {
                this.model.rollup.set({'verifyTimeType': false}, {silent: true});
                this.updateDuplicateErrorElement();
            });
        },
        createSummaryModel: function() {
            var tabs = $.extend(true, [], this.model.rollup.get('tabs'));
            tabs[0].summaries.push({
                id: this.summaryId++,
                timeValue: '1',
                timeType: 'h',
                metricError: false,
                timeError: false
            });
            this.model.rollup.set('tabs', tabs, { silent: true });
        },
        createSummaryViews: function() {
            this.summaryElements = [];
            var tabs = this.model.rollup.get('tabs');
            if (!tabs.length) {
                return;
            }
            var summaries = tabs[0].summaries;
            for (var i = 0; i < summaries.length; i++) {
                var summaryModel = summaries[i];
                var summary = new Summary({
                    model: {
                        rollup: this.model.rollup,
                    },
                    collection: {
                        indexes: this.collection.indexes
                    },
                    dataTestIndex: i,
                    canRemove: summaries.length > 1,
                    id: summaryModel.id,
                    timeValue: summaryModel.timeValue,
                    timeType: summaryModel.timeType,
                    metricError: summaryModel.metricError,
                    timeError: summaryModel.timeError
                });
                this.summaryElements = this.summaryElements.concat(summary);
            }
        },
        events: {
            'click .add-summary-link': function(e) {
                this.createSummaryModel();
                this.render();
            }
        },
        updateDuplicateErrorElement: function() {
            var summaries = this.model.rollup.get('tabs')[0].summaries;
            var duplicateSummaryError = RollupUtils.getDuplicateSummaryError(summaries);
            if (duplicateSummaryError) {
                this.$('.add-summary-duplicate-error').show();
                $(this.$el).scrollTop(0);
            } else {
                this.$('.add-summary-duplicate-error').hide();
            }
        },
        render: function() {
            if (!this.el.innerHTML) {
                var template = _.template(this.template, {
                    _: _
                });
                this.$el.html(template);
                this.$('.add-summary-duplicate-error').hide();
            }
            this.createSummaryViews();
            if (this.summaryElements && this.summaryElements.length) {
                this.$('.summaries').empty();
                for (var i = 0; i < this.summaryElements.length; i++) {
                    var summaryElement = this.summaryElements[i];
                    this.$('.summaries').append(summaryElement.render().el);
                }
            }
            this.$(".add-summary-duplicate-error").append(this.children.duplicateSummariesError.render().el);
            return this;
        },
        template: '\
                <div class="add-summary-duplicate-error"></div>\
                <div role="group" aria-label="<%- _("Summaries").t() %>" class="summaries"></div>\
                <a href="#" class="add-summary-link"><%- _("+ Add another summary").t() %></a>\
        '
    });
});
