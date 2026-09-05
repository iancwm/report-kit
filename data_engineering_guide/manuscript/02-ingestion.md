# Section 2 - Data Ingestion

Data ingestion is the on-ramp of the data lifecycle. It is the process of extracting data from source systems and moving it into a staging area, data lake, warehouse, lakehouse, or message broker. Its primary goals are fidelity, reliability, and controlled impact: move data from source to destination without losing it, corrupting it, duplicating it unexpectedly, or overwhelming either side.

Ingestion is often treated as a simple plumbing problem, but it is really a distributed systems problem. Source systems fail, networks partition, APIs throttle requests, schemas change, files arrive late, and destinations become unavailable. A good ingestion design makes these realities explicit and defines what the system should do when they happen.

For someone with coding proficiency and AI assistance, the most important skill is not memorizing connector syntax. It is knowing what constraints to specify: latency, volume, ordering, replayability, idempotency, delivery semantics, schema handling, security, and operational ownership.

## Extraction Methods

Common ingestion methods include:

- full extracts, where the entire dataset is copied each time;
- incremental extracts, where only new or changed records are copied;
- change data capture, where database changes are captured from logs;
- event ingestion, where systems publish events into a stream;
- file ingestion, where data arrives in object storage or file transfer locations;
- API ingestion, where data is pulled from service endpoints.

| Method | Strengths | Weaknesses |
| --- | --- | --- |
| Full extract | Simple and easy to reason about | Expensive for large data; can overwrite history |
| Incremental extract | Efficient for growing datasets | Needs reliable change tracking |
| Change data capture | Captures inserts, updates, deletes | Operationally complex; source-specific |
| Event ingestion | Near real-time and scalable | Requires event design and duplicate handling |
| File ingestion | Simple interface between systems | Files may be late, malformed, or duplicated |
| API ingestion | Works with SaaS and external services | Rate limits, pagination, auth, schema drift |

## Batch and Streaming Ingestion

The first design choice is usually whether the data should move in batches or continuously.

Batch ingestion reads data in bounded chunks at scheduled intervals, such as every hour or every day. It optimizes for throughput, cost, simplicity, and reproducibility. Batch jobs can group network calls, compress outputs, write efficient files, and rerun historical periods. The trade-off is latency: the data is stale between runs.

Streaming ingestion moves data continuously, either record by record or in micro-batches. It optimizes for freshness and event-driven use cases, such as fraud monitoring, market data, telemetry, personalization, and operational alerts. The trade-off is higher complexity. Streaming systems must handle long-running processes, network interruptions, duplicate events, out-of-order arrival, state management, and continuous compute cost.

| Requirement | Better fit | Reason |
| --- | --- | --- |
| Daily reporting | Batch | Cheaper, simpler, easier to reconcile |
| Intraday dashboard refresh | Frequent batch or micro-batch | Fresh enough without full streaming complexity |
| Fraud detection or alerting | Streaming | Decisions depend on low latency |
| Large historical reprocessing | Batch | Bounded data is easier to replay and audit |
| IoT telemetry or market ticks | Streaming | High-frequency events arrive continuously |

The practical question is not "batch or streaming?" but "what freshness does the consumer actually need?" Lower latency usually increases operational complexity. Many business cases described as real-time are adequately served by five-minute or hourly ingestion.

## Delivery Semantics

When data moves across systems, failures are normal. Delivery semantics describe what happens when a message, record, or file is sent but the sender does not know whether the receiver processed it successfully.

| Semantic | Meaning | Main risk | Typical use |
| --- | --- | --- | --- |
| At-most-once | Send once and do not retry | Data loss | Low-value telemetry where loss is acceptable |
| At-least-once | Retry until acknowledged | Duplicates | Most robust ingestion and streaming systems |
| Exactly-once processing | Process each logical record once despite retries | Complex assumptions | Systems with transactional sinks, offsets, and idempotent writes |

