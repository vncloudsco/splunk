define(
    [
        'underscore',
        'jquery',
        'module',
        'views/Base',
        'views/shared/controls/ControlGroup',
        'splunk.util'
    ],
    function(
        _,
        $,
        module,
        BaseView,
        ControlGroup,
        splunkUtils
    ) {
        return BaseView.extend({
            moduleId: module.id,
            tagName: 'form',
            className: 'form-vertical',
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.children.lookupName = new ControlGroup({
                    label: _('File name').t(),
                    controlType: 'Text',
                    controlOptions: {
                        model: this.model.document.entry.content,
                        modelAttribute: 'action.lookup.filename'
                    },
                    help: _('Provide a new or existing .csv lookup table file name.').t()
                });

                this.children.appendCheckbox = new ControlGroup({
                    controlType: 'SyntheticRadio',
                    controlOptions: {
                        modelAttribute: 'action.lookup.append',
                        model: this.model.document.entry.content,
                        items: [
                            {
                                label: _('Append').t(),
                                value: 1
                            },
                            {
                                label: _('Replace').t(),
                                value: 0
                            }
                        ]
                    },
                    label: _('Results').t(),
                    help: _('Each time the report runs, its new results are added to the lookup table or replace the lookup table.').t()
                });
            },

            render: function() {
                this.children.lookupName.render().appendTo(this.$el);
                this.children.appendCheckbox.render().appendTo(this.$el);

                return this;
            }
        });
    }
);
