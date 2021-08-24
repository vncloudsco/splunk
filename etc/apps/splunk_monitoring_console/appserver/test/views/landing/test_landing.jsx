import React from 'react';
import Bookmarks from 'splunk_monitoring_console/collections/Bookmarks';
import Metrics from 'splunk_monitoring_console/collections/Metrics';
import ServerInfo from 'models/services/server/ServerInfo';
import HealthDetailsModel from 'models/services/server/HealthDetails';
import ClusterConfigModel from 'models/services/cluster/Config';
import { configure, shallow } from 'enzyme';
import Landing from 'splunk_monitoring_console/views/landing/Landing';
import EnzymeAdapterReact16 from 'enzyme-adapter-react-16';

suite('Monitoring Console Landing Page', function () {
    setup(function () {
        configure({ adapter: new EnzymeAdapterReact16() });
        this.props = {
            application: {
                get: () => {},
            },
            serverInfo: new ServerInfo(),
            healthDetails: new HealthDetailsModel(),
            indexerClustering: new ClusterConfigModel(),
            bookmarks: new Bookmarks(),
            metrics: new Metrics(),
            indexes: 11,
        };
        this.wrapper = shallow(<Landing {...this.props} />);
        this.inst = this.wrapper.instance();

        assert.ok(this.wrapper, 'wrapper instantiated successfully');
    });
    teardown(function () {
        this.wrapper = null;
        this.inst = null;
        assert.ok(true, 'Teardown was successful');
    });
    test('Test rendering the Landing component', function () {
        assert.equal(
            this.wrapper.find('div[data-test-name="monitoring-console-landing"]').length,
            1, 'Landing page rendered');
        assert.equal(
            this.wrapper.find('Heading').length,
            5, 'All Headings rendered');
        assert.equal(
            this.wrapper.find('div[data-test-name="deployment-topology"]').length,
            1, 'Deployment topology section rendered');
        assert.equal(
            this.wrapper.find('div[data-test-name="deployment-metrics"]').length,
            1, 'Deployment metrics section rendered');
        assert.equal(
            this.wrapper.find('div[data-test-name="deployment-components"]').length,
            1, 'Deployment Components section rendered');
    });
});
