define([
    'jquery',
    'underscore',
    'backbone',
    'module',
    'views/Base',
    'views/shared/reportcontrols/dialogs/summaryindexingdialog/NewFieldRow'
],
    function (
        $,
        _,
        Backbone,
        module,
        BaseView,
        NewFieldRow
        ) {

        return BaseView.extend({
            moduleId: module.id,
            /**
            * @param {Object} options {
            *       model: {
            *           fieldList: <Backbone.Model>
            *       }
            * }
            */
            events: {
                'click .add-another-field': function(e) {
                    e.preventDefault();
                    var newRow = new NewFieldRow({
                        model: this.model.fieldList,
                        numRow: this.settingRows.length
                    });
                    this.settingRows.push(newRow);
                    newRow.render().appendTo(this.$('.additional-field-placeholder'));
                    this.listenTo(newRow, 'closeRow', this.onCloseRow);
                }
            },

            initialize: function(options) {
                BaseView.prototype.initialize.call(this, options);
                this.settingRows = [];

                // create any existing fields
                _.each(_.keys(this.model.fieldList.attributes), function(k) {
                    // SPL-159480,SPL-181574: Remove forceCsvResults and force_realtime_schedule
                    // parameter from summary indexing dialog.
                    if ((k.toString() !== "forceCsvResults") &&
                        (k.toString() !== "force_realtime_schedule")) {
                        var newRow = new NewFieldRow({
                            model: this.model.fieldList,
                            numRow: this.settingRows.length,
                            defaultKey: k,
                            defaultValue: this.model.fieldList.attributes[k]
                        });
                        this.settingRows.push(newRow);
                        this.listenTo(newRow, 'closeRow', this.onCloseRow);
                    }
                }.bind(this));

                // add empty field if no existing fields
                if (!this.settingRows.length) {
                    var newRow = new NewFieldRow({
                        model: this.model.fieldList,
                        numRow: this.settingRows.length
                    });
                    this.settingRows.push(newRow);
                }
            },

            onCloseRow: function(row, key) {
                var rowIndex = _(this.settingRows).indexOf(row);
                this.stopListening(row);
                row.detach();
                if (rowIndex != -1) {
                    this.settingRows.splice(rowIndex, 1); // Remove the row from our array
                }
            },

            render: function() {
                this.$el.html(this.compiledTemplate({}));
                // Render existing rows, append them to .additional-field-placeholder
                _.each(this.settingRows, function(newRow) {
                    newRow.render().appendTo(this.$('.additional-field-placeholder'));
                }.bind(this));

                return this;
            },

            template: '\
                <div class="field-label"><%- _("Add Fields").t() %></div>\
                <div class="fields-section">\
                    <div class="additional-field-placeholder"></div>\
                    <div><a href="#" class="add-another-field"><%- _("Add another field").t() %></a></div>\
                </div>\
            '
        });

    });

