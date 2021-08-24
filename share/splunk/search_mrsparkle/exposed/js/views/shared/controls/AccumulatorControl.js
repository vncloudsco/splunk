define([
    'jquery',
    'underscore',
    'module',
    'views/shared/controls/Control',
    'views/shared/controls/AccumulatorControl.pcss'
],
function (
    $,
    _,
    module,
    Control,
    css
    ) {
    /**
     * @constructor
     * @memberOf views
     * @name  AccumulatorControl
     * @extends {views.Control}
     *
     * @param {Object} options
     * @param {String} options.modelAttribute The attribute on the model to observe and update on selection
     * @param {Backbone.Model} options.model The model to operate on
     * @param {String} [options.itemName] Name the items shown. Displays as 'Available <itemName>' and 'Selected <itemName>' text.
     * @param {Object[]} options.items An array of elements and/or subarrays, where:
     * - An element is an object with keys described below (e.g. value & label)
     *   {String} [options.label] The text representing the item
     *   {String} [options.value] The value of the item to be assigned to modelAtribute when selected.
     *   {String} [options.icon] (optional) Name of the icon to show before an item
     *   {String} [options.category] (optional) Text value to be shown before a label

     */
    return Control.extend({
        moduleId: module.id,
        initialize: function() {
            var defaults = {
                itemName: _('item(s)').t()
            };

            _.defaults(this.options, defaults);

            Control.prototype.initialize.apply(this, arguments);
        },
        events: {
            'mousedown a.addAllLink': 'addAllLinkEvent',
            'keypress a.addAllLink': 'addAllLinkEvent',
            'mousedown a.removeAllLink': 'removeAllLinkEvent',
            'keypress a.removeAllLink': 'removeAllLinkEvent',
            'mousedown .availableOptions li': 'addOneItemEvent',
            'keypress .availableOptions li': 'addOneItemEvent',
            'mousedown .selectedOptions li': 'removeOneItemEvent',
            'keypress .selectedOptions li': 'removeOneItemEvent'
        },

        addAllLinkEvent: function(e) {
            this._addAll();
            e.preventDefault();
        },

        removeAllLinkEvent: function(e) {
            this._removeAll();
            e.preventDefault();
        },

        addOneItemEvent: function(e) {
            var li = e.currentTarget;
            this._addToSelected([li]);
        },

        removeOneItemEvent: function(e) {
            var li = e.currentTarget;
            this._removeFromSelected([li]);
        },

        render: function () {
            if (!this.el.innerHTML) {
                this.$el.html(this.compiledTemplate({ options: this.options }));
                this._populateAvailableOptions();
                this._addPreSelected();
                this.$('.availableOptionsHeader').text(_('Available ').t() + this.options.itemName);
                this.$('.selectedOptionsHeader').text(_('Selected ').t() + this.options.itemName);
            }
            return this;
        },

        onInputChange: function() {
            // collect selected values and update the model
            var $selectedOptions = this.$('.selectedOptions li');
            var selectedValues = [];
            $.each($selectedOptions, function(ix, option) {
                selectedValues.push($(option).data('id'));
            });
            this.setValue(selectedValues, false);

            // sort alphabetically
            $selectedOptions.sort(function(a,b){
                var keyA = $(a).text();
                var keyB = $(b).text();

                if (keyA < keyB) return -1;
                if (keyA > keyB) return 1;
                return 0;
            });
            var selItemsUl = this.$('.selectedOptions');
            $.each($selectedOptions, function(i, li){
                selItemsUl.append(li);
            });
        },

        _populateAvailableOptions: function (options) {
			var $availableOptions = this.$('.availableOptions');
			for (var i = 0, len = this.options.availableItems.length; i < len; i++) {
				var item = this.options.availableItems[i],
					iconClass = item['icon'],
					categoryClass = item['category'],
					$row = $('<div tabindex="0">').text(item['label']);
				if (iconClass) {
					$row.prepend($('<i class="icon-glyph icon-' + iconClass + '"/>'));
				}
				if (categoryClass) {
					$row.append($('<span class="icon-class">').text(categoryClass));
				}
				var opt = $('<li>').data({
						id: item['value'],
						label: item['label'],
						icon: item['icon'],
						category: item['category']
					}).html($row);
				$availableOptions.append(opt);
			}
		},

        _addToSelected: function(liArray) {
            var $selectedOptions = this.$('.selectedOptions');
            $.each(liArray, function(ix, li) {
                if (!$(li).hasClass('selected')) {
                    var id = $(li).data('id'),
                            category = $(li).data('category'),
                            icon = $(li).data('icon'),
                            label = $(li).data('label'),
                        $row = $('<div tabindex="0">').text(label);
					if (icon) {
                        $row.prepend($('<i class="icon-glyph icon-' + icon + '"/>'));
                    }
                    if (category) {
                        $row.append($('<span class="icon-class">').text(category));
                    }
                    var newLi = $('<li>').data('id',id).html($row);
                    $selectedOptions.append(newLi);
                    $(li).addClass('selected');
                } else {
                    this._removeFromSelected(liArray);
                }
            }.bind(this));
            this.onInputChange();
        },
        _removeFromSelected: function(liArray) {
            $.each(liArray, function(ix, li) {
                var id = $(li).data('id');
                this.$('.availableOptions li').filter(function(ix,item) {
                    return $(item).data('id') == id;
                }).removeClass("selected");
                this.$('.selectedOptions li').filter(function(ix,item) {
                    return $(item).data('id') == id;
                }).remove();
            }.bind(this));
            this.onInputChange();
        },
        _addAll: function() {
            var liArray = this.$('.availableOptions').find('li').not('.selected').get();
            this._addToSelected(liArray);
            this.onInputChange();
        },
        _removeAll: function() {
            this.$('.selectedOptions').find('li').remove();
            this.$('.availableOptions li.selected').removeClass("selected");
            this.onInputChange();
        },
        _addPreSelected: function() {
            if (this.options.selectedItems instanceof Array && this.options.selectedItems.length > 0) {
                var liArray = this.$('.availableOptions li').filter(function(ix, item) {
                    return this.options.selectedItems.indexOf($(item).data('id')) > -1;
                }.bind(this));
                this._addToSelected(liArray);
                this.onInputChange();
            }
        },
        remove: function () {
            return Control.prototype.remove.apply(this, arguments);
        },
        template: '\
            <div class="accumulator">\
                <div class="availableOptionsContainer">\
                    <a class="addAllLink" tabindex="0"><%= _("add all").t() %> &raquo;</a>\
                    <span class="availableOptionsHeader"></span>\
                    <ul class="availableOptions"></ul>\
                </div>\
                \
                <div class="selectedOptionsContainer">\
                    <a class="removeAllLink" tabindex="0">&laquo; <%= _("remove all").t() %></a>\
                    <span class="selectedOptionsHeader"></span>\
                    <ul class="selectedOptions"></ul> \
                </div>\
                <div class="clearfix"></div>\
            </div>'
    });
});

