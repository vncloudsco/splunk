define([
        'underscore',
        'module',
        'splunk',
        'views/shared/controls/ControlGroup',
        'views/shared/controls/SyntheticSelectControl'
    ],
    function (_,
              module,
              splunk,
              ControlGroup,
              SyntheticSelectControl) {

        return ControlGroup.extend({

            moduleId: module.id,

            initialize: function () {
                var prompt = this.model.get('splitByField');
                var names = splunk.util.stringToFieldList(this.model.get('splitByFields')) || [];
                var items = [];

                // populate the items
                _.each(names, function (name) {
                    if (name === '_aggregation') {
                        items.push(this.formatItemForAggregation(name));
                    }
                    else {
                        items.push({
                            label: _(name).t(),
                            value: name
                        });
                    }
                }, this);

                // validate the prompt value
                if (!_.contains(names, prompt)) {
                    prompt = undefined;
                }
                else if (prompt === '_aggregation') {
                    // set to undefined and let the control to pick the first item in the list for the label
                    prompt = undefined;
                }

                var control = new SyntheticSelectControl({
                    items: items,
                    modelAttribute: 'display.visualizations.trellis.splitBy',
                    model: this.model,
                    prompt: prompt,
                    toggleClassName: 'btn'
                });

                this.options.controls = [control];
                this.options.tooltip = _('Use a field from your search results to split the visualization. If the search includes two or more aggregations, such as a count, you can also use them for splitting.').t();

                ControlGroup.prototype.initialize.call(this, this.options);
            },

            formatItemForAggregation: function (name) {
                var sources = splunk.util.stringToFieldList(this.model.get('splitSources')) || [];

                var label = _('Aggregation').t();
                if (sources.length === 1) {
                    label = splunk.util.sprintf(_('Aggregation (%s)').t(), sources.length);
                }
                else if (sources.length > 1) {
                    label = splunk.util.sprintf(_('Aggregations (%s)').t(), sources.length);
                }

                return {
                    label: label,
                    value: name,
                    description: splunk.util.fieldListToString(sources).replace(/,/g, ', ')
                };
            }
        });

    });
