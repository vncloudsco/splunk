import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import TabBar from '@splunk/react-ui/TabBar';
// eslint-disable-next-line no-unused-vars
import css from 'views/indexes/shared/rollup/TabBar.pcss';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    className: 'rollup-tab-bar',
    /**
     * @constructor
     * @memberOf views
     * @name TabBar
     * @extends {views.ReactAdapterBase}
     * @description TabBar used for metric rollup configuration
     *
     * @param {Object} options
     * @param {Object} options.model The model supplied to this class
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.store = {};
        this.handleChange = this.handleChange.bind(this);
        this.handleTabsChange = this.handleTabsChange.bind(this);
        this.listenTo(this.model.content, 'change:tabIndex', this.render);
        this.listenTo(this.model.rollup, 'change:tabs', this.handleTabsChange);
        this.listenTo(this.model.rollup, 'change:addExceptionEnabled', this.render);
    },

    handleChange(e, { selectedTabId }) {
        this.model.content.set({ tabIndex: selectedTabId });
    },

    handleTabsChange() {
        const tabs = this.model.rollup.get('tabs');
        if (tabs.length) {
            this.render();
        }
    },

    renderTabBar() {
        const tabs = this.model.rollup.get('tabs');
        const tabElems = [];
        for (let i = 0; i < tabs.length; i += 1) {
            tabElems.push(
                <TabBar.Tab
                    className="rollup-tab"
                    label={tabs[i].tabBarLabel}
                    tabId={i.toString()}
                    key={i}
                />,
            );
        }
        const tabIndex = this.model.content.get('tabIndex');
        return (
            <TabBar
                layout="vertical"
                tabWidth={170}
                activeTabId={tabIndex}
                onChange={this.handleChange}
            >
                {tabElems}
            </TabBar>
        );
    },

    getComponent() {
        return (
            <BackboneProvider store={this.store} model={this.model}>
                {this.renderTabBar()}
            </BackboneProvider>
        );
    },
});
