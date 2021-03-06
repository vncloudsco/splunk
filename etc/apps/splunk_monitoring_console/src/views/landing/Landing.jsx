import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { gettext } from '@splunk/ui-utils/i18n';
import Heading from '@splunk/react-ui/Heading';
import Link from '@splunk/react-ui/Link';
import P from '@splunk/react-ui/Paragraph';
import Bookmark from 'splunk_monitoring_console/views/landing/bookmark/Bookmark';
import Anomalies from 'splunk_monitoring_console/views/landing/Anomalies';
import MetricsPanel from 'splunk_monitoring_console/views/landing/deploymentPanels/MetricsPanel';
import ComponentsPanel from 'splunk_monitoring_console/views/landing/deploymentPanels/ComponentsPanel';
import TopologyPanel from 'splunk_monitoring_console/views/landing/deploymentPanels/TopologyPanel';
import route from 'uri/route';
import './Landing.pcss';

class Landing extends Component {
    static propTypes = {
        appLocal: PropTypes.shape({}).isRequired,
        application: PropTypes.shape({
            get: PropTypes.func.isRequired,
        }).isRequired,
        serverInfo: PropTypes.shape({
            getProductName: PropTypes.func,
            getVersion: PropTypes.func,
        }).isRequired,
        healthDetails: PropTypes.shape({
            fetch: PropTypes.func,
            getAnomalies: PropTypes.func,
            getFeatures: PropTypes.func,
            models: PropTypes.arrayOf(PropTypes.shape({})),
            on: PropTypes.func,
        }).isRequired,
        indexerClustering: PropTypes.shape({}).isRequired,
        bookmarks: PropTypes.shape({
            fetch: PropTypes.func,
            updateBookmarks: PropTypes.func,
            getBookmarks: PropTypes.func,
            models: PropTypes.arrayOf(PropTypes.shape({})),
            on: PropTypes.func,
        }).isRequired,
        metrics: PropTypes.shape({
            fetch: PropTypes.func,
            models: PropTypes.arrayOf(PropTypes.shape({})),
            on: PropTypes.func,
            getMetrics: PropTypes.func,
            getEnabledMetrics: PropTypes.func,
        }).isRequired,
        indexes: PropTypes.number.isRequired,
    };

    /**
     * Render landing page.
     */
    render() {
        const {
            serverInfo,
            healthDetails,
            bookmarks,
        } = this.props;

        const learnMore = route.docHelp(
            this.props.application.get('root'),
            this.props.application.get('locale'),
            'learnmore.dmc.summary_dashboard',
        );

        return (
            <div
                data-test-name='monitoring-console-landing'
                className='overall-section'
            >
                <div
                    data-test-name='landing-navigation'
                    className='navigation-section'
                >
                    <Bookmark bookmarks={bookmarks} />
                </div>
                <div
                    data-test-name='landing-content'
                    className='content-section'
                >
                    <div
                        data-test-name='landing-heading-section'
                    >
                        <Heading
                            level={1}
                            data-test-name='landing-heading'
                            className='heading'
                        >
                            {gettext(`Overview of ${serverInfo.getProductName()} 
                                ${serverInfo.getVersion() || gettext('N/A')}`)}
                        </Heading>
                        <P
                            className='heading-description'
                            data-test-name='landing-heading-description'
                        >
                            {gettext(`The Summary dashboard integrates health status
                            information from the splunkd health report with monitoring console
                            features, such as Health Check, to let you monitor and investigate
                            issues with your deployment. `)}
                            <Link
                                to={learnMore}
                                openInNewContext
                            >
                                {gettext('Learn more')}
                            </Link>
                        </P>
                    </div>
                    <div
                        data-test-name='landing-anomalies-section'
                        className='anomalies-section'
                    >
                        <Heading
                            level={2}
                            data-test-name='anomalies-heading'
                            className='heading'
                        >
                            {gettext('Anomalies')}
                        </Heading>
                        <Anomalies anomalies={healthDetails.getAnomalies()} />
                    </div>
                    <div
                        data-test-name='landing-deployment-section'
                        className='deployment-section'
                    >
                        <div
                            data-test-name='deployment-topology'
                            className='deployment-sub-section-left'
                        >
                            <Heading
                                level={2}
                                data-test-name='topology-heading'
                                className='heading'
                            >
                                {gettext('Deployment Topology')}
                            </Heading>
                            <TopologyPanel
                                appLocal = {this.props.appLocal}
                                indexes = {this.props.indexes}
                                indexerClustering = {this.props.indexerClustering}
                            />
                        </div>
                        <div
                            data-test-name='deployment-metrics'
                            className='deployment-sub-section-center'
                        >
                            <Heading
                                level={2}
                                data-test-name='metrics-heading'
                                className='heading'
                            >
                                {gettext('Deployment Metrics')}
                            </Heading>
                            <MetricsPanel metrics={this.props.metrics} />
                        </div>
                        <div
                            data-test-name='deployment-components'
                            className='deployment-sub-section-right'
                        >
                            <Heading
                                level={2}
                                data-test-name='components-heading'
                                className='heading'
                            >
                                {gettext('Deployment Components')}
                            </Heading>
                            <ComponentsPanel features={healthDetails.getFeatures()} />
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}

export default Landing;
