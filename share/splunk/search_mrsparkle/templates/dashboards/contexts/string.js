<%page args="ctx,runOnSubmit=True,cancelOnUnload=False" />\
<%
options = dict()
for key,opt in {'searchEarliestTime':'earliest_time','searchLatestTime':'latest_time', 'earliestTime': 'earliest_time', 'latestTime': 'latest_time', 'sampleRatio': 'sample_ratio'}.items():
    if hasattr(ctx,key):
        options[opt] = getattr(ctx,key)
options['search'] = ctx.normalizedSearchCommand()
if hasattr(ctx, 'statusBuckets'):
    options['status_buckets'] = ctx.statusBuckets
else:
    options['status_buckets'] = 0
options['cancelOnUnload'] = cancelOnUnload
%>\
new SearchManager({
            "id": ${ctx.id|json_decode},
        % for k,v in options.items():
            ${k|json_decode}: ${json_decode(v)|n},
        % endfor
            "app": utils.getCurrentApp(),
            "auto_cancel": 90,
            "preview": true,
            "tokenDependencies": {
                % if hasattr(ctx.tokenDeps, 'depends') and hasattr(ctx.tokenDeps, 'rejects'):
                    "depends": ${ctx.tokenDeps.depends|json_decode},
                    "rejects": ${ctx.tokenDeps.rejects|json_decode}
                % elif hasattr(ctx.tokenDeps, 'depends'):
                    "depends": ${ctx.tokenDeps.depends|json_decode}
                % elif hasattr(ctx.tokenDeps, 'rejects'):
                    "rejects": ${ctx.tokenDeps.rejects|json_decode}
                % endif
            },
            "runWhenTimeIsUndefined": false
        }, {tokens: true});

