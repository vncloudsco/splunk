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

        /**
         * @constructor
         * @param options {Object} {
         *     model {Model} the model to operate on
         * }
         */

        initialize: function() {
            this.options.label = _('True Label').t();
            this.options.controls = [
                {
                    type: 'Text',
                    options: {
                        model: this.model,
                        modelAttribute: 'trueLabel',
                        placeholder: _('optional').t(),
                        inputClassName: 'input-medium'
                    }
                }
            ];
            ControlGroup.prototype.initialize.call(this, this.options);
        }

    });

});
