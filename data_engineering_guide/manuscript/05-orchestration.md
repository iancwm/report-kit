# Section 5 - Orchestration and Scheduling

Orchestration coordinates data workflows. It decides when work may start, which tasks must run first, what can run in parallel, and what should happen when a task is late or fails. An orchestrator records the state of each run so that a person or another system can understand what happened and take the next action.

Orchestration is related to, but different from, the other stages of the lifecycle. The responsibilities table separates coordination from ingestion, transformation, storage, and observability.

Table: Lifecycle concerns and orchestration responsibilities. \label{tbl:orchestration-concerns}

| Concern | Main question | Typical responsibility |
| --- | --- | --- |
| Ingestion | How do we move data from a source? | Connect to an API, stream, database, or file location |
| Transformation | How do we change data into a useful shape? | Parse, join, aggregate, and model records |
| Storage | Where and in what format do we keep data? | Persist files, tables, snapshots, and indexes |
| Orchestration | When and under what conditions does work run? | Order tasks, pass parameters, retry, pause, and backfill |
| Monitoring and observability | Is the system behaving as expected? | Collect signals, detect anomalies, and notify owners |

One platform can provide several of these capabilities. For example, a managed service may schedule a dbt job, display its logs, and run SQL transformations. The concepts are still distinct: the scheduler coordinates the work, dbt defines transformations, and monitoring evaluates the health of the run and its outputs.

## Why Orchestration Matters

A data platform may have hundreds or thousands of jobs. Some depend on source files, some depend on other tables, and some must run after a business cutoff. Other jobs can run independently and should run in parallel. Without explicit coordination, pipelines become fragile scripts, hidden dependencies, and manual procedures.

An orchestrator commonly provides:

- dependency management;
- time-based and event-based triggers;
- parameterized runs;
- retries and timeouts;
- concurrency and resource controls;
- backfills and reprocessing;
- run history, logs, and audit metadata;
- notifications and links to operational runbooks.

An orchestrator does not make a poorly designed task correct. It can retry a task, but it cannot decide whether a duplicate write is acceptable, whether a metric definition is right, or whether a source is authoritative. Those are data and application design decisions.

## Directed Acyclic Graphs

Many orchestrators represent a workflow as a directed acyclic graph, or DAG. A DAG contains tasks and directed dependency edges. If task B depends on task A, B is eligible to run only after A reaches the required state. "Acyclic" means that following dependency edges can never lead back to the starting task; the workflow therefore has an order in which it can make progress.

For example, a daily revenue workflow might contain these tasks:

1. ingest orders for a business date;
2. ingest payments for the same date;
3. validate both inputs;
4. build the revenue model;
5. run publication checks;
6. refresh a dashboard extract.

The ingestion tasks can run in parallel. The revenue model has a fan-in dependency on both validations. The dashboard extract should wait for the model and its publication checks. The graph makes those rules visible instead of relying on task start times or assumptions hidden in scripts.

Useful DAG vocabulary:

- **Task:** A bounded unit of work, such as loading one partition or running one model.
- **Dependency:** A condition that must be met before a task is eligible to run.
- **Fan-out:** One upstream task enables several independent downstream tasks.
- **Fan-in:** Several upstream tasks must complete before one downstream task runs.
- **Run:** One execution of a workflow, usually for a particular interval or parameter set.
- **Logical date or data interval:** The period of data a run represents; it may differ from the wall-clock time when the run starts.

Good DAGs make data dependencies explicit, keep tasks small enough to retry, and avoid hidden communication through local files or mutable global state. They should not contain cycles such as `clean_orders -> publish_metrics -> clean_orders`. A cycle usually indicates that responsibilities or intermediate outputs need to be separated.

The graph is a control structure, not a substitute for data modeling. A dependency saying "the orders task succeeded" does not prove that orders are complete, unique, or fit for a revenue calculation. Quality checks or asset conditions must express those additional requirements.

The orchestration figure gives a compact dependency example; its edges describe control order, while the later quality checks determine whether the resulting data is fit to publish.

[[REPORTKIT-VISUAL:fig:sec05-orchestration-dag]]

## Schedules and Event Triggers

A schedule starts runs according to time. A trigger starts a run because something happened. The distinction matters because a clock tells you that an attempt should begin, while a data event can tell you that an input is available. The trigger table compares the common start conditions and the risk each one requires the operator to manage.

