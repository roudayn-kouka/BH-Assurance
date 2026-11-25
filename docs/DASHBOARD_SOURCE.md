# Dashboard source for the Wave 2 pilot

Next-BH pins `web/BH-Assurance` to `394df01b2ce3fb5575a828049928885c76f3c31a` and records the dashboard upstream URL in `.gitmodules`. The upstream does not serve that commit. The pilot workflows leave submodules uninitialized and use the verified export below.

Wave 2 uses `a18e1e0fc402af64d63a16fba5532bc357d077e1`, the first dashboard revision pinned by Next-BH. It is available from the [documented upstream](https://github.com/roudayn-kouka/BH-Assurance/tree/a18e1e0fc402af64d63a16fba5532bc357d077e1). Use Git and Python 3.12 to export its React and Express sources into a new directory for isolated pilot work.

```sh
python3.12 -B scripts/prepare_dashboard_snapshot.py ../bh-dashboard-pilot-source
```

The export verifies the revision and includes application source, assets, configuration for building the source, and dependency lock files. The export selects individual files so upstream environment files, logs, installed dependencies, data, and bundled Git objects stay out of the pilot workspace. The historical validation handler can initiate email delivery. Use a synthetic pilot entry point when exercising approval or rejection.

The pilot export is prepared separately from the existing gitlink. [BH-8 source investigation](https://maiteai.atlassian.net/browse/BH-8)
