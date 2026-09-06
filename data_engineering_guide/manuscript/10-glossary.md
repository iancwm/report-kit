# Section 10 - Glossary

**API**: An interface that lets software systems exchange data or functionality.

**Asset**: A named data product, such as a table, partition, file set, or feature dataset, whose updates can trigger dependent work.

**Backfill**: Rerunning a pipeline for historical periods.

**Backpressure**: A flow-control response that slows or buffers producers when downstream systems cannot keep up.

**Batch processing**: Processing data in bounded chunks on a schedule or trigger.

**Change data capture**: Capturing database inserts, updates, and deletes, often from transaction logs.

**Checkpoint**: Durable progress information that lets a streaming job resume from a known position after a failure.

**DAG**: Directed acyclic graph; a workflow structure with tasks and dependencies.

**Data catalog**: A system for discovering, documenting, and governing data assets.

**Data contract**: An agreement defining expected schema, meaning, quality, and freshness between producers and consumers.

**Data lake**: A storage system for large-scale raw and processed data, often on object storage.

**Data lakehouse**: An architecture combining data lake flexibility with warehouse-like management features.

**Data lineage**: A record of where data came from and how it was transformed.

**Data mart**: A curated dataset or schema designed for a specific business area or use case.

**Data observability**: The practice of collecting enough signals and context to explain unexpected data or pipeline states.

**Data pipeline**: A repeatable process that moves and transforms data.

**Data quality**: The fitness of data for a particular use.

**Data warehouse**: A system optimized for analytical queries and reporting.

**Delivery semantics**: The guarantee a system makes about message loss and duplication, such as at-most-once or at-least-once delivery.

**ELT**: Extract, load, transform; loading raw data first and transforming it in the target platform.

**ETL**: Extract, transform, load; transforming data before loading it into the target platform.

**Event time**: The time an event happened according to its source, which may differ from when the platform received it.

**Feature store**: A system for managing reusable machine learning features for training and serving.

**Freshness**: How up to date a dataset is relative to expectations.

**Grain**: The meaning of one row in a dataset.

**Idempotency**: The property that rerunning a process with the same input produces the same result.

**Ingestion time**: The time a data platform received or durably recorded an event.

**Orchestration**: Coordinating scheduled and dependent workflow tasks.

**Partitioning**: Organizing data into subsets, often by date or another key, so that reads and maintenance can be scoped.

**Quarantine**: An isolated location for malformed or suspect records kept for investigation or later correction.

**Schema drift**: Changes in source data structure over time.

**SLO (service-level objective)**: A target for a service or data product, such as a freshness or availability objective.

**Source of truth**: The authoritative system or dataset used to resolve conflicting values.

**Streaming**: Processing data continuously as it arrives.

**Table format**: A metadata and transaction layer that manages files as a table, such as Delta Lake, Iceberg, or Hudi.

**Watermark**: A progress boundary used to decide how much event-time data is expected to have arrived and when a window can be finalized.
