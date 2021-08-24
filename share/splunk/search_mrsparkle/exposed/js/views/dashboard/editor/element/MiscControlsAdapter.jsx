import React from 'react';
import $ from 'jquery';
import Backbone from 'backbone';
import ReactAdapterBase from 'views/ReactAdapterBase';
import MiscControls from 'dashboard/components/editor/element/MiscControls';
import DialogHelper from 'views/dashboard/editor/element/DialogHelper';
import VisualizationRegistry from 'helpers/VisualizationRegistry';
import trellisSchema from 'views/shared/viz/schemas/trellis';
import { isDrilldownSupported } from 'controllers/dashboard/helpers/ReportModelHelper';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    initialize(...args) {
        ReactAdapterBase.prototype.initialize.apply(this, ...args);

        this.state = this.state || new Backbone.Model();

        this.onReportModelChange();

        this.listenTo(this.model.report.entry.content, 'change', this.onReportModelChange);
        this.listenTo(this.state, 'change', this.render);

        this.onClickDrilldown = this.onClickDrilldown.bind(this);
        this.onClickTrellis = this.onClickTrellis.bind(this);
    },
    onReportModelChange() {
        const vizConfig = VisualizationRegistry.findVisualizationForConfig(this.model.report.entry.content.toJSON());
        this.state.set('disableDrilldown', !isDrilldownSupported(this.model.report.entry.content.toJSON())
            || (!vizConfig || vizConfig.supports.drilldown === false));
        this.state.set('disableTrellis', !vizConfig || vizConfig.isSplittable === false);
    },
    onClickDrilldown() {
        const dialog = DialogHelper.openEditDrilldownDialog({
            settings: this.options.settings,
            model: this.model,
            collection: this.collection,
            eventManager: this.options.eventManager,
        });

        this.listenTo(dialog, 'drilldownUpdated', () => {
            this.options.model.controller.trigger('edit:drilldown', { eventManagerId: this.options.eventManager.id });
            dialog.hide();
        });
    },
    onClickTrellis(e) {
        DialogHelper.openEditTrellisDialog({
            model: this.model,
            formatterDescription: trellisSchema,
            saveOnApply: true,
            $target: $(e.target),
        });
    },
    getComponent() {
        return (<MiscControls
            onClickDrilldown={this.onClickDrilldown}
            onClickTrellis={this.onClickTrellis}
            disableDrilldown={this.state.get('disableDrilldown')}
            disableTrellis={this.state.get('disableTrellis')}
        />);
    },
});
