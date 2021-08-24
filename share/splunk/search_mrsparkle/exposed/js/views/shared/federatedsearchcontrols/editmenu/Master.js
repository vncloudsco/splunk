define(
   [
       'jquery',
       'underscore',
       'module',
       'views/Base',
       'views/shared/documentcontrols/dialogs/DeleteDialog',
       'views/shared/federatedsearchcontrols/editmenu/Menu',
       'uri/route',
       'bootstrap.modal'
   ],
   function (
       $,
       _,
       module,
       Base,
       DeleteDialog,
       EditMenuPopTart,
       route
       /* bootstrap modal */
   ) {
   return Base.extend({
           moduleId: module.id,
            /**
            * @param {Object} options {
            *      model: {
            *          report: <models.search.Report>,
            *          application: <models.Application>,
            *          user: <models.service.admin.user>,
            *          serverInfo: <models.services.server.ServerInfo>,
            *          controller: <Backbone.Model> (Optional)
            *      },
            *      collection: {
            *          fshRoles: <collections.services.authorization.FshRoles>,
            *          federations: <collections/services/dfs/Federations>
            *      },
            *      {Boolean} button: (Optional) Whether or not the Edit dropdown has class btn-pill. Default is true and class is btn.
            *      {Boolean} deleteRedirect: (Optional) Whether or not to redirect to reports page after delete. Default is false.
            *      {Boolean} showSearchField: (Optional) Whether to display a field to the user for entering the search string.
            *                                    Default is false
            *      {Function} onOpenFederatedSearchDialog: (Optional) Handler for click on edit search.
            * }
            */
           initialize: function() {
               Base.prototype.initialize.apply(this, arguments);

               var defaults = {
                   button: true,
                   deleteRedirect: false,
                   showSearchField: false
               };

               _.defaults(this.options, defaults);
           },
           events: {
               'click a.delete': function(e) {
                   this.children.deleteDialog = new DeleteDialog({
                       model: {
                           report: this.model.report,
                           application: this.model.application,
                           controller: this.model.controller
                       },
                       deleteRedirect: this.options.deleteRedirect,
                       onHiddenRemove: true
                   });

                   this.children.deleteDialog.render().appendTo($("body")).show();

                   e.preventDefault();
               },
               'click a.edit': function(e) {
                   e.preventDefault();
                   this.openEdit($(e.currentTarget));
               }
           },
           openEdit: function($target) {
               if (this.children.editMenuPopTart && this.children.editMenuPopTart.shown) {
                   this.children.editMenuPopTart.hide();
                   return;
               }

               $target.addClass('active');

               this.children.editMenuPopTart = new EditMenuPopTart({
                   model: {
                       report: this.model.report,
                       application: this.model.application,
                       user: this.model.user,
                       serverInfo: this.model.serverInfo,
                       controller: this.model.controller
                   },
                   collection: {
                       fshRoles: this.collection.fshRoles,
                       searchBNFs: this.collection.searchBNFs,
                       federations: this.collection.federations
                   },
                   onHiddenRemove: true,
                   deleteRedirect: this.options.deleteRedirect,
                   showSearchField: this.options.showSearchField,
                   onOpenFederatedSearchDialog: this.options.onOpenFederatedSearchDialog
               });

               this.children.editMenuPopTart.render().appendTo($('body'));
               this.children.editMenuPopTart.show($target);
               this.children.editMenuPopTart.on('hide', function() {
                   $target.removeClass('active');
               }, this);
           },
           render: function () {
               var canWrite = this.model.report.canWrite(this.model.user.canScheduleSearch(), this.model.user.canRTSearch()),
                   canDelete = this.model.report.canDelete();

               if (canWrite) {
                   this.$el.append('<a class="dropdown-toggle edit' + (this.options.button ? " btn" : "") + '" href="#">' + _("Edit").t() +'<span class="caret"></span></a>');
               } else if (canDelete) {
                   this.$el.append('<a class="delete' + (this.options.button ? " btn" : "") + '" href="#">' + _("Delete").t() +'</a>');
               }

               return this;
           }
       });
   }
);