Table: Workflow start conditions and operational risks. \label{tbl:workflow-start-conditions}

| Start condition | Example | Strength | Risk to manage |
| --- | --- | --- | --- |
| Fixed schedule | Run at 02:00 UTC every day | Predictable and simple | The source may not be ready yet |
| Fixed interval | Run every 15 minutes | Regular freshness | Runs can overlap if work takes too long |
| External event | Start when a partner file arrives | Responds to actual availability | Events can be duplicated or malformed |
| Sensor or poll | Check for a partition or API condition | Works with systems that emit no event | Polling can waste resources or wait forever |
| Data-aware or asset trigger | Start when an upstream table is updated and validated | Expresses data dependencies | Requires trustworthy asset metadata and update events |
| Manual or API trigger | An operator or deployment starts a run | Useful for repair and controlled releases | Easy to bypass normal parameters or checks |

Schedules need an explicit timezone and a definition of the interval they cover. A job scheduled at 02:00 may represent the previous calendar day, and daylight-saving changes can make local-clock schedules ambiguous. Use UTC where practical, pass the data interval as a parameter, and document the boundary rules. A scheduled start time is not the same as a freshness guarantee; the source, task runtime, and downstream checks determine when data is actually usable.

Event triggers must be safe to receive more than once. A file-arrival event may be delivered twice, or an event may arrive before a file has finished uploading. Use a stable event or asset identifier, verify completion and integrity, and make the resulting run idempotent. A "file exists" check is not sufficient if a producer writes directly to the final path while consumers can see a partial file. A temporary path followed by an atomic publish, or a completion manifest, is safer.

## Sensors and Data Assets

A sensor waits for a condition, such as a file, partition, upstream job, API response, or business cutoff. Sensors are useful at system boundaries, but a poorly configured sensor can occupy a worker indefinitely. Set a polling interval, timeout, and failure behavior. Where the orchestrator supports it, use a rescheduling or deferrable mode so the waiting sensor releases worker capacity between checks.

An asset is a named data product such as a table, partition, file set, or feature dataset. Asset-aware orchestration treats an update to an upstream asset as a dependency for downstream work. The dependency is stronger than "the upstream process exited with code zero": it can include the asset identifier, data interval, version, and quality status.

For example, a downstream hourly aggregate may be eligible only when:

- the raw trade partition for that hour exists;
- the producer has marked the partition complete;
- the schema is compatible;
- required quality checks pass;
- the upstream asset version is recorded.

Assets help teams reason about data products and lineage. They do not remove the need for task-level retries or validation. An asset should be marked updated only after its write is committed and any required checks have completed.

## Task Design and Idempotency

An orchestrator can rerun a task after a worker crash, a timeout, an operator action, or a backfill. Tasks should therefore be designed as repeatable operations whose outputs are identified by their input interval and parameters.

For each task, define:

- its input assets and parameters;
- its output assets and expected grain;
- the side effects it performs;
- a stable idempotency key, such as `(task_name, data_interval, source_version)`;
- the conditions for success;
- what can be safely retried;
- how partial output is removed, replaced, or quarantined.

Common idempotent patterns include:

- overwrite a complete partition after writing a temporary replacement;
- merge by a stable record or event identifier;
- use a load manifest to record source files, offsets, and output checksums;
- write to a run-specific staging location and publish atomically;
- make external side effects conditional on a recorded operation key.

Appending to a destination on every retry is unsafe unless the destination deduplicates by a stable key. A task should not depend on the local disk of the worker because a retry may run on a different machine. Keep durable state in the data platform or an explicit metadata store.

Task granularity is a trade-off. One enormous task is difficult to retry and hides progress. Thousands of tiny tasks increase scheduler overhead and can overwhelm the control plane. A useful boundary is a meaningful, independently testable unit such as one table partition, one bounded API page group, or one model layer.

## Retries and Timeouts

Retries are appropriate for transient failures: a temporary network error, rate limit, unavailable database, or worker interruption. They are usually not appropriate for deterministic failures such as an invalid SQL statement, a breaking schema change, a missing required credential, or a violated business rule. Retrying those failures delays diagnosis and may increase damage.

A retry policy should specify:

- maximum attempts;
- delay between attempts;
- exponential backoff and jitter for shared services;
- which exception or state types are retryable;
- whether the task is safe to rerun;
- what happens after the retry budget is exhausted.

