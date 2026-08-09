# Dealer AI Copilot

### Agentic AI for Dealer Performance Analytics and Reporting

The **Dealer AI Copilot** is an agentic AI analytics system designed to help business users explore dealer performance data using natural language.

The system allows users to ask analytical questions in plain English and receive data-grounded answers, dealer performance scores, and visualizations without manually navigating multiple dashboards or writing SQL queries.

This project was developed as part of my **MSc in Data Science and Analytics at Academic City University**.

### Research Title

**Design and Evaluation of an Agentic AI Copilot for Dealer Performance Analytics and Reporting in Autochek Africa**

---

## Overview

In data-driven organizations, effective decision-making depends on timely access to accurate information.

However, business data is often distributed across multiple systems and dashboards. Generating insights can therefore require:

- manual reporting;
- technical expertise;
- SQL knowledge;
- navigating several dashboards;
- repeated data extraction and analysis.

The Dealer AI Copilot explores an alternative approach.

Instead of requiring a user to manually find and analyse the relevant data, the system provides a conversational interface through which users can ask questions in natural language.

The agent interprets the request, determines which analytical operation is required, invokes the appropriate tool, retrieves or processes the required data, and returns a clear response.

The overall goal is to:

> **Simplify data access, accelerate decision-making, and make dealer analytics more accessible to non-technical users.**

---

# Problem Statement

Dealer-performance information can be distributed across multiple datasets and analytical systems.

This creates three major challenges.

### 1. Data fragmentation

Relevant information may exist across different datasets, reports, and dashboards.

### 2. Reporting delays

Generating insights often requires manual analysis, which increases the time between asking a business question and receiving an answer.

### 3. Technical complexity

Accessing and interpreting business data may require SQL, analytical tools, or technical expertise.

These challenges can make operational decision-making slower and less accessible to non-technical stakeholders.

---

# Research Objectives

The study aimed to:

1. Create a unified dealer-performance view by integrating dealer listings, leads, applications, and sales.

2. Design and implement an agentic AI system capable of interpreting user requests, determining the necessary analytical steps, and retrieving dealer operational data.

3. Implement data-grounded reasoning using deterministic retrieval and dealer-scoring tools.

4. Establish a non-agent baseline system and compare its performance with the proposed agentic approach.

5. Develop a conversational interface that allows users to interact with both systems using natural-language prompts.

---

# System Design

The research compared two systems under the same experimental conditions:

### Baseline System

A deterministic, rule-based analytics system.

### Proposed Agentic System

An LLM-powered agent capable of interpreting natural-language requests and dynamically selecting analytical tools.

Both systems used:

- the same PostgreSQL database;
- the same dealer dataset;
- the same evaluation prompts;
- the same objective ground truth.

This made it possible to compare the systems fairly.

---

# Dataset Construction

The original dataset was based on a public vehicle-listings dataset obtained from Kaggle.

The source dataset contained approximately:

- **920 rows**
- **18 columns**

and included vehicle-listing information such as price, title, and posting date.

A Python data-generation and transformation process was used to adapt the dataset to the dealer-analytics research context.

Additional synthetic dealer activity was generated for:

- Listings
- Leads
- Applications
- Sales

The resulting analytical flow was:

```text
Listings
   ↓
Leads
   ↓
Applications
   ↓
Sales
```

The processed data was integrated into a **PostgreSQL database**, which served as the central source of truth for both the baseline and agentic systems.

Using synthetic dealer activity also allowed the research architecture to be evaluated without exposing confidential production information.

---

# Dealer Performance Scoring

A deterministic dealer-scoring method was developed to create a unified representation of dealer performance.

The system evaluates four major signals:

- Sales performance
- Inventory activity
- Application volume
- Lead activity

Because these metrics exist on different scales, each metric is normalized to a **0–100 range**.

This ensures that one metric does not dominate simply because its raw values are larger.

The normalized metrics are then combined using weighted scoring.

| Metric | Weight |
|---|---:|
| Sales | 40% |
| Inventory Activity | 25% |
| Applications | 25% |
| Leads | 10% |

The result is an overall dealer-performance score that combines multiple aspects of dealer activity into a consistent analytical measure.

The important architectural principle is that scoring is performed by deterministic code rather than calculated by the LLM.

---

# Baseline System

The baseline provides a non-agent comparison for the research.

It is implemented using predefined rules and SQL query templates.

The baseline:

- matches user requests to known patterns;
- executes predetermined SQL queries;
- produces deterministic results;
- returns the same result for the same supported request.

### Strength

For known and simple analytical requests, the baseline is efficient and reliable.

