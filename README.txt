# 🏢 Company Assistant

**Company Assistant** is an AI-powered multi-agent system designed to help companies streamline **customer interactions** and **automatable workflows** through a conversational assistant.  

It integrates **retrieval-augmented generation (RAG)**, **multi-agent coordination**, **observability**, and **moderation guardrails** into a single robust architecture.  

---

## 🎯 Objectives

- Provide companies with a **chatbot assistant** that can answer customer FAQs, retrieve knowledge, and assist with task automation.  
- Ensure **secure, moderated, and reliable** responses using Guardrails.  
- Enable **scalable architectures** with message queues and pipelines for enterprise-level workloads.  
- Deliver **observability and metrics** to monitor agent performance and behaviors.  

---

## 🛠️ Tech Stack

- **LangGraph & LangChain** → Multi-agent orchestration and reasoning.  
- **LangSmith** → Observability, tracing, and evaluation of agents (**LLMOps**).  
- **LlamaIndex** → Chunking & retrieval (RAG pipeline).  
- **AWS (S3, RDS)** → Storage and relational database backend.  
- **RabbitMQ** → Message queue for data pipeline orchestration.  
- **FastMCP** → MCP servers exposing dynamic tools.  
- **FastAPI** → Backend server for APIs and orchestration.  
- **Guardrails AI** → Moderation and safety guardrails.  
- **GitHub Actions** → CI/CD for automated testing and deployment.  

---

## ⚙️ Architecture Overview

1. **Data Ingestion Pipeline** → Documents uploaded to S3 are processed, chunked, and embedded using **LlamaIndex**, stored in PostgreSQL (RDS).  
2. **Multi-Agent System** → Built with **LangGraph + LangChain**, supervised and orchestrated by a central agent.  
3. **MCP Tools** → Exposed via **FastMCP**, such as FAQ queries and document search.  
4. **Guardrails Node** → Final moderation layer ensuring safe, non-toxic responses.  
5. **Observability** → **LangSmith** captures traces, metrics, and evaluation of agent decisions.  
6. **CI/CD** → Automated workflows with **GitHub Actions** to test and deploy updates.  

---

## 🚀 Getting Started

### 1️⃣ Prerequisites
- Python 3.10+
- PostgreSQL with `pgvector` extension
- RabbitMQ
- AWS account (S3 + RDS)