Use timeouts to bound waiting. A task timeout protects worker capacity when a query or API call hangs. A sensor timeout protects the workflow from waiting forever for a source that may never arrive. Timeouts should be long enough for normal variation but short enough to produce a useful operational signal. A retry must not extend an unbounded task indefinitely without a clear overall run deadline.

Downstream behavior after failure must be explicit. A downstream task may be blocked when an upstream task fails, skipped when an optional branch is empty, or allowed to run against a known prior version. The last option is a business decision and should be visible to consumers; silently serving stale data is not a neutral default.

## Failure Handling

Failure handling is a control loop rather than a single "retry on error" setting:

1. Detect the failure and preserve the relevant error, parameters, input versions, and logs.
2. Classify it as transient, data-related, code-related, or external and determine whether retrying is safe.
3. Retry within a bounded budget when the failure is likely to recover.
4. Stop or quarantine affected downstream outputs when correctness is uncertain.
5. Alert the owning team with the affected interval, asset, and suggested runbook.
6. After the cause is corrected, rerun the smallest safe scope and validate the result.
7. Record the incident and prevention work if consumers received incorrect or late data.

Partial outputs should not appear as complete assets. Write to a temporary or run-specific location, then publish or commit only after the task finishes. If a task must produce partial progress, expose that state explicitly and ensure downstream tasks know whether partial data is acceptable.

Orchestration can route an alert, pause a dependent branch, or launch a repair workflow. Monitoring and observability provide the evidence used for those decisions: logs, metrics, freshness, volume, schema, and lineage signals. An orchestrator is not a replacement for monitoring, and an alert is not a repair strategy by itself.

## Backfills and Reprocessing

A backfill runs a workflow for past data intervals that were missing, late, or invalid. Reprocessing is the broader act of computing data again, often because transformation logic changed or a source correction arrived. Both should use the same version-controlled code path as normal runs, with an explicit interval or partition parameter.

Backfills are necessary when:

- source data was missing or wrong;
- a pipeline failed for multiple periods;
- transformation logic changed;
- historical data was added;
- a new derived asset needs history;
- a late correction must flow through downstream models.

Before launching a backfill, confirm:

- the source data and schema are available for every requested interval;
- the output operation is idempotent or writes a new version;
- downstream consumers will not read half-repaired history;
- the intended code and reference data versions are recorded;
- the backfill will not overload source systems or shared compute;
- the validation and publication steps are included.

Run a small interval first. Then choose bounded parallelism rather than launching thousands of historical runs at once. Separate backfill outputs from current production outputs when the result needs review. If the logic changed, preserve the model or code version used so that historical numbers remain explainable.

Backfills should not be treated as a special manual script that has different correctness rules. A reliable daily run and a reliable historical run are the same operation applied to different data intervals.

## Concurrency and Resource Controls

Concurrency determines how much work may run at the same time. More parallelism can reduce latency, but it can also exhaust worker capacity, exceed API or database limits, create lock contention, and make failures harder to recover from.

Useful controls include:

- maximum active workflow runs;
- maximum concurrent instances of a task;
- pools or queues for shared resources, such as a source database;
- worker slots or execution limits by task size;
- priority rules for business-critical workflows;
- separate capacity for interactive work and backfills;
- API rate limits and database connection limits;
- overall workflow deadlines.

Set controls around the bottleneck, not just around the scheduler. For example, a warehouse may support many tasks while a partner API permits only ten requests per second. A pool for that API protects the source even when workers are available.

Avoid a thundering herd after an outage. When a scheduler recovers, delayed runs, retries, and sensors can all become eligible at once. Use backoff, limits, priorities, and staggered recovery. A backfill should not compete with the current business-critical run unless that trade-off is deliberate.

## Data-Aware Scheduling

Time schedules are useful when work is naturally periodic. Data-aware scheduling is useful when the arrival or successful update of an input is the real condition for downstream work.

Data-aware scheduling can express rules such as:

- run a model when both the orders and payments partitions for a date are ready;
- refresh a dashboard after the curated table and its quality checks succeed;
- recompute a feature when its source asset version changes;
- wait for a complete daily source snapshot rather than starting at a fixed time.

This approach can reduce unnecessary polling and make dependencies match the data lifecycle. It also introduces a responsibility: upstream producers must publish accurate asset events and consumers must understand whether an update is provisional or final. A successful task status alone is not enough if the task wrote the wrong interval or skipped a partition.

## Orchestration Tooling Landscape

