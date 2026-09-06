# Section 6 - Data Quality and Reliability

Data quality is the degree to which data is fit for its intended use. Data reliability is the engineering practice of making that quality consistent over time. If processing turns raw data into information, quality and reliability are what make that information trustworthy.

Quality is not the same as cleaning. Cleaning happens during transformation: casting types, standardizing values, removing obvious defects, and applying business logic. Data quality in the operational sense is broader. It defines the assertions, checks, monitoring, ownership, and incident response needed to stop bad data from silently reaching consumers.

The goal is not perfect data. The goal is known, measured, communicated trust. A dataset used for exploratory analysis may tolerate rough edges. A dataset used for trading, regulatory reporting, billing, or executive decisions needs much stronger controls.

## Dimensions of Data Quality

| Dimension | Question | Example test |
| --- | --- | --- |
| Completeness | Is expected data present? | no missing daily partitions |
| Accuracy | Does data reflect reality? | totals reconcile to source |
| Validity | Does data follow rules? | email format is valid |
| Consistency | Do datasets agree? | customer IDs match across tables |
| Timeliness | Is data available when needed? | table refreshed by 08:00 |
| Uniqueness | Are duplicates controlled? | primary key is unique |
| Integrity | Are relationships valid? | every order has a customer |

Quality is contextual. A dataset can be good enough for exploratory analysis but not acceptable for regulatory reporting.

For market, pricing, or fundamental datasets, these dimensions become concrete. A price table may need tests for missing securities, stale values, negative prices, duplicated vendor records, invalid currency codes, suspicious day-over-day moves, and reconciliation against source delivery counts. The exact tests should follow the use case, not a generic checklist.

[[REPORTKIT-VISUAL:fig:sec06-quality-loop]]

## Data Quality and Data Observability

Data quality and data observability are related but distinct.

Data quality is prescriptive. It asks whether data satisfies known rules: primary keys should be unique, prices should be positive, required partitions should exist, and foreign keys should match dimensions.

Data observability is descriptive. It monitors the behavior and health of data, pipelines, and metadata over time. It catches unusual patterns even when no specific rule was written in advance.

Common observability signals include:

- freshness: whether data arrived and updated on time;
- volume: whether row counts, file counts, or event counts are within expected ranges;
- schema: whether columns, types, and nested structures changed;
- distribution: whether values shifted unexpectedly;
- lineage: which upstream systems and downstream consumers are affected;
- operational status: whether jobs, retries, runtimes, and resources behaved normally.

The difference matters. A table can pass every static test and still be suspicious if today's row count is 90 percent below normal. Conversely, an anomaly alert may be legitimate business activity rather than a data defect. Quality systems need both assertions and behavioral monitoring.

## Testing Data as Code

Data tests can run at many points:

- source checks before ingestion;
- schema checks during ingestion;
- transformation checks after each model;
- reconciliation checks against source systems;
- anomaly checks on trends and distributions;
- contract checks before publishing to consumers.

Common tests include row counts, null checks, uniqueness checks, accepted value checks, referential integrity checks, freshness checks, and custom business rules.

Treat these checks as code. They should be version-controlled, reviewed, run automatically, and tied to clear failure behavior. Some failures should block publication. Some should warn owners. Some should create incidents only if the affected dataset is business-critical.

Useful test categories include:

| Test type | Purpose | Example |
| --- | --- | --- |
| Schema test | Protect structure | column exists and has expected type |
| Constraint test | Protect basic validity | `price > 0` |
| Grain test | Protect row meaning | trade ID is unique |
| Relationship test | Protect joins | every fact row has a matching dimension key |
| Reconciliation test | Compare against source | loaded records match vendor delivery count |
| Freshness test | Protect timeliness | table updated within two hours |
| Distribution test | Detect unusual behavior | volume is within historical range |
| Business-rule test | Protect domain logic | cancelled orders should not contribute to recognized revenue |

## Shift-Left Quality

Shift-left quality means moving checks earlier in the lifecycle. Instead of waiting for a production dashboard to reveal bad data, teams test source contracts, schemas, transformation logic, and representative datasets before changes are deployed.

Examples include:

- validating source schemas at the ingestion boundary;
- running dbt tests in continuous integration before merging model changes;
- testing transformation logic against small fixture datasets;
- checking that a pull request does not break downstream contracts;
- reviewing metric definition changes before dashboards update;
- validating API or event schema changes before producers deploy them.

Shift-left testing does not replace production monitoring. Some failures only appear with real volumes, real late data, real source behavior, and real operational timing. The point is to catch preventable failures earlier and reserve production alerts for issues that truly need operational response.

## Monitoring and Alerting

Tests are only useful if failures reach the right people with enough context. Alerts should explain:

- what failed;
- when it failed;
- what data is affected;
- which consumers may be impacted;
- whether the issue is new or recurring;
- where to find logs and ownership information.

Too many low-value alerts create alert fatigue. A mature system prioritizes alerts by business impact.

Good alerting design asks:

- Is this dataset business-critical?
- Is the failure actionable?
- Who owns the fix?
- Should downstream publication stop?
- Does the alert include enough context for triage?
- Is this a new failure or a recurring noisy check?

High-signal checks usually protect grain, freshness, volume, source reconciliation, schema compatibility, and critical business rules. Low-signal checks often encode brittle thresholds without domain context.

## Incident Management

Data incidents should be handled with the same seriousness as software incidents when they affect business-critical outputs. A good incident process includes detection, triage, mitigation, communication, resolution, and post-incident learning.

