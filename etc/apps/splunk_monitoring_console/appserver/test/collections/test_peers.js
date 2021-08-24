define(
            [
                'underscore',
                'splunk_monitoring_console/collections/Peers',
                'util/qunit_utils'
            ],
            function (
                _,
                PeersCollection,
                qunitUtils
            ) {
                suite('Setup', function() {
                    util(qunitUtils.FakeXhrModule, {
                        setup: function() {
                            qunitUtils.FakeXhrModule.setup.call(this);

                            this.peers = new PeersCollection();
                            assert.ok(this.peers, 'We should get no exceptions');
                            assert.ok(true, 'module setup successful');
                        },
                        teardown: function() {
                            qunitUtils.FakeXhrModule.teardown.call(this);
                            this.peers.reset();
                            assert.ok(true, 'module teardown successful');
                        }
                    });

                    test("Test fetch", function () {
                        this.peers.fetch();
                        var request = this.requests[0];
                        this.verifyRequestArgs(
                            request,
                            {
                                output_mode: 'json',
                                search: 'name=dmc_*',
                                count: 1000
                            }, 
                            'correct default args including count'
                        );

                    });
                });
            }
    );

