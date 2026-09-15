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

```text
Transaction Document
        │
        ▼
┌──────────────────────┐
│ Global Extraction    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Transaction          │
│ Classification       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Movement Pattern     │
│ Selection            │
└──────────┬───────────┘
           │
      ┌────┴─────┐
      ▼          ▼
┌───────────┐ ┌───────────┐
│ Security  │ │ Cash      │
│ Extraction│ │ Extraction│
└─────┬─────┘ └─────┬─────┘
      │              │
      └──────┬───────┘
             ▼
┌──────────────────────┐
│ Transaction Assembly │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Validation           │
└──────────┬───────────┘
           │
     Validation errors?
        ┌──┴──┐
       Yes    No
        │      │
        ▼      ▼
┌────────────┐ Structured
│ Targeted   │ Transaction
│ Repair     │
└─────┬──────┘
      │
      └──────► Re-validation