"Exactly once" needs careful interpretation. True exactly-once delivery across heterogeneous systems is rarely something to assume. In practice, reliable systems usually combine at-least-once delivery with idempotent writes, transactional commits, deterministic keys, and offset tracking. The goal is not magic; it is making retries safe.

[[REPORTKIT-VISUAL:fig:sec02-ingestion-semantics]]

## Idempotency

An ingestion process is idempotent if running it multiple times with the same input produces the same final result. Idempotency matters because pipelines fail, retries happen, and backfills are common.

For example, if a job loads the same file twice and doubles the number of rows, it is not idempotent. Better approaches include unique file identifiers, load manifests, primary keys, merge logic, deterministic output paths, and partition replacement.

Common patterns include:

- In batch ingestion, overwrite a complete partition only after the replacement data is ready.
- In database ingestion, upsert by a stable primary key or business key.
- In file ingestion, record processed file names, sizes, checksums, and arrival timestamps in a manifest.
- In event ingestion, store source event identifiers and deduplicate within an appropriate time window.
- In lakehouse ingestion, use table formats that support transactions and merge operations.

Idempotency should be designed deliberately. It is difficult to bolt on after a pipeline already produces duplicates.

## Backpressure and Flow Control

Backpressure is what prevents a fast producer from overwhelming a slower consumer. Suppose a market data feed emits 10,000 messages per second, but the destination database can write only 1,000 messages per second. Without flow control, the ingestion layer may buffer data in memory until it crashes.

A robust design can respond in several ways:

- slow down reads from the source, if the protocol supports it;
- buffer data durably in a message broker;
- scale consumers horizontally;
- write larger micro-batches instead of single records;
- shed non-critical data according to explicit rules;
- alert operators before lag becomes unrecoverable.

Message brokers such as Kafka, Redpanda, Kinesis, and Pulsar are often used as durable buffers. They decouple producers from consumers, retain events for replay, and allow downstream systems to consume at their own pace. They do not remove the need for capacity planning; they make overload visible and survivable.

## Change Data Capture and Query-Based Extraction

Many ingestion pipelines copy data from operational databases. There are two common approaches: query-based extraction and change data capture.

Query-based extraction runs SQL queries such as:

```sql
SELECT *
FROM users
WHERE updated_at > :last_successful_run;
```

This approach is simple and often good enough. Its weaknesses are important: it may miss hard deletes, it depends on reliable update timestamps, it can struggle with high-volume tables, and it adds read load to the source system.

Change data capture, or CDC, reads database change logs such as a write-ahead log, binary log, or transaction log. CDC can capture inserts, updates, and deletes with lower query load than repeated table scans. It is especially useful for near real-time replication from transactional systems into analytical platforms.

CDC is not free. It is source-specific, operationally sensitive, and still consumes source resources. It requires careful handling of schema changes, initial snapshots, transaction ordering, tombstone records, and downstream replay.

## Schema Drift

Schema drift occurs when a source changes its structure. Examples include added columns, renamed fields, changed types, nested JSON changes, or altered enum values. A robust ingestion system should detect these changes, classify their severity, and route them appropriately.

Some schema changes are safe, such as adding a nullable column. Others are dangerous, such as changing a customer identifier from integer to string or altering the meaning of a status value.

Useful responses to schema drift include:

- accepting additive nullable fields automatically;
- quarantining records that violate required schemas;
- alerting owners when breaking changes occur;
- versioning schemas for event streams;
- maintaining compatibility rules between producers and consumers;
- documenting semantic changes, not just structural changes.

Schema drift is both a technical and organizational problem. A pipeline can detect that a field changed type, but a data contract or ownership process is needed to explain whether the meaning changed.

## Late and Out-of-Order Data

Data does not always arrive when expected. Mobile devices may send events after reconnecting. Payment processors may revise settlements. Operational systems may backdate corrections. Streaming events may arrive out of order.

