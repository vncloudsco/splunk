define(
    [
        'module',
        'jquery',
        'underscore',
        '../Base',
        'views/shared/PopTart',
        'util/pdf_utils'
    ],
    function(module,
             $,
             _,
             BaseDashboardView,
             PopTartView,
             PDFUtils) {

        var defaults = {
            button: true,
            showOpenActions: true,
            deleteRedirect: false
        };

        var ExportMenuOptions = PopTartView.extend({
            className: 'dropdown-menu export-menu',
            initialize: function() {
                PopTartView.prototype.initialize.apply(this, arguments);
                _.defaults(this.options, defaults);
            },
            events: {
                'click a.edit-export-pdf': function(e) {
                    e.preventDefault();
                    this._triggerControllerEvent('action:export-pdf');
                },
                'click a.edit-schedule-pdf': function(e) {
                    e.preventDefault();
                    if ($(e.currentTarget).is('.disabled')) {
                        return;
                    }
                    this._triggerControllerEvent('action:schedule-pdf');
                },
                'click a.edit-print': function(e) {
                    e.preventDefault();
                    this._triggerControllerEvent('action:print');
                }
            },
            _triggerControllerEvent: function() {
                this.model.controller.trigger.apply(this.model.controller, arguments);
                this.hide();
            },
            render: function() {
                this.$el.html(PopTartView.prototype.template_menu);
                this.$el.append(this._getTemplate());
                return this;
            },
            _getTemplate: function() {
                var menuModel = {
                    canWrite: this.model.view.entry.acl.canWrite(),
                    isSimpleXML: this.model.view.isSimpleXML(),
                    userCanSchedule: this.model.user.canSchedulePDF(),
                    viewSchedulable: this.model.view.canSchedulePDF(),
                    viewPdfSchedulable: PDFUtils.isPDFGenAvailable() && this.model.view.canSchedulePDF(),
                    canExport: this.model.view.isSimpleXML() && PDFUtils.isPDFGenAvailable(),
                    isForm: this.model.view.isForm()
                };
                return this.compiledTemplate(menuModel);
            },
            isEmpty: function() {
                return false; // There're will be at least one print item
            },
            template: '\
                <ul class="first-group">\
                    <% if (canExport) { %>\
                        <li><a href="#" class="edit-export-pdf"><%- _("Export PDF").t() %></a></li>\
                    <% } else { %>\
                        <li><a href="#" class="edit-export-pdf disabled"><%- _("Export PDF").t() %></a></li>\
                    <% } %>\
                    <% if (userCanSchedule) { %>\
                        <% if (viewPdfSchedulable) { %>\
                            <li><a href="#" class="edit-schedule-pdf"><%- _("Schedule PDF Delivery").t() %></a></li>\
                        <% } else { %>\
                            <li><a href="#" class="edit-schedule-pdf disabled"><%- _("Schedule PDF Delivery").t() %></a></li>\
                        <% } %>\
                    <% } %>\
                    <li><a href="#" class="edit-print"><%- _("Print").t() %></a></li>\
                </ul>\
            '
        });


        return BaseDashboardView.extend({
            moduleId: module.id,
            ViewOptions: {
                register: false
            },
            initialize: function() {
                BaseDashboardView.prototype.initialize.apply(this, arguments);
            },
            events: {
                'click a.edit-export': function(e) {
                    e.preventDefault();
                    this.children.exportMenuOptions = new ExportMenuOptions({
                        model: this.model
                    });
                    this.children.exportMenuOptions.once('hide', this.children.exportMenuOptions.remove);
                    $('body').append(this.children.exportMenuOptions.render().$el);
                    var $btn = $(e.currentTarget);
                    $btn.addClass('active');
                    this.children.exportMenuOptions.show($btn);
                    this.children.exportMenuOptions.once('hide', function(){
                        $btn.removeClass('active');
                    });
                }
            },
            render: function() {
                this.$el.html(this.compiledTemplate());
                return this;
            },
            template: '\
                    <a class="btn edit-export" href="#"><%- _("Export").t() %> <span class="caret"></span></a>\
            '
        });
    }
);