Choose an orchestrator according to workflow shape, deployment model, team skills, and operational constraints. The names below describe common fits rather than hard boundaries. The orchestration-tooling table is a starting map, not a ranking.

Table: Orchestration tools and common fits. \label{tbl:orchestration-tooling}

| Tool or category | Typical fit | Important consideration |
| --- | --- | --- |
| Apache Airflow | Batch DAGs, broad integrations, explicit task dependencies | Strong ecosystem; requires care with scheduler, worker, and metadata database operations |
| Dagster | Asset-oriented pipelines, lineage, typed definitions, local development | Works well when data assets are first-class design objects |
| Prefect | Python-native workflows and dynamic control flow | Flexible execution model; deployment and state behavior still need to be designed |
| Cloud schedulers | Managed jobs across a cloud provider's services | Lower infrastructure burden; provider coupling and service-specific limits |
| Argo Workflows or Kubernetes operators | Containerized jobs and platform-native batch work | Useful for Kubernetes teams; cluster operations become part of the system |
| dbt Cloud or a scheduler running dbt | Coordinating SQL model runs and tests | dbt performs transformations; it is not a general ingestion or storage system |

The orchestrator should be the thinnest reliable control layer that meets the need. A small project may use a cloud scheduler or a single cron job with a robust script. A large platform may need a distributed scheduler, worker pools, asset metadata, and role-based operations. Using a more elaborate tool does not remove the need for clear task contracts and safe retries.

## Implementation Pattern: A Daily Workflow

The following is deliberately tool-neutral pseudocode. It illustrates the information a workflow definition should make explicit; it is not intended to run without adapting it to a chosen orchestrator.

```text
workflow: daily_revenue
schedule: 02:00 UTC
run_parameter: business_date
max_active_runs: 1

tasks:
  ingest_orders:
    inputs: orders source, business_date
    output: raw_orders[business_date]
    retries: 3
    timeout: 20 minutes
    idempotency_key: ingest_orders/business_date

  ingest_payments:
    inputs: payments source, business_date
    output: raw_payments[business_date]
    retries: 3
    timeout: 20 minutes
    idempotency_key: ingest_payments/business_date

  validate_inputs:
    depends_on: [ingest_orders, ingest_payments]
    output: inputs_validated[business_date]

  build_revenue:
    depends_on: [validate_inputs]
    output: revenue[business_date]
    operation: replace partition after successful write

  publish_dashboard:
    depends_on: [build_revenue]
    condition: publication checks pass
```

The same workflow can run for one historical `business_date` during a backfill. The tasks do not infer the date from the machine clock, and the final output is replaced or merged by a stable key rather than appended blindly. If `ingest_orders` fails, the payment task can still complete, but validation and publication remain blocked until both inputs are ready.

## Capstone Continuation: Orchestrating the Crypto Lakehouse

The crypto project contains a useful boundary between streaming services and orchestration. The WebSocket producer and broker consumer are long-running services; an orchestrator should supervise their deployment and health, not create one scheduler task for every trade event.

A practical hourly workflow is:

1. wait for the raw trade partition to be marked complete;
2. validate schema, timestamps, and duplicate trade identifiers;
3. compact or commit the hourly Parquet or table partition;
4. build the hourly aggregate for each asset and exchange;
5. run quality checks and publish the aggregate asset.

The workflow is data-aware: the hourly aggregate waits for a complete raw partition and successful checks. If an hour is corrected, rerun that hour with the same partition key. Limit concurrent historical hours so a repair does not overwhelm the local broker, object store, or query engine.

## Orchestration Design Checklist

Before implementing a workflow, define:

- the workflow's purpose and owning team;
- the data interval and timezone represented by each run;
- the tasks, outputs, and explicit dependencies;
- which dependencies are task, time, event, sensor, or asset conditions;
- idempotency keys and the handling of partial output;
- retryable versus deterministic failures;
- task and sensor timeouts;
- downstream behavior when an upstream task fails or is late;
- concurrency, priority, pool, and source rate-limit controls;
- backfill and reprocessing parameters;
- validation and publication gates;
- logs, run metadata, alert routing, and a repair runbook.

A workflow is production-ready when it can explain what it is processing, wait for the right inputs, fail without corrupting outputs, retry within a bounded policy, recover historical intervals, and avoid overwhelming its dependencies. The orchestration layer should make those guarantees visible rather than leaving them implicit in task code.
