import _ from 'underscore';
import PropTypes from 'prop-types';
import React from 'react';
import ItemSelector from 'dashboard/components/shared/ItemSelector';
import Parameters from 'dashboard/components/editor/drilldown/dashboard/Parameters';
import Advanced from 'dashboard/components/editor/drilldown/dashboard/AdvancedSection';
import PreviewURL from 'dashboard/components/editor/drilldown/dashboard/PreviewURL';
import OpenInNewTab from 'dashboard/components/shared/OpenInNewTab';
import Link from '@splunk/react-ui/Link';
import { createTestHook } from 'util/test_support';

const DashboardActionEditor = ({
    activeApp,
    activeAppError,
    apps,
    isFetchingApps,
    onAppChange,
    activeDashboard,
    activeDashboardError,
    dashboards,
    isFetchingDashboards,
    onDashboardChange,
    onTargetChange,
    target,
    params,
    onParamsChange,
    previewLink,
    candidateTokens,
    learnMoreLinkForTokens,
}) =>
    <div {...createTestHook(module.id)}>
        <ItemSelector
            label={_('App').t()}
            activeItem={activeApp}
            items={apps}
            isLoading={isFetchingApps}
            onChange={onAppChange}
            filter
            error={activeAppError}
            {...createTestHook(null, 'dashboardAppSelector')}
        />
        <ItemSelector
            label={_('Dashboard').t()}
            activeItem={activeDashboard}
            items={dashboards}
            isLoading={isFetchingDashboards}
            onChange={onDashboardChange}
            filter
            error={activeDashboardError}
            {...createTestHook(null, 'dashboardSelector')}
        />
        <OpenInNewTab
            value={target}
            onClick={onTargetChange}
        />
        <Advanced active={params.filter(param => param.key).length > 0}>
            <Parameters
                label={_('Parameters').t()}
                items={params}
                onChange={onParamsChange}
                keyPlaceholder=""
                valuePlaceholder=""
                candidateTokens={candidateTokens}
                help={(
                    <div>
                        {_('Use parameters to set token values in the target dashboard. For example, ' +
                        'form.host = $click.value2$ or host = $row.host$').t()}
                        {' '}
                        <Link
                            to={learnMoreLinkForTokens}
                            openInNewContext
                        >{_('Learn more').t()}</Link>
                    </div>)}
            />
            <PreviewURL url={previewLink} />
        </Advanced>
    </div>;

DashboardActionEditor.propTypes = {
    activeApp: PropTypes.string.isRequired,
    activeAppError: PropTypes.string,
    apps: PropTypes.arrayOf(PropTypes.object).isRequired,
    isFetchingApps: PropTypes.bool.isRequired,
    onAppChange: PropTypes.func.isRequired,
    activeDashboard: PropTypes.string,
    activeDashboardError: PropTypes.string,
    dashboards: PropTypes.arrayOf(PropTypes.object).isRequired,
    isFetchingDashboards: PropTypes.bool.isRequired,
    onDashboardChange: PropTypes.func.isRequired,
    target: PropTypes.string.isRequired,
    onTargetChange: PropTypes.func.isRequired,
    params: PropTypes.arrayOf(PropTypes.shape({
        key: PropTypes.string,
        value: PropTypes.string,
    })).isRequired,
    onParamsChange: PropTypes.func.isRequired,
    previewLink: PropTypes.shape({
        label: PropTypes.string.isRequired,
        value: PropTypes.string.isRequired,
    }).isRequired,
    candidateTokens: PropTypes.arrayOf(PropTypes.shape({
        token: PropTypes.string.isRequired,
        description: PropTypes.string,
    })).isRequired,
    learnMoreLinkForTokens: PropTypes.string.isRequired,
};

DashboardActionEditor.defaultProps = {
    activeAppError: '',
    activeDashboard: '',
    activeDashboardError: '',
};

export default DashboardActionEditor;
