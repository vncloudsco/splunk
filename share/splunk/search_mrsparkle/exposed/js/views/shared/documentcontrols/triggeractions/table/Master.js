define(
    [
        'jquery',
        'underscore',
        'views/Base',
        'views/shared/documentcontrols/triggeractions/table/PrimaryRow',
        'views/shared/documentcontrols/triggeractions/table/formrow/Master',
        'views/shared/delegates/TableRowToggle',
        'util/general_utils',
        'module'
    ],
    function(
        $,
        _,
        BaseView,
        TableRowView,
        FormRowView,
        TableRowToggleView,
        GeneralUtils,
        module
    ) {
    return BaseView.extend({
        moduleId: module.id,
        className: 'alert-actions-control-group',
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
            this.listenTo(this.collection.selectedAlertActions, 'reset', this.reRenderRows);
            this.listenTo(this, 'addrow', function(addedAlertAction) {
                this.addRow(addedAlertAction, true, true);
            });
            this.listenTo(this.model.document, 'toggleRow', function($row, collapseOthers) {
                this.children.tableRowToggle.toggleRow($row, collapseOthers);
            });
        },
        addRow: function(selectedAlertAction, expand, scrollTo) {
            var alertActionUI = this.collection.alertActionUIs.findByEntryName(selectedAlertAction.entry.get('name'));
            var row = new TableRowView({
                model: {
                    selectedAlertAction: selectedAlertAction,
                    document: this.model.document,
                    application: this.model.application,
                    alertActionUI: alertActionUI
                },
                collection: {
                    selectedAlertActions: this.collection.selectedAlertActions,
                    unSelectedAlertActions: this.collection.unSelectedAlertActions
                }
            });
            var isCustomAction = GeneralUtils.normalizeBoolean(selectedAlertAction.entry.content.get('is_custom'));
            var isExpandable = !isCustomAction || alertActionUI != null;

            if (isExpandable) {
                var form = new FormRowView({
                    pdfAvailable: this.options.pdfAvailable,
                    model: {
                        selectedAlertAction: selectedAlertAction,
                        document: this.model.document,
                        application: this.model.application,
                        alertActionUI: alertActionUI
                    },
                    documentType: this.options.documentType
                });

                form.render().prependTo(this.$el.find('tbody'));
            }
            row.render().prependTo(this.$el.find('tbody'));
            if (isExpandable) {
                this.children.tableRowToggle.toggleRow(row.$el, true);
            } else {
                this.children.tableRowToggle.toggleRow(row.$el.siblings('.expanded'), false);
            }
            if (scrollTo) {
                var $scrollingBody = $('.modal-body-scrolling:visible');
                $scrollingBody.animate({
                    scrollTop: $scrollingBody.scrollTop() + (row.$el.offset().top - $scrollingBody.offset().top) - 5
                }, 200);
            }
        },
        renderRows: function() {
            this.collection.selectedAlertActions.each(function(selectedAlertAction) {
                this.addRow(selectedAlertAction);
            }, this);
        },
        reRenderRows: function() {
            this.$('tr').remove();
            this.renderRows();
        },
        render: function() {
            this.children.tableRowToggle = new TableRowToggleView({
                el: this.el,
                collapseOthers: true,
                disabledClass: 'disabled',
                allowKeyToggle: true
            });
            this.$el.html(this.compiledTemplate({
                _: _
            }));

            this.renderRows();
            return this;
        },
        template: '\
            <label class="control-label trigger-actions-control-label"><%- _("When triggered").t() %></label>\
            <div class="controls trigger-actions-controls">\
                <table class="table-chrome table table-row-expanding table-hover">\
                    <tbody>\
                    </tbody>\
                </table>\
            </div>\
        '
    });
});
