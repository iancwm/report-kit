# Section 9 - A Learning Path and Project Roadmap

Data engineering is best learned by building systems. The following path moves from foundations to production thinking.

[[REPORTKIT-VISUAL:fig:sec09-learning-roadmap]]

## Core Skills

1. Learn SQL deeply: joins, windows, aggregation, CTEs, query plans, and indexing concepts.
2. Learn Python for data work: files, APIs, data validation, packaging, and testing.
3. Learn data modeling: facts, dimensions, grain, slowly changing dimensions, and semantic definitions.
4. Learn storage formats: CSV, JSON, Parquet, partitioning, compression, and schema evolution.
5. Learn orchestration: dependencies, retries, scheduling, and backfills.
6. Learn cloud basics: object storage, compute, IAM, networking basics, and cost.
7. Learn quality and observability: tests, freshness, reconciliation, alerts, and incidents.

## Portfolio Project

A strong beginner-to-intermediate project is a complete analytics pipeline:

1. Pull data from a public API.
2. Store raw responses.
3. Normalize and model the data.
4. Load it into a local warehouse or analytical database.
5. Add data quality tests.
6. Schedule the pipeline.
7. Create a dashboard or summary report.
8. Document lineage, assumptions, and known limitations.

Possible datasets include public transit arrivals, weather observations, stock prices, sports results, open government datasets, or e-commerce sample data.

## Advanced Project

An advanced project adds production-like concerns:

- change data capture or event streaming;
- schema drift handling;
- partitioned lakehouse tables;
- incremental models;
- automated backfills;
- data contracts;
- anomaly detection;
- access control design;
- cost and performance tuning;
- incident runbooks.

The goal is not just to move data. The goal is to operate a reliable data product.
