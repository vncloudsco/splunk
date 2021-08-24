define(
    [
        'underscore',
        'jquery',
        'module',
        'models/Base',
        'views/Base',
        'views/shared/controls/ControlGroup',
        'views/shared/controls/SyntheticSelectControl',
        'views/shared/controls/SyntheticRadioControl',
        'views/shared/controls/SyntheticCheckboxControl',
        'views/shared/controls/SyntheticSliderControl',
        'views/shared/controls/CheckboxGroup',
        'views/shared/controls/TextControl',
        'views/shared/controls/TextareaControl',
        'views/shared/controls/TextBrowseControl',
        'views/shared/controls/DateControl',
        'views/shared/controls/LabelControl',
        'views/shared/controls/AccumulatorControl',
        'views/shared/controls/SliderControl',
        '../Master.pcss'
    ],
    function(
        _,
        $,
        module,
        BaseModel,
        BaseView,
        ControlGroup,
        SyntheticSelectControl,
        SyntheticRadioControl,
        SyntheticCheckboxControl,
        SyntheticSliderControl,
        CheckboxGroupControl,
        TextControl,
        TextareaControl,
        TextBrowseControl,
        DateControl,
        LabelControl,
        Accumulator,
        SliderControl,
        css
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'form-horizontal',
            events: {
                'click .content a': function(e) {
                    e.preventDefault();
                }
            },
            initialize: function() {
                // Dummy model
                this.model = new BaseModel({
                    sliderVal: 0.5
                });
                BaseView.prototype.initialize.apply(this,arguments);
                this.children.split1 = new ControlGroup ({
                    controls: [
                        new TextControl({
                            modelAttribute: 'appendTextControl'
                        }),
                        new SyntheticSelectControl ({
                            model: this.model,
                            modelAttribute: 'appendSelect',
                            items: [
                                { label: _('is greater than').t(), value: 'greater than' },
                                { label: _('is less than').t(), value: 'less than' },
                                { label: _('is equal to').t(), value: 'equal to' },
                                { label: _('is not equal to').t(), value: 'not equal to' },
                                { label: _('drops by').t(), value: 'drops by' },
                                { label: _('rises by').t(), value: 'rises by' }
                            ],
                            toggleClassName: 'btn',
                            menuWidth: 'narrow'
                        })
                    ],
                    label: _('Join (Default)').t()
                });
                this.children.split2 = new ControlGroup ({
                    controlsLayout: 'separate',
                    controls: [
                        new TextControl({
                            modelAttribute: 'prependTextControl'
                        }),
                        new SyntheticSelectControl ({
                            model: this.model,
                            modelAttribute: 'prependSelect',
                            items: [
                                { label: _('is greater than').t(), value: 'greater than' },
                                { label: _('is less than').t(), value: 'less than' },
                                { label: _('is equal to').t(), value: 'equal to' },
                                { label: _('is not equal to').t(), value: 'not equal to' },
                                { label: _('drops by').t(), value: 'drops by' },
                                { label: _('rises by').t(), value: 'rises by' }
                            ],
                            toggleClassName: 'btn',
                            menuWidth: 'narrow'
                        })
                    ],
                    label: _('Separate').t()
                });
                this.children.link = new ControlGroup({
                    controlType:'Text',
                    controlOptions: {
                        modelAttribute: 'appendCustomHTML',
                        append: '<a class="add-on bookmark" href=""><i class="icon-bookmark"></i><span class="hide-text">' + _("Splunk Search Job").t() + '</span></a>'
                    },
                    label: _('Append custom html').t()
                });
            },
            render: function() {
                // Renders each child view
                this.eachChild(function(view) {
                    view.render().appendTo(this.$el);
                },this);
                return this;
            }
        });
    }
);
