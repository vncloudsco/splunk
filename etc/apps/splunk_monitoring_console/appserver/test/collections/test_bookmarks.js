define(
[
    'underscore',
    'splunk_monitoring_console/collections/Bookmarks',
    'fixtures/monitoringconsole/Bookmarks.json',
    'util/qunit_utils'
],
function (
    _,
    BookmarksCollection,
    BookmarksFixture,
    qunitUtils
) {
    suite('Setup', function() {
        util(qunitUtils.FakeXhrModule, {
            setup: function() {
                qunitUtils.FakeXhrModule.setup.call(this);

                this.bookmarks = new BookmarksCollection();
                assert.ok(this.bookmarks, 'We should get no exceptions');
                assert.ok(true, 'module setup successful');
            },
            teardown: function() {
                qunitUtils.FakeXhrModule.teardown.call(this);
                this.bookmarks.reset();
                assert.ok(true, 'module teardown successful');
            }
        });

        test("test fetch", function () {
            this.bookmarks.fetch();
            var request = this.requests[0];
            this.verifyRequestArgs(
                request,
                {
                    output_mode: 'json',
                    count: -1,
                },
                'correct default args including count'
            );

        });
        test('test getBookmarks', function() {
            var bookmarks = this.bookmarks.getBookmarks();
            assert.equal(Object.keys(bookmarks).length, 0, 'There should be 0 bookmarks');

            var deferred = this.bookmarks.fetch();
            assert.notStrictEqual(deferred.state(), "rejected", 'request should not be rejected');
            assert.notStrictEqual(deferred.state(), "resolved", 'request should not be resolved');

            var request = this.requests[0];
            this.respondTo(request, JSON.stringify(BookmarksFixture))
            assert.notStrictEqual(deferred.state(), "rejected", 'request should not be rejected');
            assert.strictEqual(deferred.state(), "resolved", 'request should be resolved');

            bookmarks = this.bookmarks.getBookmarks();
            assert.equal(Object.keys(bookmarks).length, 2, 'should contain 2 bookmarks');
        });
    });
});

