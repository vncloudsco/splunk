define(
[
    'jquery',
    'underscore',
    'module',
    'util/indexes/RollupUtils',
    'util/indexes/TimeConfigUtils',
    'views/Base',
    'views/shared/controls/SyntheticSelectControl',
    'views/indexes/shared/rollup/js/Select',
    'views/shared/controls/TextControl',
    'views/indexes/shared/rollup/js/CloseButton',
    'views/indexes/shared/rollup/Summary.pcss'
],
function(
    $,
    _,
    module,
    RollupUtils,
    TimeConfigUtils,
    BaseView,
    SyntheticSelectControl,
    Select,
    TextControl,
    CloseButton,
    css
){
    return BaseView.extend( /** @lends views.Summary.prototype */ {
        moduleId: module.id,
        className: 'rollup-summary',
        /**
         * @constructor
         * @memberOf views
         * @name Summary
         * @extends {views.BaseView}
         * @description Generic view for creating metric fields
         *
         * @param {Object} options
         * @param {Object} options.model The model supplied to this class
         * @param {Object} options.collection The collection supplied to this class
         * @param {Number} options.dataTestIndex The index of the summary for summary elements
         * @param {Number} options.id The id of the specific summary
         * @param {Boolean} options.canRemove Whether or not the summary is able to be removed
         */
        initialize: function(options) {
            BaseView.prototype.initialize.call(this, options);
            this.summary = this.getSummaryById(options.id);
            this.summary.timeError = TimeConfigUtils.getTimeErrorForSummary({
                minSpanAllowed: this.model.rollup.get('minSpanAllowed'),
                timeType: this.summary.timeType,
                timeValue: this.summary.timeValue
            });

            this.children.indexesDropdown = new Select({
                className: 'index-select',
                model: {
                    rollup: this.model.rollup
                },
                filter: true,
                inline: true,
                defaultValue: this.summary.targetIndex,
                placeholder: _('Select Index').t(),
                error: this.summary.metricError,
                onChange: this.handleChangedIndex.bind(this),
                items: this.collection.indexes.getItems(),
                menuWidth: 250,
                style: {
                    width: '170px'
                }
            });

            this.children.timeValueSelect = new Select({
                className: 'time-value-select',
                model: {
                    rollup: this.model.rollup
                },
                inline: true,
                defaultValue: Number(this.summary.timeValue),
                error: this.summary.timeError,
                onChange: this.changedTimeValue.bind(this),
                items: this.getCreationTimeValues(),
                menuWidth: 100,
                style: {
                    width: '60px'
                }
            });

            this.children.timeTypeSelect = new Select({
                className: 'time-type-select',
                model: {
                    rollup: this.model.rollup
                },
                inline: true,
                defaultValue: this.summary.timeType,
                error: this.summary.timeError,
                onChange: this.changedTimeType.bind(this),
                items: [{
                    value: 'm',
                    label: _('m').t(),
                    description: _('minute').t()
                },{
                    value: 'h',
                    label: _('h').t(),
                    description: _('hour').t()
                },{
                    value: 'd',
                    label: _('d').t(),
                    description: _('day').t()
                }],
                menuWidth: 100,
                style: {
                    width: '60px'
                }
            });

            var canRemove = this.options.canRemove;
            if (canRemove) {
                this.children.closeButton = new CloseButton({
                    onClick: this.handleCloseClick.bind(this),
                    style: {
                        'float': 'none'
                    }
                });
            }
            this.setAriaAttributes();
            this.startListening();
        },
        getCreationTimeValues: function() {
            var timeType = this.summary.timeType;
            var options = RollupUtils.summaryValuesMap[timeType];
            return options.map(function(option) {
                return {
                    value: option,
                    label: _(option.toString()).t()
                };
            });
        },
        setAriaAttributes: function() {
            var ariaLabel = 'Rollup summary ' + this.options.id;
            this.$el.attr({
                role: 'group',
                'aria-label': _(ariaLabel).t()
            });
        },
        startListening: function() {
            this.listenTo(this.model.rollup, 'change:tabs', this.render);
        },
        changedTimeValue: function(e, value) {
            var timeValue = value.value;
            this.summary.timeValue = timeValue;
            this.updateSummaryAttribute('timeValue', timeValue, false);
            this.model.rollup.set('verifyTimeType', true);
        },
        changedTimeType: function(e, value) {
            var type = value.value;
            this.summary.timeType = type;
            // if the new time type does not contain the current time value, default it to 1
            if (!RollupUtils.summaryValueForTypeExists(type, this.summary.timeValue)) {
                this.updateSummaryAttribute('timeValue', 1, false);
            }
            this.updateSummaryAttribute('timeType', type, false);
        },
        getSummaryById: function(id) {
            var tabs = $.extend(true, [], this.model.rollup.get('tabs'));
            var filteredSummaries = tabs[0].summaries.filter(function(summary) {
                return summary.id === id;
            });
            return filteredSummaries.length < 1 ? null : filteredSummaries[0];
        },
        handleChangedIndex: function(e, value) {
            this.updateSummaryAttribute('metricError', false, true);
            this.updateSummaryAttribute('targetIndex', value.value, false);
        },
        handleCloseClick: function() {
            var rollup = $.extend(true, {}, this.model.rollup);
            var tabs = rollup.get('tabs');
            tabs[0].summaries = tabs[0].summaries.filter(function(summary) {
                return summary.id !== this.options.id;
            }.bind(this));
            this.model.rollup.set('tabs', tabs);
        },
        updateSummaryAttribute: function(attr, value, silent) {
            var tabs = $.extend(true, [], this.model.rollup.get('tabs'));
            var id = this.summary.id;
            tabs[0].summaries.map(function(summary) {
                if (summary.id === id) {
                    summary[attr] = value;
                }
                return summary;
            }.bind(this));
            this.model.rollup.set({ 'tabs': tabs }, { silent: silent });
        },
        render: function() {
            if (!this.el.innerHTML) {
                var minSpanAllowed = this.model.rollup.get('minSpanAllowed');
                var abbrMinSpanAllowed = TimeConfigUtils.getAbbreviatedTime(minSpanAllowed);
                var template = _.template(this.template, {
                    _: _,
                    id: this.summary.id,
                    timeError: this.summary.timeError ? _("Must be >= " + abbrMinSpanAllowed).t() : undefined
                });
                this.$el.html(template);
                this.$("." + this.summary.id + "-time-value-select-placeholder").append(this.children.timeValueSelect.render().el);
                this.$("." + this.summary.id + "-time-type-select-placeholder").append(this.children.timeTypeSelect.render().el);
                this.$("." + this.summary.id + "-indexes-dropdown-placeholder").append(this.children.indexesDropdown.render().el);
                if (this.options.canRemove) {
                    this.$("." + this.summary.id + "-close-button-placeholder").append(this.children.closeButton.render().el);
                }
                this.summary.timeError ? this.$('.summary-time-error').show() : this.$('.summary-time-error').hide();
            }
            this.$el.attr('data-test-index', this.options.dataTestIndex);
            return this;
        },
        template: '\
            <span class="summary-item"><%- _("Roll up summary data into").t() %></span>\
            <span class="summary-item summary-target-index <%- id %>-indexes-dropdown-placeholder"></span>\
            <span class="summary-item"><%- _("every").t() %></span>\
            <span class="summary-time-value <%- id %>-time-value-select-placeholder"></span>\
            <span class="summary-time-type summary-item <%- id %>-time-type-select-placeholder"></span>\
            <span class="summary-item <%- id %>-close-button-placeholder"></span>\
            <div class="summary-time-error <%- id %>-time-error"><%- timeError %></div>\
        '
    });
});
