# Section 7 - Metadata, Governance, and Serving Data

Metadata is data about data. It describes schemas, owners, definitions, freshness, quality, sensitivity, lineage, and usage. Governance is the set of policies, roles, processes, and tools used to manage data responsibly.

Governance is broader than data quality. Data quality asks whether data is fit for use. Governance asks who owns it, who can access it, what it means, how long it should be retained, how changes are approved, and whether its use is compliant with policy and law.

Good governance is practical. It should make the right thing easy. If governance is only a committee, a spreadsheet, or a gatekeeping process, teams will route around it. If governance is embedded into catalogs, contracts, access controls, tests, lineage, and documentation, it becomes part of normal engineering work.

## Data Catalogs

A data catalog helps users discover and understand data assets. A useful catalog answers:

- What datasets exist?
- Who owns them?
- What do fields mean?
- How fresh is the data?
- Can I trust it?
- Who uses it?
- Is it approved for my use case?

Catalogs fail when they become stale documentation. They work best when integrated with pipelines, access controls, tests, and lineage systems.

A useful catalog contains both technical metadata and business metadata.

| Metadata type | Examples |
| --- | --- |
| Technical metadata | schema, column types, table location, partitions, refresh time |
| Operational metadata | owners, job status, test results, freshness, incident history |
| Business metadata | descriptions, glossary terms, metric definitions, certified datasets |
| Governance metadata | sensitivity classification, access policy, retention rule, approved use |

## Lineage

Lineage shows where data came from and how it was transformed. It can be column-level, table-level, job-level, or report-level.

Lineage is valuable for:

- impact analysis before changing a source field;
- root cause analysis after a data incident;
- regulatory auditability;
- understanding metric definitions;
- identifying unused or duplicated assets.

Lineage is most valuable when tied to action. If a source column changes, lineage should help identify affected ingestion jobs, staging models, fact tables, dashboards, machine learning features, and consumers. If a quality alert fires, lineage should help trace the issue upstream and communicate impact downstream.

[[REPORTKIT-VISUAL:fig:sec07-lineage]]

## Governance

Governance includes ownership, access control, quality expectations, retention, privacy, definitions, and compliance.

Good governance is practical. It should make the right thing easy, not merely add approval steps. For example, a governed platform might automatically classify sensitive columns, apply access policies, and show approved datasets in a catalog.

Core governance questions include:

- Who owns this dataset?
- What does each critical field mean?
- Which dataset is the source of truth?
- Who is allowed to access it?
- Does it contain sensitive or regulated data?
- How long should it be retained?
- What downstream assets depend on it?
- What changes require review?
- What quality level is promised to consumers?

## Data Contracts

A data contract is an agreement between data producers and data consumers. It defines expectations about schema, data types, semantics, freshness, ownership, compatibility, and quality.

Data contracts are useful because many data failures originate upstream. A software team may rename a field, change a status code, alter an event payload, or stop populating a timestamp. If those changes are not communicated, pipelines break downstream.

A practical contract may include:

- dataset or event name;
- owner and contact path;
- schema and data types;
- field descriptions and semantic definitions;
- primary keys or event identifiers;
- freshness or delivery expectations;
- allowed schema evolution rules;
- quality expectations;
- deprecation process;
- examples of valid records.

Contracts should be version-controlled and tested where possible. The goal is not bureaucracy. The goal is to make producer-consumer expectations explicit before production data breaks.

## Access, Classification, and Retention

Governance also includes protecting sensitive data. Data may include personal information, payment details, health records, credentials, confidential business information, or regulated investment data.

Practical controls include:

- classifying sensitive columns;
- granting access by role and purpose;
- masking or tokenizing sensitive values;
- applying row-level or column-level security;
- encrypting data at rest and in transit;
- auditing access;
- defining retention and deletion rules;
- creating safe development datasets.

Security and compliance are discussed further in Section 8, but they are not separate from governance. A catalog that knows sensitivity, ownership, and lineage is much more useful than one that lists table names only.

## Governance Tooling Landscape

| Tool category | Purpose | Examples |
| --- | --- | --- |
| Catalogs | Search, describe, and certify data assets | DataHub, OpenMetadata, Amundsen, Alation, Collibra |
| Lineage tools | Trace upstream and downstream dependencies | dbt docs, OpenLineage, Marquez, DataHub |
| Policy and access control | Govern permissions and sensitive fields | Unity Catalog, Lake Formation, Apache Ranger, cloud IAM |
| Contract and schema tools | Manage producer-consumer expectations | schema registries, event schemas, contract tests |
| Glossary and metric layers | Standardize business meaning | semantic layers, BI metric stores, catalog glossaries |

## Serving Data for Analytics, Machine Learning, and Applications

Serving is the final stage where data becomes available to consumers. Different consumers need different serving patterns.

## Business Intelligence

Business intelligence tools need curated, well-modeled, queryable data. BI serving often uses warehouses, semantic layers, cubes, extracts, or dashboards connected to marts.

Important BI concerns include:

- consistent metric definitions;
- reasonable dashboard performance;
- understandable dimensions and filters;
- row-level security;
- documentation;
- freshness indicators.

## Machine Learning

Machine learning workflows need training data, features, labels, model outputs, and monitoring data. The same feature logic may need to run in batch for training and at low latency for prediction.

Feature stores help manage reusable features, but they do not remove the need for careful data engineering. Feature quality, point-in-time correctness, leakage prevention, and training-serving consistency are central concerns.

## Operational Applications

Some data products serve applications directly. Examples include recommendation APIs, fraud scoring systems, customer 360 views, inventory availability services, and personalization engines.

Application serving usually requires lower latency and stronger availability than analytical serving. Data may need to be pushed into caches, search indexes, key-value stores, or APIs designed for operational reads.