### Limitation

The system cannot easily adapt when:

- a request is phrased differently;
- several analytical conditions are combined;
- the user asks a multi-step question;
- the query falls outside the predefined templates.

This makes the baseline effective for structured tasks but less flexible for natural business-language interaction.

---

# Proposed Agentic System

The proposed system uses a **Large Language Model as the reasoning layer** and deterministic tools as the execution layer.

A simple way to think about the architecture is:

> **The agent is the brain. The tools are the hands.**

The LLM is responsible for:

- interpreting the user's request;
- understanding intent;
- identifying the required analytical operation;
- deciding which tool should be called;
- interpreting the tool output;
- generating a human-readable response.

The LLM does **not** directly calculate business metrics or invent analytical values.

Instead, calculations and data retrieval are performed using deterministic tools.

---

# Root Agent and Tools

The final system uses one primary **root agent**.

The root agent receives the user's natural-language request and dynamically selects the appropriate tool.

Three core tools support the agent.

## 1. `db_query`

Used for retrieving structured information from the PostgreSQL database.

Example questions include:

```text
How many dealers are in the database?
```

```text
Which dealers generated the most sales?
```

```text
Show dealer applications for this period.
```

The purpose of the database tool is to ensure that responses are grounded in actual database results rather than the language model's internal knowledge.

---

## 2. `score_dealers`

Used to calculate and rank dealer performance using the defined scoring methodology.

For example:

```text
Show me the highest-performing dealers.
```

```text
Rank dealers according to their performance.
```

The agent interprets the request and invokes the scoring tool.

The scoring itself remains deterministic.

This separation is important:

```text
LLM
↓
Understands what the user wants

Tool
↓
Performs the actual calculation

LLM
↓
Explains the result
```

---

## 3. `chart_tool`

Used to generate visualizations when a graphical representation of the analysis is useful.

For example:

```text
Show dealer sales as a chart.
```

```text
Visualize the top-performing dealers.
```

```text
Compare applications across dealers.
```

The chart tool converts analytical results into visual outputs that make patterns and comparisons easier for users to understand.

---

# How the Agent Works

A typical interaction follows this workflow:

```text
1. User asks a question
        ↓
2. Root agent interprets the request
        ↓
3. Agent identifies the metric, filters, and analytical task
        ↓
4. Agent selects the appropriate tool
        ↓
5. Tool retrieves or calculates the required information
        ↓
6. Agent interprets the tool result
        ↓
7. User receives a clear natural-language answer
        ↓
8. Chart is generated when appropriate
```

For example:

```text
User:
Show me the top five dealers by performance.
```

The root agent identifies that the request requires dealer scoring and invokes:

```text
score_dealers
```

The deterministic scoring function calculates the ranking.

The agent then converts the structured result into an understandable response.

---

# System Architecture

```text
                    ┌─────────────────────┐
                    │        User         │
                    └──────────┬──────────┘
                               │
                     Natural-language query
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Streamlit UI     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Root Agent      │
                    │     Google ADK      │
                    └──────────┬──────────┘
                               │
                    Dynamic Tool Selection
                               │
              ┌────────────────┼─────────────────┐
              │                │                 │
              ▼                ▼                 ▼
       ┌────────────┐   ┌──────────────┐   ┌────────────┐
       │  db_query  │   │score_dealers │   │ chart_tool │
       └──────┬─────┘   └──────┬───────┘   └──────┬─────┘
              │                │                  │
              └────────────────┼──────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ MCP / Tool Layer    │
                    │ Safe Data Access    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    PostgreSQL       │
                    │    Dealer Data      │
                    └─────────────────────┘
```

---

# Why Tool-Grounded Agentic AI?

A major design principle of the project is the separation of:

```text
Reasoning
```

from:

```text
Execution
```

The language model provides flexibility in understanding natural-language requests.

The tools provide reliability.

For example, the LLM should not estimate the number of dealer sales itself.

Instead:

```text
User Question
      ↓
LLM interprets question
      ↓
db_query retrieves actual value
      ↓
LLM explains actual result
```

This provides a more reliable architecture for business analytics.

---

# Safe Database Access

The system architecture includes a controlled tool/MCP layer between the agent and the PostgreSQL database.

This allows database interaction to remain structured and controlled.

The objective is to prevent the language model from having unrestricted control over the database while still allowing it to answer analytical questions.

The system therefore follows an important enterprise-AI principle:

> **The model reasons about what should be done, while controlled tools determine what it is allowed to do.**

---

# User Interface

A **Streamlit interface** provides the conversational front end.

