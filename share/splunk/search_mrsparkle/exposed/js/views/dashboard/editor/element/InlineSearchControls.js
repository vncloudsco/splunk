define([
    'module',
    'underscore',
    'views/dashboard/editor/element/ElementControls',
    'views/dashboard/editor/element/DialogHelper',
    'controllers/dashboard/helpers/EditingHelper',
    'util/general_utils',
    'bootstrap.tooltip'
], function(module,
            _,
            ElementControls,
            DialogHelper,
            EditingHelper,
            GeneralUtils) {

    var InlineSearchControls = ElementControls.extend({
        moduleId: module.id,
        events: _.extend(ElementControls.prototype.events, {
            'keydown a.action-edit-search': function(e) {
                if (e.keyCode == 13) {  // is 'enter' key
                    this.onEditSearch(e);
                }
            },
            'click a.action-edit-search': 'onEditSearch'
        }),
        onEditSearch: function(e) {
            e.preventDefault();
            var dialog = DialogHelper.openEditSearchDialog({
                model: this.model,
                searchManager: this.searchManager
            }).on('searchUpdated', function(searchAttributes) {
                this.searchManager.settings.set(_.omit(searchAttributes, 'refreshDisplay'), {tokens: true});
                this.model.report.entry.content.set('dashboard.element.refresh.display', searchAttributes.refreshDisplay);
                this.model.controller.trigger('edit:search', {searchManagerId: this.searchManager.id});
                dialog.hide();
            }.bind(this));
            this.children.popdown.hide();
        },
        getIconClass: function() {
            var isPivot = GeneralUtils.isValidPivotSearch(this.searchManager.settings.resolve());
            return isPivot ? "icon-pivot" : "icon-search-thin";
        },
        tooltip: function(options) {
            this.$('a.action-edit-search').tooltip(options);
        },
        render: function() {
            ElementControls.prototype.render.apply(this, arguments);

            this.tooltip({
                title: _('Edit search').t()
            });

            return this;
        },
        template: '\
            <a class="dropdown-toggle action-edit-search btn-pill" href="#">\
                    <span class="<%- iconClass %>"></span>\
            </a>\
        '
    });

    return InlineSearchControls;
});
