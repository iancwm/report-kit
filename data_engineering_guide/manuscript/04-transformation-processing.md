# Section 4 - Data Transformation and Processing

Transformation and processing are where raw data becomes useful information. Ingestion and storage preserve data; this stage imposes structure, meaning, and business logic. It includes cleaning, standardizing, deduplicating, joining, aggregating, modeling, and computing derived datasets for analytics, machine learning, applications, and reporting.

This is often the most intellectually demanding part of data engineering because the engineer must understand both systems and semantics. A technically efficient pipeline can still be wrong if it joins at the wrong grain, applies the wrong business definition, loses late-arriving corrections, or silently duplicates facts.

## ETL and ELT

ETL stands for extract, transform, load. Data is transformed before it enters the target analytical system. ELT stands for extract, load, transform. Data is loaded first and transformed inside the warehouse, lakehouse, or processing engine.

| Pattern | Description | Common use |
| --- | --- | --- |
| ETL | Transform before loading into the target platform | Strict preprocessing, legacy systems, sensitive data filtering, non-SQL workloads |
| ELT | Load raw data first, then transform inside the analytical platform | Cloud warehouses, lakehouses, SQL-centric analytics |

ELT is common in modern platforms because storage is relatively cheap, compute is elastic, and analytical engines are powerful. Keeping raw data also supports reprocessing when business logic changes. If a metric definition changes, the team can rerun transformation logic against preserved raw data instead of going back to the source system.

ETL is still useful when data must be transformed before landing, when raw data cannot be stored for privacy or regulatory reasons, when the source emits data in a form that requires specialized parsing, or when the transformation is better handled by a dedicated compute engine such as Spark, Flink, or a machine learning pipeline.

The practical rule is not "always use ELT." It is: preserve raw data when safe and affordable, make transformation logic version-controlled and testable, and run computation where it is most reliable and cost-effective.

[[REPORTKIT-VISUAL:fig:sec04-transformation-flow]]

## Cleaning and Standardization

Cleaning tasks include:

- normalizing date and timestamp formats;
- converting currencies and units;
- trimming invalid strings;
- deduplicating records;
- handling nulls;
- validating identifiers;
- standardizing categorical values;
- parsing nested structures.

Cleaning should not silently erase important facts. For example, replacing every missing value with zero can create misleading analytics. A better approach is to preserve missingness, document assumptions, and create explicit derived fields where needed.

## Distributed Processing Concepts

Processing means executing computation over data. Some transformations fit comfortably inside a single database or a single-machine engine such as DuckDB or Polars. Others require distributed processing across many machines.

A useful mental model is map and reduce:

- map operations apply independently to records or partitions, such as parsing JSON, casting fields, filtering rows, or calculating row-level derived columns;
- reduce operations combine records, such as aggregations, joins, deduplication, ranking, and window functions.

The expensive part of distributed processing is usually data movement. A shuffle occurs when data must be redistributed across machines, often because records with the same key need to meet in the same partition. Joins, group-bys, distinct operations, and some window functions can trigger shuffles.

For Spark, Flink, Beam, and similar engines, good performance often depends on:

- filtering early;
- selecting only needed columns;
- avoiding unnecessary joins;
- joining on well-distributed keys;
- using broadcast joins when one table is small enough;
- choosing appropriate partition counts;
- avoiding operations that pull large data back to a driver process;
- writing outputs in file sizes and partitions suited to downstream queries.

Engines such as Spark use lazy evaluation: they build a logical plan before execution and optimize that plan when an action runs. This allows predicate pushdown, projection pushdown, join reordering, and other optimizations. The engineer should still inspect plans and measure performance. Optimizers are powerful, but they cannot fix unclear business logic, poor keys, bad partitioning, or unnecessary materialization.

## Batch, Streaming, and Real-Time Processing

Data processing can happen on a schedule, continuously, or in response to events.

Batch processing handles data in bounded chunks. A job may run hourly, daily, or weekly. Batch is often simpler, cheaper, and easier to debug than streaming.

Batch is appropriate when:

- data does not need to be available immediately;
- source systems provide periodic extracts;
- transformations require large joins or historical context;
- reproducibility and auditability are more important than low latency.

Streaming processing handles data continuously as it arrives. It is useful for fraud detection, monitoring, personalization, IoT, alerts, and operational analytics.

