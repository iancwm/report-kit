# Section 8 - Topics in Data Engineering

The earlier sections describe the core lifecycle: ingest data, store it durably, transform it, orchestrate the work, test its quality, and make the result discoverable and useful. This section collects practitioner concerns that cross those stages or become important as a system grows. They are not a second mandatory lifecycle. Read the parts that match the risk, scale, and operating context of the system you are building.

The central question is not "Which fashionable tool should we use?" It is "Which capability does this system need, and what is the simplest dependable way to provide it?" A small daily report and a global event platform may use different products while relying on the same engineering principles.

## Security, Privacy, and Compliance

Data platforms often combine operational, behavioral, financial, and personal information. Security is therefore a system property, not a final checklist. Controls should be designed at the point where data is collected, copied, transformed, stored, and served.

At a minimum, reason about:

- **Identity and authorization:** authenticate people and services, assign the least privilege needed, and separate read, write, administer, and deploy permissions.
- **Isolation:** separate development, test, and production environments; restrict network paths; and keep untrusted workloads away from sensitive stores.
- **Protection:** encrypt data in transit and at rest, manage keys and secrets outside source code, and avoid placing sensitive values in logs or error messages.
- **Lifecycle controls:** classify data, minimize collection, define retention periods, support approved deletion or correction requests, and document where copies exist.
- **Accountability:** record access and administrative changes, preserve enough audit context to investigate incidents, and review permissions as roles change.

The security-layers figure groups these controls by responsibility and emphasizes that a single product may implement more than one layer.

[[REPORTKIT-VISUAL:fig:sec08-security-layers]]

Access control can be implemented with roles, attributes, row-level policies, column masking, tokenization, or a combination. The mechanism matters less than making the policy explicit. For example, "analysts can read aggregated regional revenue but not customer email addresses" is a testable rule; "the warehouse is secure" is not.

Sensitive data includes personally identifiable information, health records, payment data, credentials, confidential business data, and regulated records. Classify sensitive fields near the source, propagate that classification through metadata and contracts, and create realistic but non-sensitive development datasets. A raw landing zone is not exempt from these controls merely because it is not user-facing.

Compliance obligations vary by industry, region, and contract. Examples include GDPR, HIPAA, PCI DSS, SOC 2, and internal controls. Data engineers normally share responsibility with security, legal, privacy, and platform teams. Their systems should make retention, deletion, access review, lineage, reproducibility, and evidence collection possible rather than relying on manual memory.

## Observability and Operations

Data systems are production systems. A successful process can still publish an empty table, stale data, duplicate facts, or a plausible result with a broken definition. Observability makes these failures visible and helps a team decide what to do next.

Separate three related practices:

- **Testing:** checks an expected condition, such as a non-null key, before or during a run.
- **Monitoring:** records a signal over time and compares it with a threshold or target, such as freshness or job duration.
- **Observability:** provides enough context to explain an unexpected state, including the run, inputs, code version, data version, and affected consumers.

A useful minimum signal set covers:

- job state, duration, retry count, and queue delay;
- source and destination volume, freshness, and completeness;
- schema changes and contract violations;
- key quality measures such as null rates, uniqueness, valid ranges, and distribution changes;
- resource use, query performance, and cost;
- lineage or dependency information for assets that were not refreshed.

Logs describe events and decisions. Metrics provide numeric time series that can be alerted on. Traces connect a request or pipeline run across services. A batch pipeline may need only structured logs, run metrics, and dataset-level signals; a highly distributed streaming system may also need end-to-end traces. Instrumentation should match the failure modes rather than be added indiscriminately.

Alerts should be actionable. An alert should identify the affected asset, the failed check, the relevant run or partition, the likely owner, and the next diagnostic step. Alerting on every small fluctuation creates fatigue and teaches people to ignore the system. Pair important alerts with a short runbook that explains whether to retry, pause downstream publication, quarantine data, roll back, or escalate to the source owner.

When an incident occurs, preserve the evidence needed to reconstruct it: code and configuration versions, input offsets or partitions, schema versions, test results, and deployment history. After recovery, distinguish the immediate failure from the control that would have detected or prevented it. This turns operations into feedback for design rather than a sequence of one-off repairs.

