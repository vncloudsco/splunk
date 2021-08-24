/**
 * @author atruong
 * @date 8/06/15
 *
 */

define([
	'jquery',
	'underscore',
	'backbone',
	'module',
	'models/shared/LinkAction',
	'models/Base',
	'splunk_monitoring_console/models/ThresholdConfig',
	'views/shared/FlashMessages',
	'views/shared/Modal',
    'util/splunkd_utils',
    'splunk_monitoring_console/views/settings/overview_preferences/components/ColorRangeControlGroup',
    'splunk_monitoring_console/helpers/ThresholdConfigsClient'
], function (
	$,
	_,
	Backbone,
	module,
	LinkAction,
	BaseModel,
	ThresholdConfig,
	FlashMessagesView,
	Modal,
	splunkDUtils,
	ColorRangesControlGroup,
	ThresholdConfigsClientHelper
) {
	return Modal.extend({
		moduleId: module.id,
        className: Modal.CLASS_NAME + ' edit-dialog-modal',
        _allInputsValid: true,

		initialize: function (options) {
			Modal.prototype.initialize.apply(this, arguments);
			this.children.flashMessagesView = new FlashMessagesView({ model: { thresholdConfig: this.model.thresholdConfig }});

			this.ranges = this.model.colorRanges.rangesValuesToArray();
            this.colors = this.model.colorRanges.colorValuesToArray();

			this.children.colorRangesView = new ColorRangesControlGroup({ 
				model: this.model.colorRanges, 
				displayMinMaxLabels: options.displayMinMaxLabels,
				rangesEditable: options.rangesEditable,
				rangesGradient: options.rangesGradient,
				rangesRational: options.rangesRational,
				paletteColors: ['#1e93c6', '#3863a0', '#5cc05c', '#d6563c', '#f2b827', '#ed8440', '#cc5068', '#6a5c9e', '#11a88b']
			});
			this.model.colorRanges.on('rangesValidated', this._handleValidation, this);
			this.model.colorRanges.on('resetToDefault', this._resetThresholdToDefault, this);
		},

		_handleValidation: function (isValid, error) {
			if (isValid) {
				this.updateValidationFailedMessage(false);
				this.$('#save-edit-btn').removeClass('disabled');
				this._allInputsValid = true;
			} else {
				this.updateValidationFailedMessage(true, error);
				this.$('#save-edit-btn').addClass('disabled');
				this._allInputsValid = false;
			}

		},

		_resetThresholdToDefault: function() {
			var default_threshold_name = "dmc_rangemap_default_" + this.model.colorRanges.get("name");
			var thresholdCollection = this.model.thresholdConfig.collection;
			var thresholdConfig = thresholdCollection.find(function(threshold) {
				return threshold.id.indexOf(default_threshold_name) !== -1;

			});
			var threshold = ThresholdConfigsClientHelper.parseDMCRangemapDefinition(this.model.colorRanges.get("name"), thresholdConfig.entry.content.get("definition"));

			this.model.colorRanges.set(threshold);

			this.stopListening();
			this.initialize(this.options);
			this.render();
		},

		updateValidationFailedMessage: function (failed, errMessage) {
	        if (failed) {
	            this.children.flashMessagesView.flashMsgHelper.addGeneralMessage('validation_failed',
	                {
	                    type: splunkDUtils.ERROR,
	                    html: errMessage
	                });
	        } else {
	            this.children.flashMessagesView.flashMsgHelper.removeGeneralMessage('validation_failed');
	        }
	    },

		events: $.extend({}, Modal.prototype.events, {
			'shown': function(e) {
				$(document).off('focusin.modal');
			},

			'click .modal-btn-save': function (e) {
				e.preventDefault();
				if (this._allInputsValid) {
					var definition = this.model.colorRanges.thresholdsToDefinition();
				
					this.model.thresholdConfig.entry.content.set({'definition': definition});
					this.model.thresholdConfig.save().done(_(function () {
						this.updateSaveFailedMessage(false);
						this.hide();
					}).bind(this)).fail(_(function () {
						this.updateSaveFailedMessage(true);
					}).bind(this));
				}
			}
		}),

		updateSaveFailedMessage: function (failed) {
	        if (failed) {
	            var errMessage = _('Failed to save changes to color mapping.').t();
	            this.children.flashMessagesView.flashMsgHelper.addGeneralMessage('save_failed',
	                {
	                    type: splunkDUtils.ERROR,
	                    html: errMessage
	                });
	        } else {
	            this.children.flashMessagesView.flashMsgHelper.removeGeneralMessage('save_failed');
	        }
	    },

		render: function () {
			var BUTTON_SAVE = '<a href="#" id="save-edit-btn" class="btn btn-primary modal-btn-save modal-btn-primary">' + _('Save').t() + '</a>';
			
			this.$el.html(Modal.TEMPLATE);
			this.$(Modal.HEADER_TITLE_SELECTOR).html( _('Edit: ').t() + this.model.colorRanges.get('displayName'));
			this.$(Modal.BODY_SELECTOR).show();
			this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);
			this.$(Modal.BODY_FORM_SELECTOR).html(_(this.dialogFormBodyTemplate).template());

			this.children.colorRangesView.render().appendTo(this.$('.color-ranges-view-placeholder'));
			this.children.flashMessagesView.render().appendTo(this.$('.flash-messages-view-placeholder'));
			
			this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
			this.$(Modal.FOOTER_SELECTOR).append(BUTTON_SAVE);


			return this;
		},

		dialogFormBodyTemplate: '\
			<div class="flash-messages-view-placeholder"></div>\
			<div class="color-ranges-view-placeholder"></div>\
		'
	});
});