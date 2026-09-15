# Agentic Financial Transaction Extraction

A multimodal LLM pipeline for extracting structured financial transaction data from heterogeneous bank and custodian documents.

The project combines **LLM-based document understanding**, **financial-domain rules**, **schema validation**, and **targeted repair** to transform unstructured transaction documents into normalized structured data.

## Overview

Financial transaction documents vary significantly between banks, custodians, transaction types, and document layouts.

Instead of relying on a single LLM call to extract an entire transaction, this project uses a multi-step workflow that decomposes the task into smaller stages.

The system:

1. Extracts document-level information
2. Classifies the financial transaction
3. Determines the expected transaction structure
4. Extracts cash and/or security movements
5. Builds a normalized transaction representation
6. Validates the extracted transaction
7. Repairs individual fields when validation fails

This allows probabilistic LLM extraction to be combined with deterministic financial-domain logic.

## Architecture

```mermaid
flowchart TD
    A[Transaction Document] --> B[Global Extraction]
    B --> C[Transaction Classification]
    C --> D[Movement Pattern Selection]

    D --> E[Security Extraction]
    D --> F[Cash Extraction]

    E --> G[Transaction Assembly]
    F --> G

    G --> H[Validation]

    H -->|No errors| I[Structured Transaction]
    H -->|Errors found| J[Targeted Repair]

    J --> H