## Cost Management

Cost is part of correctness for a production data system. A pipeline that meets its latency target by consuming an unreasonable amount of compute, storage, or network capacity is not complete. Cost should be considered alongside reliability and performance, not optimized in isolation.

The largest levers are usually:

- storing data in an efficient columnar format and retaining only the history and copies that have a purpose;
- partitioning or clustering for the access patterns that actually occur, without creating thousands of tiny partitions;
- processing only new or changed data when a full refresh is unnecessary;
- right-sizing compute and turning off idle resources;
- avoiding repeated scans through incremental models, sensible caching, and query review;
- controlling cross-region or cross-cloud transfer and unplanned egress;
- assigning spend to teams, products, or workloads so that the owner of a decision can see its effect.

Track unit measures such as cost per successful pipeline run, cost per gigabyte processed, or cost per dashboard refresh. Set budgets and review unusually expensive queries, retries, and storage growth. A cheaper design is not automatically better if it loses data or requires excessive on-call work; compare total cost of ownership, including people and failure recovery.

## Architecture Patterns

Architecture patterns are useful vocabulary for discussing trade-offs, not templates to copy. They operate at different levels and can be combined: Lambda and Kappa describe processing paths, medallion describes data organization, and data mesh describes an organizational model. The pattern-comparison table keeps the choice tied to a workload and its main risk.

Table: Data architecture patterns and trade-offs. \label{tbl:architecture-patterns}

| Pattern | Useful when | Main cost or risk |
| --- | --- | --- |
| Lambda | A system needs a low-latency view and an independent batch recomputation path | Batch and streaming logic can diverge, creating duplicate code and reconciliation work |
| Kappa | Durable, replayable events are the primary source of truth and consumers can rebuild state | Replay depends on event quality, retention, and an affordable way to reprocess history |
| Medallion | A lakehouse needs recognizable raw, refined, and curated boundaries | Layer names do not define semantics; uncontrolled copies can create confusion and storage cost |
| Data mesh | Multiple domains need ownership of data products while a platform supplies shared capabilities | It requires strong contracts, discoverability, and federated standards; decentralization alone does not create quality |

Choose a pattern only after stating the workload, failure model, ownership model, and expected change. A straightforward batch pipeline is often a better starting point than a dual-path architecture. A streaming architecture is justified by a real latency or event-replay requirement, not by the presence of a message broker in a diagram.

## Practitioner Discussion: Data Contracts

Section 7 introduced data contracts as a core governance concept. This practitioner discussion focuses on applying them across independently changing teams and systems. An explicit contract should cover more than column names: it states the grain of a record, field meanings and units, keys, allowed values, freshness, quality expectations, ownership, privacy classification, compatibility rules, and the process for changing the interface.

Contracts are most valuable where teams or systems change independently. They can be lightweight for a small project: a versioned schema, an owner, and a documented change rule may be enough. They become more formal when many consumers depend on the same dataset. A contract does not guarantee good data; it makes expectations visible, testable, and attributable.

Prefer backward-compatible changes when possible. Add a nullable field before making it required, version a breaking semantic change, and give consumers a migration window. Validate the contract close to the producer and again at ingestion or transformation boundaries, because a valid schema can still contain invalid business facts.

## Tools and Technology Landscape

Tool names change faster than capabilities. The following maps are deliberately small; each row describes a responsibility boundary and gives representative choices rather than an exhaustive catalogue. A single product may cover several rows, but its responsibilities should still be named separately. The first table covers the core pipeline capabilities.

Table: Core data-platform capabilities and representative tools. \label{tbl:core-tool-landscape}

