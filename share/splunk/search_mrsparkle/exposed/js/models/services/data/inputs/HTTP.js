define(
    [
        'jquery',
        'underscore',
        'models/services/data/inputs/BaseInputModel',
        'util/splunkd_utils'
    ],
    function (
        $,
        _,
        BaseInputModel,
        splunkd_utils
        ) {
        return BaseInputModel.extend({
            url: "data/inputs/http",
            urlRoot: "data/inputs/http",
            validation: {
                'ui.name': [
                    {
                        required: function() {
                            return this.isNew();
                        },
                        msg: _("Token name is required.").t()
                    },
                    {
                        fn: 'checkInputExists'
                    }
                ],
                'ui.index': [
                    {
                        required: function() {
                            if (this.wizard && this.wizard.get('currentStep') === 'inputsettings') {
                                return _.isArray(this.get('ui.indexes')) && this.get('ui.indexes').length;
                            }
                            return false;
                        },
                        msg: _("Default index is required when list of allowed indexes is set.").t()
                    }
                ]
            },

            runAction: function(action, options) {
                var url = this.entry.links.get(action);
                if (!url) {
                    return;
                }
                return $.post(splunkd_utils.fullpath(url), options);
            },

            isEnabled: function () {
                return !!this.entry.links.get('disable');
            },

            disable: function() {
                return this.runAction('disable');
            },

            enable: function() {
                return this.runAction('enable');
            },

            canEdit: function () {
                return this.entry.links.has('edit');
            },

            canDelete: function () {
                return this.entry.links.has('remove');
            },

            canDisable: function () {
                return this.entry.links.has('disable');
            },

            canEnable: function () {
                return this.entry.links.has('enable');
            }
        });
    }
);
