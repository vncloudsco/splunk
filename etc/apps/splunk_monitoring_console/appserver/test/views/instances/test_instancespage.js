define(
    [
        'backbone',
        'models/classicurl',
        'splunkjs/mvc',
        'splunk_monitoring_console/views/instances/Master',
        'mocks/collections/services/configs/MockCoreVisualizations'
    ],
    function(
          Backbone,
          classicurl,
          mvc,
          MasterView,
          MockCoreVisualizations
        ) {
      var mockModel = {
        classicurlDfd: new Backbone.Model(),
        appLocal: new Backbone.Model(),
        application: new Backbone.Model(),
        earliestModel: new Backbone.Model(),
        latestModel: new Backbone.Model()
      };

      suite('Instances page', function() {
        setup(function() {
          MockCoreVisualizations.loadMockCoreVisualizations();
        });
        teardown(function() {
          delete this.masterView;
          mvc.Components.revokeInstance('groupDropdown');
          mvc.Components.revokeInstance('smcGetGroups');
          mvc.Components.revokeInstance('instanceSearchManager');
          mvc.Components.revokeInstance('instancesTable');
          classicurl.off();
          classicurl.clear();
          MockCoreVisualizations.reset();
        });

        test('no url parameter', function() {
          this.masterView = new MasterView({
            model: mockModel
          });
          assert.equal(this.masterView.groupDropdownDefault, '*', 'this.groupDropdownDefault');

          classicurl.on('change', function() {
            if (classicurl.get('group') == undefined) { return; }
            assert.equal(classicurl.get('group'), this.masterView.groupDropdownView.val(), 'select an option: ' + JSON.stringify(classicurl.attributes));
            assert.equal(this.description, undefined, 'this.description');
          }.bind(this));
          this.masterView.groupDropdownView.val('dmc_group_indexer');
          this.masterView.groupDropdownView.val('dmc_search_head');
          this.masterView.groupDropdownView.val('dmc_customgroup_anewgroup');
          this.masterView.groupDropdownView.val('*');
        });

        test('Test only group parameter presents', function() {
          classicurl.set({
            group: 'dmc_group_indexer'
          });
          this.masterView = new MasterView({
            model: mockModel
          });
          assert.equal(this.masterView.groupDropdownDefault, 'dmc_group_indexer', 'this.groupDropdownDefault');

          classicurl.on('change', function() {
            if (classicurl.get('group') == undefined) { return; }
            assert.equal(classicurl.get('group'), this.masterView.groupDropdownView.val(), 'select an option: ' + JSON.stringify(classicurl.attributes));
            assert.equal(this.description, undefined, 'this.description');
          }.bind(this));
          this.masterView.groupDropdownView.val('dmc_group_indexer');
          this.masterView.groupDropdownView.val('dmc_search_head');
          this.masterView.groupDropdownView.val('dmc_customgroup_anewgroup');
          this.masterView.groupDropdownView.val('*');
        });

        test('Test only search parameters present', function() {
          classicurl.set({
            earliest: '500',
            latest: '0',
            search: 'index=_internal'
          });
          this.masterView = new MasterView({
            model: mockModel
          });
          assert.equal(this.masterView.groupDropdownDefault, '-----', 'this.groupDropdownDefault');

          classicurl.on('change', function() {
            if (classicurl.get('group') == undefined) { return; }
            assert.equal(classicurl.get('group'), this.masterView.groupDropdownView.val(), 'select an option: ' + JSON.stringify(classicurl.attributes));
            assert.equal(this.description, classicurl.get('description'), 'this.description');
          }.bind(this));
          this.masterView.groupDropdownView.val('dmc_group_indexer');
          this.masterView.groupDropdownView.val('dmc_search_head');
          this.masterView.groupDropdownView.val('dmc_customgroup_anewgroup');
          this.masterView.groupDropdownView.val('*');
        });

        test('Test both group and search parameters present', function() {
          classicurl.set({
            group: 'dmc_group_indexer',
            earliest: '500',
            latest: '0',
            search: 'index=_internal'
          });
          this.masterView = new MasterView({
            model: mockModel
          });
          assert.equal(this.masterView.groupDropdownDefault, 'dmc_group_indexer', 'this.groupDropdownDefault');
          classicurl.on('change', function() {
            if (classicurl.get('group') == undefined) { return; }
            assert.equal(classicurl.get('group'), this.masterView.groupDropdownView.val(), 'select an option: ' + JSON.stringify(classicurl.attributes));
            assert.equal(this.description, classicurl.get('description'), 'this.description');
          }.bind(this));
          this.masterView.groupDropdownView.val('dmc_group_indexer');
          this.masterView.groupDropdownView.val('dmc_search_head');
          this.masterView.groupDropdownView.val('dmc_customgroup_anewgroup');
          this.masterView.groupDropdownView.val('*');
        });

        test('Test user selection when no url parameter but has search parameter', function() {
          classicurl.set({
            earliest: '500',
            latest: '0',
            search: 'index=_internal'
          });
          this.masterView = new MasterView({model: mockModel});
          assert.equal(this.masterView.groupDropdownDefault, '-----', 'this.groupDropdownDefault before selecting');
          assert.equal(classicurl.get('group'), undefined, 'classicurl before selecting');
          assert.notEqual(classicurl.get('search'), undefined, 'classicurl before selecting');

          classicurl.on('change:group', function(val) {
            assert.equal(classicurl.get('group'), 'dmc_group_indexer', 'classicurl after selecting Indexer option');
            classicurl.off();
          });
          this.masterView.groupDropdownView.val('dmc_group_indexer');

          classicurl.on('change', function() {
            assert.equal(classicurl.get('group'), undefined, 'classicurl after selecting DRILLDOWN option');
            classicurl.off();
          })
          this.masterView.groupDropdownView.val('-----');

          classicurl.on('change:group', function() {
            assert.equal(classicurl.get('group'), 'dmc_group_search_head', 'classicurl after selecting Search Head option');
            classicurl.off();
          })
          this.masterView.groupDropdownView.val('dmc_group_search_head');

          classicurl.on('change:group', function() {
            assert.equal(classicurl.get('group'), '*', 'classicurl after selecting All option');
            classicurl.off();
          })
          this.masterView.groupDropdownView.val('*');
        });
      });
    }
);
