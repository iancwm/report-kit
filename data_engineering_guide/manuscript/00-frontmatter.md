---
title: "A Practical Guide to Data Engineering"
subtitle: "Core Concepts, Systems, Pipelines, and Production Practices"
author: "ReportKit contributors"
date: "2026-09-06"
version: "Version 1.0"
license: "Original prose and diagrams are licensed CC BY 4.0; code examples and third-party assets retain their separate licences."
disclaimer: "Educational material only. Verify examples against your systems and current documentation; this guide is not operational, financial, legal, or security advice."
project-url: "https://github.com/iancwm/report-kit"
documentclass: article
papersize: a4
fontsize: 11pt
geometry: margin=1in
toc: true
toc-depth: 1
numbersections: false
---

## Preface

This guide introduces data engineering from first principles and then develops the subject into a practical map of the discipline. It begins with the central idea that data engineering is the work of designing, building, operating, and improving the systems that move data from raw sources into trustworthy forms that people and software can use.

The guide is prepared as a publication source. It uses ordinary Markdown headings, tables, and references so that the publication workflow can convert it to LaTeX. Formatting and diagram conventions for that workflow are collected separately in `publication-guidelines.md`.

## Reader's Roadmap

This linked roadmap is a reading aid for the Markdown manuscript; the generated publication table of contents remains the authoritative contents list.

- [Section 1 - Introduction to Data Engineering](#section-1---introduction-to-data-engineering)
- [Section 2 - Data Ingestion](#section-2---data-ingestion)
- [Section 3 - Data Storage](#section-3---data-storage)
- [Section 4 - Data Transformation and Processing](#section-4---data-transformation-and-processing)
- [Section 5 - Orchestration and Scheduling](#section-5---orchestration-and-scheduling)
- [Section 6 - Data Quality and Reliability](#section-6---data-quality-and-reliability)
- [Section 7 - Metadata, Governance, and Serving Data](#section-7---metadata-governance-and-serving-data)
- [Section 8 - Topics in Data Engineering](#section-8---topics-in-data-engineering)
- [Section 9 - A Learning Path and Project Roadmap](#section-9---a-learning-path-and-project-roadmap)
- [Section 10 - Glossary](#section-10---glossary)
- [Section 11 - References](#section-11---references)
