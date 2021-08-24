define(
	[
		'jquery',
		'underscore',
		'module',
		'views/shared/controls/MultiInputControl'
	],
	function(
		$,
		_,
		module,
		MultiInputControl
	) {
		return MultiInputControl.extend({
			moduleId: module.id,
			
			initialize: function() {
				this.options.placeholder = this.options.placeholder || _("Choose groups").t();
				this.populateCollectionTags();
				this.collection.on('change:' + this.options.modelAttribute, this.updateTags, this);

				MultiInputControl.prototype.initialize.apply(this, arguments);
			},

			updateTags: function() {
				this.populateCollectionTags();
				this.debouncedRender();
			},

			populateCollectionTags: function() {
				this.options.autoCompleteFields = this.collection[this.options.collectionMethod].call(this.collection);
			}
		});

	}
);