Data engineers handle late data with:

- event time rather than processing time;
- watermarking and allowed lateness windows;
- partition repair or merge strategies;
- periodic reconciliation jobs;
- clear freshness expectations for consumers.

Late data policy should be explicit. A dashboard may show preliminary numbers quickly and finalize them later. A financial reporting process may wait for reconciliation before publishing. A machine learning feature pipeline may need point-in-time correctness to avoid leakage.

## Tooling Landscape

Tool choice depends on source type, volume, latency, reliability requirements, team capability, and cost. AI can help write implementation code, but architecture choices still need human judgment.

| Tool category | What it does | When to use | Main catch |
| --- | --- | --- | --- |
| Custom code | Pulls or pushes data with APIs, database drivers, SDKs, or WebSockets | Custom APIs, internal systems, unusual logic | You own maintenance, retries, pagination, and drift handling |
| Managed connectors | Provide prebuilt pipelines between common sources and destinations | SaaS tools, common databases, standard replication | Cost, connector limits, vendor lock-in, infrastructure management |
| Message brokers | Buffer and distribute event streams | Streaming, backpressure, multiple consumers, replay | Operational complexity and capacity planning |
| CDC engines | Read database logs and emit changes | Near real-time database replication | Source-specific setup, schema evolution, delete handling |
| File transfer and object storage | Land files for downstream processing | Partner feeds, batch exports, lake ingestion | Late files, malformed files, duplicate arrivals |

Examples include Airbyte and Fivetran for connectors, Kafka and Redpanda for event streaming, Kinesis and Pub/Sub for cloud-native streams, Debezium for CDC, and Python or Go for custom ingestion services.

## Free Data Sources for Practice

Good portfolio projects need sources that reveal real ingestion problems, not just clean CSV loading.

| Ingestion style | Example sources | What they teach |
| --- | --- | --- |
| Streaming WebSockets | Binance, Coinbase, Kraken public market streams | high-frequency events, ordering, buffering, replay |
| Chat or social streams | Twitch IRC or PubSub-style feeds | bursty traffic, text payloads, rate limits |
| REST APIs | CoinGecko, Alpha Vantage, OpenWeatherMap, NASA APIs | pagination, rate limits, authentication, incremental pulls |
| Public files | NYC Open Data, GTFS transit feeds, government datasets | batch ingestion, partitioning, file validation |
| IoT and MQTT | ESP32 or Raspberry Pi sensors with Mosquitto | device telemetry, unreliable networks, small event payloads |

For a finance-leaning portfolio, market data ingestion is useful because it naturally introduces freshness, volume, replay, and deduplication questions. For a public-sector or operations portfolio, transit, weather, or city-service datasets can be equally strong.

## Capstone Project: Crypto Trade Ingestion

A practical ingestion project is to collect real-time Bitcoin trade data, buffer it, and land it in a local data lake. The running example in the later sections is a Binance Spot `BTCUSDT` trade stream. It is intentionally a trade-tick pipeline, not a full order-book reconstruction.

To keep the later stages reproducible, make the project contract explicit:

- Source: a public Binance Spot WebSocket stream for the `BTCUSDT` symbol. Source payloads and field names can change, so an implementation should verify the exchange documentation when it is built.
- Logical key: `(exchange_name, asset_symbol, source_trade_id)`. The exchange trade identifier is stable within a symbol; the composite key keeps the assumption safe if more exchanges or symbols are added later.
- Measures: `price` is quoted in USDT per BTC and `quantity` is measured in BTC. No currency conversion is introduced in this capstone.
- Time: `event_timestamp` is the exchange's trade time and `ingested_at` is the timezone-aware UTC time at which the producer receives the event and assigns its envelope. Store both timestamps, retain the original source timestamp where possible, and record file-write time in the manifest if it is needed for sink diagnostics.
- Partitioning: derive `event_date` and `event_hour` from `event_timestamp` in UTC. A late event can therefore be written to an older event-time partition even when it arrives today.
- Scope: the stream may run continuously, or a bounded UTC interval may be used for local testing. Examples use parameters or placeholders rather than a fixed calendar date.

