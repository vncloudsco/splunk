import _ from 'underscore';
import React from 'react';
import { createStore, applyMiddleware } from 'redux';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import thunkMiddleware from 'redux-thunk';
import createLogger from 'redux-logger';
import ReactAdapterBase from 'views/ReactAdapterBase';
import reducers from 'dashboard/containers/editor/drilldown/drilldownReducer';
import DrilldownContainer from 'dashboard/containers/editor/drilldown/DrilldownContainer';
import {
    fetchTimeRangePresets,
    fetchApps,
    fetchDashboards,
    fetchReports,
    validateLinkToDashboard,
} from 'dashboard/containers/editor/drilldown/drilldownActions';
import {
    updateLinkToSearchSetting,
} from 'dashboard/containers/editor/drilldown/search/searchActions';
import {
    updateLinkToDashboardSetting,
} from 'dashboard/containers/editor/drilldown/dashboard/dashboardActions';
import {
    updateLinkToReportSetting,
} from 'dashboard/containers/editor/drilldown/report/reportActions';
import {
    updateLinkToURLSetting,
} from 'dashboard/containers/editor/drilldown/url/urlActions';
import {
    updateTokensSetting,
} from 'dashboard/containers/editor/drilldown/tokens/tokensActions';

import {
    createInitialState,
    applyState,
} from 'controllers/dashboard/helpers/DrilldownStateConverter';
import {
    NO_DRILLDOWN,
    LINK_TO_SEARCH,
    LINK_TO_DASHBOARD,
    LINK_TO_REPORT,
    LINK_TO_CUSTOM_URL,
    EDIT_TOKENS,
} from 'dashboard/containers/editor/drilldown/drilldownNames';
import { stringNotEmpty } from 'dashboard/containers/utils/validators';
import { DEBUG } from 'util/env';
import { getReactUITheme, getReactTimeRangeTheme } from 'util/theme_utils';
import { TOKEN_OPTION } from 'dashboard/containers/editor/drilldown/search/timeRangeOptionNames';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    initialize({ settings, eventManager, model, collection = {} }, ...options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.eventManager = eventManager;
        this.settings = settings;
        this.model = model;
        this.collection = collection;
        const middlewares = [thunkMiddleware];

        if (DEBUG) {
            const loggerMiddleware = createLogger({
                actionTransformer: action => Object.assign({}, action, {
                    type: String(action.type),
                }),
                collapsed: true,
            });
            middlewares.push(loggerMiddleware);
        }

        this.store = createStore(
            reducers,
            createInitialState({
                model: this.model,
                eventManager: this.eventManager,
            }),
            applyMiddleware(...middlewares),
        );
        this.updateSettingFromState = this.updateSettingFromState.bind(this);
        this.remove = this.remove.bind(this);
        this.bootstrap();
    },
    bootstrap() {
        this.store.dispatch(fetchTimeRangePresets({
            app: this.model.application.get('app'),
            owner: this.model.application.get('owner'),
            count: -1,
        }));
        this.store.dispatch(fetchApps());
        this.store.dispatch(fetchDashboards({
            app: this.store.getState().forms[LINK_TO_DASHBOARD].activeApp,
        // the reason we do validateLinkToDashboard here instead of doing it in `createInitialState`
        // is because this validation needs the list of dashboards which needs be fetched.
        // In general for any link that we don't 100% recognize, we will treat it as a custom url.
        })).then(() => this.store.dispatch(validateLinkToDashboard()));
        this.store.dispatch(fetchReports({
            app: this.store.getState().forms[LINK_TO_REPORT].activeApp,
        }));
    },
    validate() {
        const hasError = errors => (
            _.values(errors).some(error => (error !== ''))
        );
        const state = this.store.getState();
        let errors;
        let formState;
        switch (state.activeAction) {
            case NO_DRILLDOWN:
                return true;
            case LINK_TO_SEARCH:
                formState = state.forms[LINK_TO_SEARCH];
                if (formState.activeOption === 'custom') {
                    errors = {
                        searchError: stringNotEmpty(formState.search),
                    };
                    if (formState.activeTimeRangeOption === TOKEN_OPTION) {
                        Object.assign(errors, {
                            earliestTokenError: stringNotEmpty(
                                formState.activeTimeRangeToken.earliest),
                            latestTokenError: stringNotEmpty(
                                formState.activeTimeRangeToken.latest),
                        });
                    }
                    if (hasError(errors)) {
                        this.store.dispatch(updateLinkToSearchSetting(errors));
                        return false;
                    }
                }
                return true;
            case LINK_TO_DASHBOARD:
                formState = state.forms[LINK_TO_DASHBOARD];
                errors = {
                    activeAppError: stringNotEmpty(formState.activeApp),
                    activeDashboardError: stringNotEmpty(formState.activeDashboard),
                };
                if (hasError(errors)) {
                    this.store.dispatch(updateLinkToDashboardSetting(errors));
                    return false;
                }
                return true;
            case LINK_TO_REPORT:
                formState = state.forms[LINK_TO_REPORT];
                errors = {
                    activeAppError: stringNotEmpty(formState.activeApp),
                    activeReportError: stringNotEmpty(formState.activeReport),
                };
                if (hasError(errors)) {
                    this.store.dispatch(updateLinkToReportSetting(errors));
                    return false;
                }
                return true;
            case LINK_TO_CUSTOM_URL:
                formState = state.forms[LINK_TO_CUSTOM_URL];
                errors = {
                    urlError: stringNotEmpty(formState.url),
                };
                if (hasError(errors)) {
                    this.store.dispatch(updateLinkToURLSetting(errors));
                    return false;
                }
                return true;
            case EDIT_TOKENS:
                formState = state.forms[EDIT_TOKENS];

                if (_.filter(formState.items, item => item.type && item.token).length === 0) {
                    errors = {
                        error: _('Should have at least one token.').t(),
                    };
                }

                if (hasError(errors)) {
                    this.store.dispatch(updateTokensSetting(errors));
                    return false;
                }
                return true;
            default:
                return true;
        }
    },
    updateSettingFromState(editorDialog) {
        const state = this.store.getState();
        if (state.isSupported) {
            if (this.validate(state)) {
                applyState({
                    state,
                    settings: this.settings,
                    model: this.model,
                    eventManager: this.eventManager,
                });
            } else {
                return;
            }
        }
        editorDialog.close();
    },
    getComponent() {
        return (
            <BackboneProvider store={this.store} model={this.model} collection={this.collection}>
                <DrilldownContainer
                    onApply={this.updateSettingFromState}
                    onClose={() => { _.delay(this.remove, 300); }}
                />
            </BackboneProvider>
        );
    },
    getTheme() {
        return { ...getReactTimeRangeTheme(), ...getReactUITheme() };
    },
});