Post-incident reviews should ask:

- Why did the issue happen?
- Why was it not caught earlier?
- How long was incorrect data available?
- Which consumers were affected?
- What change would prevent recurrence?
- What documentation or ownership was missing?

## Quality Tooling Landscape

| Tool category | Purpose | Examples |
| --- | --- | --- |
| Transformation tests | Run checks close to modeled data | dbt tests, custom SQL tests |
| Validation frameworks | Express richer expectations | Great Expectations, Soda, Deequ |
| Observability platforms | Monitor freshness, volume, schema, lineage, anomalies | Monte Carlo, Bigeye, Metaplane, Datadog |
| Orchestrator alerts | Track job failures and lateness | Airflow, Dagster, Prefect, cloud schedulers |
| Warehouse checks | Query data directly for assertions | SQL, stored procedures, scheduled queries |
| Incident tools | Route and manage response | PagerDuty, Slack, Jira, ServiceNow |

Tooling does not create trust by itself. Trust comes from meaningful checks, clear ownership, good runbooks, and a habit of learning from incidents.

## Capstone Continuation: Operationalizing Trust

The final core milestone consumes the outputs from Sections 2 through 4: the raw event files and manifest, the `curated_trades` table, `stg_trades`, `fct_trades`, and `fct_hourly_ohlcv`. It does not treat a successful job status as proof that the data is correct.

The quality checks use the same project contract throughout:

- The source is Binance Spot `BTCUSDT` trade data, with logical key `(exchange_name, asset_symbol, source_trade_id)`.
- `event_timestamp` records when the trade happened; `ingested_at` records when the producer received the event and assigned its envelope. Both are timezone-aware UTC timestamps; durable file-write time is tracked as `landed_at` in the manifest.
- `event_date` and `event_hour` are event-time partitions. Late events may revise an older partition, so checks run over a documented lookback window and only finalize an hourly interval after the allowed-lateness period.
- `stg_trades` and `fct_trades` have one row per unique trade key. `fct_hourly_ohlcv` has one row per exchange, asset, and UTC hour; its row count should not be compared directly with the trade fact's row count.

One possible implementation:

1. Run dbt tests in continuous integration against a small DuckDB dataset before model changes are merged.
2. Add schema and grain tests to `stg_trades` and `fct_trades`.
3. Add business-rule tests: price and quantity should be positive, timestamps should be sane, and trade identifiers should be non-null.
4. Add OHLCV tests: high price should be greater than or equal to low, open, and close prices.
5. Add freshness checks for the distinct clocks: compare the latest manifest or table `landed_at` with the expected pipeline schedule, measure the gap between `ingested_at` and `event_timestamp` as source delay, and compare `event_timestamp` with a source heartbeat or an active-source expectation. A quiet exchange is not automatically an ingestion failure.
6. Add volume checks: compare current finalized UTC-hour trade counts with a documented historical baseline, allowing for market-activity changes and the initial warm-up period.
7. Add reconciliation checks for each closed event-time interval. Verify that accepted raw attempts plus quarantined records explain all received records; count duplicate accepted attempts separately; then verify that the distinct trade-key count in `stg_trades` agrees with `fct_trades`, and that the sum of `trade_count` in finalized hourly aggregates agrees with the fact table for the same interval.
8. Quarantine malformed records under a path such as `s3://crypto-lake/quarantine/trades/event_date=YYYY-MM-DD/event_hour=HH/`, retaining the raw payload, `ingested_at`, and an actionable error code instead of silently dropping records.
9. Document owners, expected refresh times, the allowed-lateness and lookback policies, and failure response steps.
10. Publish or expose the curated models only after blocking checks pass; route warning-level anomalies to owners with enough context for investigation.

Avoid hardcoded thresholds without thought. A rule such as `price < 100000` may be sensible today and wrong later. Prefer thresholds tied to domain logic, source specifications, or historical distributions, with room for legitimate regime changes.

## Capstone Milestone Map

| Milestone | Consumes | Produces | Handoff condition |
| --- | --- | --- | --- |
| Ingest | Binance Spot `BTCUSDT` events | Raw payloads, normalized envelope, UTC timestamps, manifest, replay path | Files and manifest are durable; offsets are committed only after successful writes |
| Store | Section 2 raw landing and manifest | `curated_trades` with one row per unique trade key, documented schema and location | Curated writes are retry-safe; late events can update the correct event-time partition |
| Model | `curated_trades` | `stg_trades`, `fct_trades`, and `fct_hourly_ohlcv` with declared grains | Incremental lookback and aggregate finalization rules are documented |
| Operationalize trust | Raw and modeled outputs | Test results, freshness and volume signals, reconciliation evidence, quarantine records, ownership and runbook | Blocking failures prevent publication; warnings and incidents reach the responsible owner |

The completed capstone is therefore more than a set of tables. It is a reproducible path from a source event to a documented analytical result, with enough evidence to explain what arrived, what was accepted, what was delayed or quarantined, and which outputs consumers can trust.

## Quality and Reliability Checklist

Before publishing a production dataset, define:

- the intended consumers and use cases;
- the quality dimensions that matter most;
- the expected grain and primary keys;
- freshness expectations;
- source reconciliation requirements;
- schema compatibility rules;
- valid ranges and accepted values;
- anomaly detection signals;
- blocking versus warning failures;
- ownership and escalation paths;
- downstream impact when data is delayed or wrong;
- incident review and prevention process.
