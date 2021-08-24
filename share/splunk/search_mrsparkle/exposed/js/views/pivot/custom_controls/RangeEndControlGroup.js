define([
            'underscore',
            'module',
            'views/shared/controls/ControlGroup',
            'views/shared/controls/Control'
        ],
        function(
            _,
            module,
            ControlGroup,
            Control
        ) {

    return ControlGroup.extend({

        moduleId: module.id,

        initialize: function() {
            this.options.label = _('Range End').t();
            this.options.controls = [
                {
                    type: 'Text',
                    options: {
                        model: this.model,
                        modelAttribute: 'rangeEnd',
                        placeholder: _('optional').t(),
                        inputClassName: 'input-medium'
                    }
                }
            ];
            ControlGroup.prototype.initialize.call(this, this.options);
        }

    });

});