Streaming introduces challenges:

- events can arrive late or out of order;
- failures can cause duplicates;
- state must be managed over time;
- exactly-once behavior is difficult and system-specific;
- testing and replay require careful design.

"Real-time" is often used loosely. Many business needs are actually near real-time. A fraud decision may need milliseconds. A support dashboard may need one-minute freshness. An executive dashboard may be fine with hourly updates.

| Requirement | Typical meaning |
| --- | --- |
| Real-time | Milliseconds to seconds |
| Near real-time | Seconds to minutes |
| Frequent batch | Minutes to hours |
| Periodic batch | Daily or longer |

Lower latency usually increases complexity and cost. The right design meets the real business need, not the most impressive technical target.

## Idempotent and Incremental Transformations

Idempotency means that running the same transformation with the same input produces the same output. This matters because recurring jobs fail, retry, backfill, and rerun.

Unsafe pattern:

```sql
INSERT INTO fct_trades
SELECT *
FROM stg_trades
WHERE event_date = :target_event_date;
```

If this job runs twice, it may duplicate rows.

The parameter is a UTC event date, and the model should replace or merge the complete bounded interval rather than append a second copy. The same principle applies to a lookback window used to catch late events.

Safer patterns include:

- create or replace a complete derived table;
- overwrite a complete partition after the replacement data is ready;
- merge by a stable business key;
- delete and insert a bounded date range inside a transaction;
- write to a new table version and atomically swap or commit it.

Incremental processing avoids recomputing all history every run. A high-water mark tracks the furthest processed timestamp, identifier, offset, or table version. Strict watermarks can miss late-arriving records, so many pipelines reprocess a lookback window, such as the last three days, and combine it with idempotent merge or partition overwrite logic.

For streaming transformations, the equivalent concepts are checkpoints, offsets, event time, watermarks, and state. A streaming aggregation may keep a time window open for late events before finalizing output.

## Joins and Enrichment

Data becomes more valuable when connected. Orders become more useful when joined to customers, products, promotions, and shipping events. Enrichment may also add external reference data such as geographies, exchange rates, taxonomies, or risk scores.

Joins require careful attention to:

- key uniqueness;
- many-to-many relationships;
- slowly changing dimensions;
- time validity;
- missing matches;
- duplicate amplification.

If a join unexpectedly increases row counts, it may be multiplying records. Row count tests before and after joins are simple but powerful safeguards.

## Grain

Grain is the meaning of one row in a dataset. It is the most important modeling decision in transformation.

Examples:

- one row per trade;
- one row per order line item;
- one row per customer per day;
- one row per asset per exchange per hour.

Every column in a model should match its grain. If a table is one row per trade, then trade price and quantity fit naturally. Daily volume does not, unless it is clearly a repeated contextual attribute and the duplication is intentional. If a table is one row per customer per day, then transaction-level columns do not belong unless they have been aggregated to that level.

Many analytical errors are grain errors. Joining a daily customer table to a transaction table without aggregating first may multiply rows and inflate metrics. Declaring grain before writing SQL prevents a surprising amount of damage.

## Aggregation and Metrics

Aggregation summarizes lower-grain data into higher-grain outputs. For example, order line items may be aggregated into daily revenue by product category.

Good metric definitions specify:

- the entity being measured;
- the grain of the output;
- inclusion and exclusion rules;
- time boundaries and timezone;
- handling of refunds, cancellations, and corrections;
- ownership and approval.

Metrics are organizational contracts, not just SQL expressions. Two teams can both calculate "active users" correctly according to their own definitions and still disagree because the definition was not shared.

## Dimensional Modeling

Data modeling structures data for use. Common modeling styles include normalized relational models, dimensional models, wide analytical tables, data vault models, and entity-centric models.

Dimensional modeling is especially common in analytics. It separates facts, which represent business events or measurements, from dimensions, which describe entities.

| Model element | Description | Example |
| --- | --- | --- |
| Fact table | Measurements or events | order line, payment, page view |
| Dimension table | Descriptive context | customer, product, date, region |
| Grain | Meaning of one row | one row per order line |
| Measure | Numeric value to aggregate | revenue, quantity, duration |

Fact tables are usually long and relatively narrow. They contain event keys, foreign keys, timestamps, and measures such as price, quantity, duration, balance, or revenue.

Common fact table types include:

- transaction facts, with one row per event;
- periodic snapshot facts, with one row per entity per time period;
- accumulating snapshot facts, with one row per process that changes as the process moves through stages.

Dimension tables contain descriptive attributes such as customer segment, product category, country, asset class, or exchange type. They are often wider and more descriptive than fact tables.

Surrogate keys are often used in dimensions to insulate analytical models from source-system keys. They are especially useful when the same business entity appears in multiple source systems, when natural keys can change, or when slowly changing dimensions are required. They are not magic, and they are not always required; the design should follow history, integration, and query needs.

A star schema places a fact table at the center and connects it directly to dimensions. This is usually easier for analysts and BI tools than a highly normalized schema. A snowflake schema further normalizes dimensions into subdimensions, which can reduce duplication but adds joins and complexity.

Good models make common questions easy and uncommon questions possible.

## Slowly Changing Dimensions

Dimension attributes change. A customer moves country, a product changes category, a security changes classification, or an account changes relationship manager. Slowly changing dimension techniques define how much history to preserve.

| Type | Behavior | Use case |
| --- | --- | --- |
| Type 1 | Overwrite the old value | Current-state reporting where history is not needed |
| Type 2 | Add a new row with validity dates | Point-in-time analysis and historical reporting |
| Type 3 | Add a previous-value column | Limited history for a small number of attributes |

Type 2 dimensions are powerful because they allow point-in-time joins. A fact can join to the dimension row that was valid when the event occurred. This is critical when historical meaning matters, but it adds complexity to keys, joins, and tests.

## Transformation Tooling Landscape

Different tools fit different transformation workloads.

| Tool | Best fit | Key ideas | Watch out for |
| --- | --- | --- | --- |
| dbt | SQL transformations in warehouses and lakehouses | models, refs, DAGs, tests, documentation | hardcoded table names, unclear grain, weak tests |
| Spark | distributed batch and large-scale transformations | DataFrames, SQL, partitions, shuffles, Catalyst | unnecessary shuffles, driver collection, poor partitioning |
| Flink | stateful stream processing | event time, state, watermarks, checkpoints | operational complexity and state management |
| Beam | portable batch and streaming pipelines | unified model, runners, windows | runner-specific behavior and debugging |
| DuckDB | local analytical SQL and prototyping | in-process OLAP, Parquet, SQL | not a distributed production warehouse |
| Polars | fast single-machine DataFrame processing | lazy plans, columnar execution, Rust engine | memory limits still matter |
| SQL warehouses | governed ELT and analytics | SQL, optimization, access control | cost, warehouse-specific syntax, lock-in |

dbt deserves special attention because it changed how many teams write transformations. Conceptually, dbt is a framework for managing SQL transformation code. A dbt model is usually a `SELECT` statement. dbt compiles that statement, resolves dependencies through `ref()` calls, runs models in dependency order, and supports tests and documentation.

dbt does not extract or load data. It assumes data already exists in the warehouse or lakehouse. It is mainly a transformation tool in an ELT architecture.

When using AI to generate transformation code, supervise the architecture:

- require the model grain to be stated;
- require explicit column lists rather than `SELECT *`;
- require idempotent materialization or merge logic;
- require tests for uniqueness, nulls, relationships, accepted values, and business rules;
- require `ref()` or equivalent dependency references rather than hardcoded table names;
- inspect joins for fan-out and unintended many-to-many relationships.

## Common Transformation Anti-Patterns

Common mistakes include:

- mixing grains inside one model;
- using `SELECT *` in production models;
- embedding business logic in ingestion instead of version-controlled transformation;
- creating one giant table that tries to serve every use case;
- using append-only inserts for recurring derived tables without deduplication;
- applying filters before preserving raw data;
- joining without checking row counts before and after;
- calculating metrics without documented definitions;
- hiding null handling, timezone assumptions, or currency conversions.

These errors are dangerous because they often produce plausible numbers. A pipeline can run successfully and still be analytically wrong.

## Capstone Continuation: Modeling the Crypto Lakehouse

The crypto lakehouse project can now be transformed into a small dimensional model. This stage consumes the `curated_trades` table produced in Section 3; it does not read directly from the exchange or infer fields from file paths. The goal is to let an analyst answer questions such as: what was the average hourly traded quantity for BTC on Binance over a requested UTC interval?

The modeling contract is:

- Input grain: `curated_trades` contains one row per unique `(exchange_name, asset_symbol, source_trade_id)`.
- Time: `event_timestamp`, `ingested_at`, `event_date`, and `event_hour` retain the UTC conventions established during ingestion and storage. `hour_start_utc` is derived from `event_timestamp`, not from the arrival time.
- Key and measures: `source_trade_id` identifies the exchange trade; `price` is USDT per BTC and `quantity` is BTC. The model does not invent a converted currency measure.
- Late data: incremental runs reprocess a documented event-time lookback window and merge or replace it idempotently. An hourly bar is considered final only after the project's allowed-lateness policy is satisfied.
- Output grain: `fct_trades` remains one row per trade, while `fct_hourly_ohlcv` has one row per `(exchange_name, asset_symbol, hour_start_utc)`.

One possible local architecture:

1. Use DuckDB as a local analytical engine.
2. Use dbt with a DuckDB adapter to manage SQL models, dependencies, tests, and documentation.
3. Read `curated_trades` from the local lakehouse, or its documented Parquet representation when a table format is not being used.
4. Build staging models that cast types, rename fields, deduplicate trades, and preserve one row per trade.
5. Build dimension models such as `dim_asset`, `dim_exchange`, and a date or time dimension if useful.
6. Build a transaction fact table, `fct_trades`, with one row per trade.
7. Build an hourly aggregate fact, `fct_hourly_ohlcv`, with one row per asset, exchange, and UTC hour.
8. Add tests for unique trade identifiers, positive prices and quantities, non-null timestamps, relationship integrity, and expected row counts.

The staging layer should keep the same grain as the raw trade feed: one row per trade. The hourly table deliberately changes the grain by aggregating trades into hourly OHLCV records.

Example aggregation in DuckDB-style SQL:

```sql
SELECT
    asset_symbol,
    exchange_name,
    date_trunc('hour', event_timestamp) AS hour_start_utc,
    arg_min(price, event_timestamp) AS open_price,
    max(price) AS high_price,
    min(price) AS low_price,
    arg_max(price, event_timestamp) AS close_price,
    sum(quantity) AS total_quantity,
    count(*) AS trade_count
FROM stg_trades
WHERE event_timestamp >= :start_timestamp_utc
  AND event_timestamp < :end_timestamp_utc
GROUP BY 1, 2, 3;
```

The interval uses an inclusive lower bound and exclusive upper bound, both in UTC. The exact SQL varies by engine. Some warehouses use different ordered aggregate functions for open and close prices. When multiple trades have the same event timestamp, use `source_trade_id` as a deterministic tie-breaker. The important point is conceptual: the model declares its grain, aggregates from a lower grain to a higher grain, and can be tested.

This project teaches:

- how to preserve raw data while building curated models;
- how to declare grain across staging, dimensions, and facts;
- how a transformation DAG runs models in dependency order;
- how idempotent materializations make reruns safe;
- how quality tests catch transformation bugs before they reach dashboards;
- how aggregation changes the meaning of one row.

## Transformation Output and Handoff

At the end of this stage, the project should expose:

- `stg_trades`, a typed and deduplicated one-row-per-trade model with the composite trade key and both UTC timestamps;
- `fct_trades`, the transaction-level fact used for detailed analysis;
- `fct_hourly_ohlcv`, an idempotently rebuilt or merged hourly aggregate with documented open, high, low, close, quantity, and count semantics;
- version-controlled model definitions and a declared event-time lookback policy for late data.

Section 6 consumes these models as data products. Its checks should compare raw, accepted, quarantined, and deduplicated counts using the declared grains; it should not expect the hourly aggregate's row count to equal the trade fact's row count.

## Transformation and Processing Checklist

Before implementing a transformation pipeline, define:

- the grain of each input and output model;
- the source-of-truth fields and business definitions;
- whether the model is full-refresh, incremental, or streaming;
- the idempotency strategy;
- the deduplication keys;
- the late-arriving data policy;
- the event-time timezone, interval boundaries, and lookback window;
- the join keys and expected cardinality;
- the aggregation level and metric definitions;
- the test suite and failure behavior;
- the compute engine and cost expectations;
- the partitioning and output layout;
- the documentation and ownership.

Transformation is successful when the output is not only technically valid, but semantically correct, reproducible, tested, and understandable.