Users can enter questions using plain English rather than manually writing database queries.

Example interactions include:

```text
Which dealers have the highest sales?
```

```text
Show the five best-performing dealers.
```

```text
How many applications were generated?
```

```text
Compare dealer performance.
```

```text
Create a chart showing the top dealers.
```

The objective is to reduce the analytical barrier between business users and operational data.

---

# Evaluation

The study evaluated both the baseline system and the proposed agentic system using the same conditions.

### Evaluation Dataset

A set of **13 structured natural-language prompts (T1–T13)** was created.

The prompts represented common analytical tasks including:

- data retrieval;
- dealer ranking;
- metric analysis;
- multi-step analytical questions.

### Ground Truth

Correct results were calculated directly from the **PostgreSQL database**.

This created an objective reference against which system responses could be compared.

---

# Evaluation Metrics

Three metrics were used.

## 1. Numeric Accuracy

Measures whether numerical results match the PostgreSQL ground truth.

The evaluation considered factors such as:

- correct metric;
- correct filter;
- correct date range;
- correct numerical value;
- correct ranking.

Output:

```text
Accurate = 1
Inaccurate = 0
```

---

## 2. Task Completion

Measures whether the system fully satisfies the user's analytical request.

Scoring:

```text
1.0 = Full completion
0.5 = Partial completion
0.0 = Failed
```

This metric is particularly important for multi-step queries.

---

## 3. Efficiency

Measures the amount of processing required to complete a task.

For the agentic system, this is represented by the number of **tool calls**.

For the baseline, it is represented by the number of processing steps.

This allows the research to examine the trade-off between flexibility and computational effort.

---

# Results

| Metric | Baseline | Agentic System |
|---|---:|---:|
| Numeric Accuracy | 100% | 100% |
| Full Task Completion | 80% | 100% |
| Average Completion Score | 0.85 | 1.00 |
| Average Steps / Tool Calls | 1.15 | 2.20 |

Both systems achieved **100% numeric accuracy** on successfully executed structured queries.

The key difference was task completion.

The agentic system successfully handled more complex and multi-step requests, achieving a **100% full-completion rate**, compared with **80% for the rule-based baseline**.

However, that flexibility came at a cost.

The agentic system required more tool calls on average.

---

# Key Finding

The main improvement from the agentic architecture was **not numeric accuracy**.

Both systems were capable of returning accurate numerical results.

The improvement was in:

- flexibility;
- task completion;
- interpretation of natural-language requests;
- ability to handle multi-part analytical questions.

This led to an important research finding:

> **Agentic AI increased task-completion capability while maintaining the same numeric accuracy as the deterministic baseline.**

The trade-off was increased processing steps.

---

# Conclusion

The research demonstrates that a tool-grounded agentic AI architecture can provide a practical approach to conversational dealer analytics.

The agentic system combines:

- natural-language understanding;
- deterministic database retrieval;
- dealer-performance scoring;
- analytical visualization;
- controlled database access.

Rather than replacing traditional analytics, the copilot provides a conversational layer on top of structured analytical systems.

The final architecture follows the principle:

```text
Natural Language
      ↓
Agent Reasoning
      ↓
Deterministic Tools
      ↓
Structured Data
      ↓
Grounded Answer
```

The results suggest that agentic AI is particularly useful when analytical requests become more flexible, complex, or multi-step.

---

# Technology Stack

### AI & Orchestration

- Large Language Models
- Google Agent Development Kit (ADK)
- Tool-augmented reasoning

### Data

- PostgreSQL
- SQL
- Python
- Pandas

### Application

- Streamlit

### Analytical Tools

- Database query tool
- Dealer scoring tool
- Chart-generation tool

### Research & Evaluation

- Synthetic dealer activity data
- Deterministic PostgreSQL ground truth
- Structured natural-language evaluation prompts

---

# Research Outputs

The Dealer AI Copilot was presented as part of my MSc research through both a research poster and a technical presentation.

The research materials cover:

- research motivation;
- literature review;
- dataset construction;
- dealer-scoring methodology;
- baseline architecture;
- agentic architecture;
- tool design;
- evaluation methodology;
- experimental results;
- research conclusions.

---

# Author

**Regina Adobea Essien (Adobea)**

Data Scientist & AI Researcher

Research interests:

- Agentic AI
- Applied Machine Learning
- Statistical Modelling
- Conversational Analytics
- Decision-Support Systems
- Responsible AI
- AI Strategy

GitHub: [adobea-dev](https://github.com/adobea-dev)

LinkedIn: [Adobea Essien](https://www.linkedin.com/in/adobea-essien/)
