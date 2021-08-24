import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import SlidingPanels from '@splunk/react-ui/SlidingPanels';
import ReactRollupView from 'views/indexes/shared/rollup/js/ReactRollupView';
import ReactAddEditIndexView from 'views/indexes/core/ReactAddEditIndexView';
import RollupConfirmation from 'views/indexes/shared/rollup/js/RollupConfirmation';
import PANEL_CONSTANTS from 'util/indexes/AddEditIndexPanelConstants';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @constructor
     * @memberOf views
     * @name AddEditIndexPanels
     * @extends {views.ReactAdapterBase}
     * @description A view for managing transitions between multiple
     * panels within a modal.
     *
     * @param {Object} options
     * @param {Object} options.model The model supplied to this class
     * @param {Object} options.collection The collection supplied to this class
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.store = {};
    },

    renderPanels() {
        const activePanelId = this.model.content.get('activePanelId');
        const transition = this.model.content.get('transition');
        const EDIT_INDEX_MODAL_WIDTH = 800; // Matches $rollupModalWidth avoids jank in transition
        const ROLLUP_VIEW_HEIGHT = 495; // Matches $rollupModalHeight avoids jank in transition
        return (
            <SlidingPanels
                activePanelId={activePanelId}
                transition={transition}
            >
                <SlidingPanels.Panel
                    key={PANEL_CONSTANTS.ADD_EDIT}
                    panelId={PANEL_CONSTANTS.ADD_EDIT}
                    style={{
                        padding: 20,
                        width: EDIT_INDEX_MODAL_WIDTH,
                        display: 'block',
                    }}
                >
                    <ReactAddEditIndexView
                        model={{
                            content: this.model.content,
                            rollup: this.model.rollup,
                            entity: this.model.entity,
                            addEditIndexModel: this.model.addEditIndexModel,
                            user: this.model.user,
                            application: this.model.application,
                        }}
                        collection={{
                            appLocals: this.collection.appLocals,
                            dimensions: this.collection.dimensions,
                            metrics: this.collection.metrics,
                            indexes: this.collection.indexes,
                        }}
                    />
                </SlidingPanels.Panel>
                <SlidingPanels.Panel
                    key={PANEL_CONSTANTS.ROLLUP_SETTINGS}
                    panelId={PANEL_CONSTANTS.ROLLUP_SETTINGS}
                    style={{
                        padding: 0,
                        width: EDIT_INDEX_MODAL_WIDTH,
                        height: ROLLUP_VIEW_HEIGHT,
                        display: 'block',
                    }}
                >
                    <ReactRollupView
                        model={{
                            content: this.model.content,
                            rollup: this.model.rollup,
                        }}
                        collection={{
                            dimensions: this.collection.dimensions,
                            metrics: this.collection.metrics,
                            indexes: this.collection.indexes,
                        }}
                    />
                </SlidingPanels.Panel>
                <SlidingPanels.Panel
                    key={PANEL_CONSTANTS.ROLLUP_SETTINGS_EDIT}
                    panelId={PANEL_CONSTANTS.ROLLUP_SETTINGS_EDIT}
                    style={{
                        padding: 0,
                        width: EDIT_INDEX_MODAL_WIDTH,
                        height: ROLLUP_VIEW_HEIGHT,
                        display: 'block',
                    }}
                >
                    <ReactRollupView
                        model={{
                            content: this.model.content,
                            rollup: this.model.rollup,
                        }}
                        collection={{
                            dimensions: this.collection.dimensions,
                            metrics: this.collection.metrics,
                            indexes: this.collection.indexes,
                        }}
                    />
                </SlidingPanels.Panel>
                <SlidingPanels.Panel
                    key={PANEL_CONSTANTS.CONFIRM_EDIT_ROLLUP}
                    panelId={PANEL_CONSTANTS.CONFIRM_EDIT_ROLLUP}
                    style={{
                        padding: 20,
                        width: EDIT_INDEX_MODAL_WIDTH,
                        display: 'block',
                    }}
                >
                    <RollupConfirmation isEdit />
                </SlidingPanels.Panel>
                <SlidingPanels.Panel
                    key={PANEL_CONSTANTS.CONFIRM_DELETE_ROLLUP}
                    panelId={PANEL_CONSTANTS.CONFIRM_DELETE_ROLLUP}
                    style={{
                        padding: 20,
                        width: EDIT_INDEX_MODAL_WIDTH,
                        display: 'block',
                    }}
                >
                    <RollupConfirmation />
                </SlidingPanels.Panel>
            </SlidingPanels>
        );
    },

    getComponent() {
        return (
            <BackboneProvider store={this.store} model={this.model}>
                {this.renderPanels()}
            </BackboneProvider>
        );
    },
});
