define([
    'jquery',
    'underscore',
    'splunk.util',
    'views/shared/dialogs/TextDialog',
    'views/dashboard/editor/dialogs/EditDrilldown',
    'views/shared/vizcontrols/trellis/Dialog',
    'views/dashboard/editor/dialogs/EditSearch',
    'views/dashboard/editor/dialogs/CreateReport',
    'views/dashboard/editor/dialogs/SelectReport'
], function($,
            _,
            splunkUtils,
            TextDialog,
            EditDrilldownDialog,
            EditTrellisDialog,
            EditSearchDialog,
            CreateReportDialog,
            SelectReportDialog) {

    // this is to workaround circular reference issue in require.js.
    // this function is needed inside EdiSearchDialog, which cannot import DialogHelper, because DialogHelp has imported
    // EditSearchDialog.
    function openCreateReportDialog(options) {
        var createReportDialog = new CreateReportDialog({
            model: options.model,
            searchManager: options.searchManager,
            onHiddenRemove: true
        });
        $("body").append(createReportDialog.render().el);
        createReportDialog.show();
        return createReportDialog;
    }

    return {
        openEditDrilldownDialog: function(options) {
            var editDrilldownDialog = new EditDrilldownDialog({
                settings: options.settings,
                model: options.model,
                collection: options.collection,
                eventManager: options.eventManager,
                onHiddenRemove: true
            });
            $('body').append(editDrilldownDialog.render().$el);
            return editDrilldownDialog;
        },
        openEditTrellisDialog: function(options) {
            var editTrellisDialog = new EditTrellisDialog({
                model: options.model,
                className: 'popdown-dialog popdown-dialog-draggable popdown-dialog-trellis',
                formatterDescription: options.formatterDescription,
                onHiddenRemove: true,
                saveOnApply: options.saveOnApply
            });
            $('body').append(editTrellisDialog.render().$el);
            editTrellisDialog.show(options.$target);
            return editTrellisDialog;
        },
        openEditSearchDialog: function(options) {
            var editSearchDialog = new EditSearchDialog({
                model: options.model,
                searchManager: options.searchManager,
                openCreateReportDialog: openCreateReportDialog,
                onHiddenRemove: true
            });
            $("body").append(editSearchDialog.render().el);
            editSearchDialog.show();
            return editSearchDialog;
        },
        openCreateReportDialog: openCreateReportDialog,
        confirmConvertToInline: function(options) {
            var name = options.isPivot ? "Pivot Search" : "Inline Search";
            var dfd = $.Deferred();
            var dialog = new TextDialog({
                id: "modal_inline",
                onHiddenRemove: true
            });
            dialog.settings.set("primaryButtonLabel", splunkUtils.sprintf(_("Clone to %s").t(), name));
            dialog.settings.set("cancelButtonLabel", _("Cancel").t());
            dialog.settings.set("titleLabel", splunkUtils.sprintf(_("Clone to %s").t(), name));
            dialog.setText('<div>\
                <p>' + splunkUtils.sprintf(_("The report will be cloned to %s.").t(), name.toLowerCase()) + '</p>\
                <p>' + splunkUtils.sprintf(_("The %s:").t(), name.toLowerCase()) + '\
                </p><ul>\
                <li>' + _("Cannot be scheduled.").t() + '</li>\
                <li>' + _("Will run every time the dashboard is loaded.").t() + '</li>\
                <li>' + _("Will use the permissions of the dashboard.").t() + '</li>\
                </ul>\
                </div>');
            $("body").append(dialog.render().el);
            dialog.once('click:primaryButton', dfd.resolve);
            dialog.once('hide hidden', dfd.reject);
            dialog.show();
            return dfd.promise();
        },
        openSelectReportDialog: function(options) {
            var dialog = new SelectReportDialog({
                model: options.model,
                collection: options.collection,
                reportLimit: options.reportLimit,
                onHiddenRemove: true
            });
            $("body").append(dialog.render().el);
            dialog.show();
            return dialog;
        },
        confirmUseReportSetting: function(options) {
            var dfd = $.Deferred();
            var dialog = new TextDialog({
                id: "modal_use_report_formatting"
            });
            dialog.settings.set("primaryButtonLabel", _("Use Report's Formatting").t());
            dialog.settings.set("cancelButtonLabel", _("Cancel").t());
            dialog.settings.set("titleLabel", _("Use Report's Formatting").t());
            dialog.setText(_("This will change the content's formatting to the report's formatting. Are you sure you want use the report's formatting?").t());
            $("body").append(dialog.render().el);
            dialog.once('click:primaryButton', dfd.resolve);
            dialog.once('hide hidden', dfd.reject);
            dialog.show();
            return dfd.promise();
        }
    };
});