| Capability | Responsibility | Representative starting choices | Boundary to remember |
| --- | --- | --- | --- |
| Source systems | Generate and own operational records or external data | PostgreSQL or MySQL, SaaS APIs, files, application events | The source system defines what happened; the pipeline should not silently invent source semantics |
| Ingestion and transport | Extract, transfer, buffer, and acknowledge data | A Python connector or managed connector for batch; a Kafka-compatible broker or cloud pub/sub service for events | A broker transports and retains events; it is not a warehouse or an orchestrator |
| Durable storage and tables | Retain data and provide transactional or analytical table semantics | Object storage with Parquet; Iceberg, Delta Lake, or Hudi; a managed warehouse | File format, table format, warehouse, and query engine are related but different layers |
| Query and processing | Filter, join, aggregate, and reshape data | SQL in a warehouse or DuckDB; dbt for SQL models; Spark or Flink when distributed or streaming execution is required | Processing computes results; it does not decide when the work runs |
| Orchestration | Represent dependencies, schedule work, retry, backfill, and record runs | Airflow, Dagster, Prefect, or a managed workflow service | An orchestrator coordinates tasks; it should not become the place where all business logic is hidden |
| Quality and observability | Test data, record signals, detect drift, and support diagnosis | Native assertions and metrics first; dbt tests, Great Expectations, or Soda as needs grow | Tests state expected conditions; observability explains behavior over time |
| Catalog and governance | Describe, discover, classify, trace, and control data | A platform catalog, DataHub, or a commercial catalog | A catalog documents and helps enforce policy; it is not a replacement for ownership |

The cross-cutting and consumption table completes the landscape without leaving a single serving row stranded on a continuation page.

Table: Cross-cutting governance and consumption capabilities. \label{tbl:cross-cutting-tool-landscape}

| Capability | Responsibility | Representative starting choices | Boundary to remember |
| --- | --- | --- | --- |
| Serving and consumption | Deliver trusted data to people or applications | BI tools such as Looker, Tableau, or Power BI; APIs or feature stores for programmatic consumers | A dashboard is a consumer and does not remove the need for data contracts and freshness guarantees |

The examples are illustrative, not endorsements. A warehouse may provide storage, query execution, access control, and monitoring in one service. An open table format may provide table semantics on object storage but still need a query engine and catalog. Name the capability first so that a product change does not change the architecture by accident.

## Selecting Tools and Managing Trade-offs

Evaluate tools against the workload and the team that will operate them. A compact decision record should answer:

1. **What data arrives, from where, and at what rate?** Consider protocols, source limits, volume, schema variability, and whether deletes or corrections must be captured.
2. **What latency and recovery behavior is required?** Specify acceptable freshness, replay or backfill needs, recovery time, and delivery or processing semantics.
3. **Where should data live and who will query it?** Decide whether the workload needs an operational database, analytical warehouse, object storage, table format, or more than one.
4. **What constraints are non-negotiable?** Include privacy, residency, security, compatibility, portability, budget, and existing platform standards.
5. **Who will own the service at 02:00?** Count upgrades, patching, scaling, incident response, support, and the skills already present on the team.
6. **How will the choice be tested?** Run a small representative workload and measure correctness, recovery, latency, cost, and operational effort before committing.

Managed services usually reduce infrastructure work, provide integrated scaling and support, and let a small team reach a service level sooner. They can also introduce usage-based cost, data-transfer charges, provider-specific interfaces, migration effort, and less control over failure behavior. Open-source software can offer portability, customization, and inspectable behavior, but the team owns deployment, upgrades, security, capacity planning, and on-call response. "Open source" is not the same as "free."

Use a managed option by default when the team is small, the operational requirement is urgent, or the capability is not a source of competitive advantage. Consider self-managed or open-source components when portability, deep customization, local deployment, or existing operational expertise justifies the additional work. A hybrid is often reasonable: managed storage or warehouse services with open formats and version-controlled transformation code. Record the trade-off and the exit cost rather than treating one operating model as universally superior.

## Minimum Viable Stack and Learning Order

Most learners can build a complete, credible batch pipeline without adopting a distributed cluster or a long list of services. A practical minimum stack is:

- SQL and Python for querying, modeling, and small integrations;
- version control and a reproducible environment;
- Parquet files on local or object storage for durable analytical data;
- DuckDB or a small analytical warehouse for queries;
- SQL models or dbt for transformations;
- one orchestrator once the manual workflow is understood;
- assertions, structured logs, run metadata, and a basic freshness check.

Learn and add capability in this order. The learning-order table makes the recommended progression explicit and names what to defer until the current limitation is measured.