The goal is to ingest those events with their raw payload and normalized envelope intact, publish them to a Kafka-compatible broker, and write replayable micro-batches to Parquet for later storage and transformation.

One possible architecture:

1. Source: connect to a public WebSocket stream such as `btcusdt@trade`.
2. Producer: write a Python ingestion service that preserves the raw JSON, normalizes the fields in the project contract, attaches `exchange_name`, `asset_symbol`, `source_trade_id`, `event_timestamp`, and `ingested_at`, and publishes the event to a `raw_crypto_trades` topic.
3. Buffer: run Redpanda or Kafka locally through Docker. Retain messages long enough to replay after failures.
4. Consumer: read from the topic in micro-batches and write append-only Parquet files under `s3://crypto-lake/raw/trades/event_date=YYYY-MM-DD/event_hour=HH/part-<batch_id>.parquet`, deriving the partition values from `event_timestamp` in UTC. For local testing, map this logical URI to MinIO or a filesystem-backed equivalent.
5. Manifest: track written batch identifiers, offsets, file paths, row counts, checksums, and a UTC `landed_at` timestamp for each durable file.
6. Quality checks: validate required fields, timestamp sanity, non-negative quantity, and duplicate trade identifiers.
7. Recovery: test what happens when the consumer crashes, the broker restarts, or the sink is temporarily unavailable.

The raw landing is append-only: a retry should not overwrite an earlier raw event file. The manifest makes file publication idempotent by associating a deterministic `batch_id` with the broker offset range and output path. A crash after the file write but before the offset commit may still cause redelivery, so the consumer must detect an already-recorded batch and the downstream table must deduplicate by the logical trade key. Commit broker offsets only after the file and its manifest entry are durable.

This project teaches the core ingestion questions:

- Can the producer reconnect without losing data silently?
- Are events deduplicated by exchange trade ID or another stable key?
- Are broker offsets committed only after sink writes succeed?
- Can an hour or partition be rebuilt from retained raw events?
- Is the raw data preserved before transformation?
- Are malformed records quarantined instead of discarded silently?

## Ingestion Output and Handoff

At the end of this stage, the project should have four explicit outputs:

- an append-only raw landing containing the original payload, normalized fields, both timestamps, and the source trade key;
- a manifest that relates broker offsets and batch identifiers to durable file paths, counts, checksums, and `landed_at` timestamps;
- a defined quarantine location and error record for malformed events;
- a replay procedure that can rebuild a bounded event-time interval from retained broker data or raw files.

Section 3 treats the raw landing and manifest as its inputs. It should not need to reconnect to the exchange to reconstruct an already landed event. Storage will organize these files into a queryable `curated_trades` table while preserving the same event-time, UTC, and trade-key conventions.

Be cautious with the phrase "order book" for this project. Trade ticks are simpler than full order book reconstruction. A true order book project requires ingesting snapshots and incremental depth updates, then applying sequence numbers correctly. That is a valuable advanced extension, but it should not be confused with basic trade ingestion.

## Ingestion Design Checklist

Before implementing an ingestion pipeline, define:

- source ownership and source-of-truth status;
- extraction method and expected volume;
- latency and freshness requirements;
- schema and schema evolution policy;
- delivery semantics and retry behavior;
- idempotency strategy;
- deduplication keys;
- handling for deletes and corrections;
- late-data policy;
- destination format and partitioning;
- event-time versus ingestion-time semantics;
- security and credential handling;
- monitoring, alerting, and runbook ownership;
- backfill and replay strategy;
- cost and rate-limit constraints.

An ingestion pipeline is production-ready when it can fail, retry, replay, and explain what happened. The raw movement of bytes is only the beginning.