Table: Learning stages and capabilities to defer. \label{tbl:learning-order}

| Stage | Learn or use | Defer until there is evidence of need |
| --- | --- | --- |
| 1. Foundations | SQL, Python, Git, relational modeling, JSON/CSV/Parquet | Cloud-specific abstractions and distributed execution |
| 2. Durable batch | A source database or API, Parquet, DuckDB or one warehouse | Multiple storage systems and several table formats |
| 3. Reusable models | Incremental SQL, tests, documentation, and optionally dbt | A separate transformation framework for every language |
| 4. Reliable operation | One orchestrator, retries, backfills, logs, metrics, and alerts | Complex event-driven scheduling before dependencies are understood |
| 5. Scale and latency | Partitioning, query plans, object-store layout, and workload measurement | Spark, Flink, or a broker until single-node limits or latency targets require them |
| 6. Platform concerns | Cloud IAM, secrets, cataloging, lineage, retention, and cost controls | Enterprise governance products before the ownership and policy needs are clear |
| 7. Streaming | Events, offsets, replay, watermarking, and a Kafka-compatible broker or cloud service | A second streaming engine unless the workload needs its distinct processing model |

When choosing the next tool, write down the limitation it resolves. "The current job cannot meet a measured latency target" is a reason to consider streaming; "this tool is popular" is not. Learning one complete stack end to end builds more judgment than sampling several products without operating any of them.

## Data Engineering in Practice

The following example shows how practitioner concerns fit around the core lifecycle. It is intentionally ordinary: the same reasoning can be applied to a portfolio project or a production system.

Suppose a company wants a trusted daily revenue dashboard from an orders database, a payment processor API, a product catalog, and refund events. A proportionate design might:

1. capture order changes or scheduled extracts with a documented watermark;
2. ingest payment settlements and refunds, retaining source timestamps and identifiers;
3. store immutable raw inputs with load metadata and an explicit retention policy;
4. standardize currencies, timestamps, identifiers, and product references;
5. deduplicate events and define the grain of each modeled table;
6. reconcile orders, settlements, and refunds before publishing revenue;
7. build a curated revenue mart by day, region, category, and channel;
8. expose the mart to a BI tool with documented freshness and ownership;
9. monitor volume, freshness, quality checks, cost, and downstream refreshes;
10. restrict sensitive customer fields and record access to the relevant assets.

The visible output is a dashboard. The engineering work is the set of contracts, controls, recovery paths, and decisions that make the dashboard trustworthy.

## Design Questions Before Building

Before selecting products or writing pipeline code, answer:

- Who will use the data, and what decision or process will it support?
- What does one row represent, and what are the keys and valid time fields?
- What is the source of truth for each important fact?
- What freshness, completeness, and recovery targets matter?
- How are inserts, updates, deletes, late events, and corrections represented?
- What history must be preserved, and what may be deleted or aggregated?
- Which quality checks block publication, and which produce warnings?
- What data is sensitive, and who may access each layer?
- Who owns the source, pipeline, dataset, and consumer-facing definition?
- How will a failed run be retried, replayed, backfilled, or rolled back?
- How will cost and usage be measured as volume grows?

These questions prevent overbuilding and expose missing requirements early. They also make a tool decision explainable: the architecture follows the workload and its obligations rather than the other way around.

## Production Readiness Checklist

A business-critical pipeline should have, at an appropriate level of rigor:

- version-controlled code, configuration, and schemas;
- documented inputs, outputs, grain, owners, and service expectations;
- reproducible environments and a deployment path;
- explicit delivery, retry, deduplication, and idempotency behavior;
- schema compatibility checks and data-quality tests;
- structured logs, run metadata, freshness signals, and actionable alerts;
- access controls, secret handling, classification, retention, and audit evidence;
- a backfill and recovery procedure that has been exercised;
- lineage or dependency visibility for downstream consumers;
- cost monitoring and a review process for unexpected growth;
- a short runbook explaining common failures and escalation paths.

Not every pipeline needs every platform feature. The standard should be proportional to the harm caused by stale, incorrect, unavailable, exposed, or unexpectedly expensive data. A clear risk decision is stronger than an accidental omission.
