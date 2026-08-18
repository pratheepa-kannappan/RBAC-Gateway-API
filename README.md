# RBAC Agent Gateway

## Project Overview

This project is a Role-Based Access Control (RBAC) Gateway that combines an AI Agent, LangGraph, FastAPI, MySQL, and Ollama with Llama 3.1.

The system allows a user to request access to a resource. The RBAC engine checks the user's permissions using data stored in MySQL. If access is available, the request is granted. If access requires Team Lead approval, the LangGraph workflow pauses until the Team Lead approves or rejects the request.

The final technical decision comes from the RBAC system. Llama 3.1 is used only to generate a natural-language response for the user.

---

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| FastAPI | Provides the RBAC REST API |
| MySQL | Stores users, groups, resources, permissions and access requests |
| LangGraph | Orchestrates the access-control workflow |
| AI Agent | Starts and manages the RBAC workflow |
| Ollama | Runs the Llama 3.1 model locally |
| Llama 3.1 | Generates the final natural-language response |
| Uvicorn | Runs the FastAPI application |
| Requests | Allows the Agent/LangGraph to communicate with FastAPI |
| Pydantic | Validates FastAPI request data |

---

## Project Structure

```text
rbac-agent-project/
│
├── agent.py
├── langgraph_agent.py
├── main.py
├── database.py
├── .env
├── requirements.txt
└── README.md
```

### agent.py

The main Agent workflow.

It:

- Receives the user request.
- Starts the LangGraph workflow.
- Handles the Team Lead approval process.
- Resumes the workflow after approval.
- Displays the final response.

### langgraph_agent.py

Contains the LangGraph workflow.

It:

- Calls FastAPI.
- Processes the RBAC result.
- Detects pending approval.
- Uses `interrupt()` to pause the workflow.
- Resumes the workflow using `Command(resume=...)`.
- Re-checks RBAC after approval.
- Calls Ollama/Llama 3.1 to generate the final response.

### main.py

Contains the FastAPI RBAC Gateway and provides four endpoints:

```text
GET  /
GET  /api/access
POST /api/approve
POST /api/reject
```

### database.py

Handles the MySQL database connection.

---

# System Architecture

```text
                         USER
                           │
                           ▼
                      agent.py
                      AI Agent
                           │
                           ▼
                       LangGraph
                     Orchestrator
                           │
                           ▼
                  GET /api/access
                           │
                           ▼
                       FastAPI
                     RBAC Engine
                           │
                           ▼
                         MySQL
                           │
                  ┌────────┴────────┐
                  │                 │
               GRANTED           PENDING
                  │                 │
                  │                 ▼
                  │            interrupt()
                  │                 │
                  │            Team Lead
                  │                 │
                  │        ┌────────┴────────┐
                  │        │                 │
                  │     APPROVE           REJECT
                  │        │                 │
                  │        ▼                 ▼
                  │ POST /api/approve   POST /api/reject
                  │        │                 │
                  │        ▼                 ▼
                  │    APPROVED          REJECTED
                  │        │                 │
                  │        ▼                 │
                  │ Command(resume)          │
                  │        │                 │
                  │        ▼                 │
                  │   Re-check RBAC          │
                  │        │                 │
                  └────────┴─────────────────┘
                           │
                           ▼
                    Access Decision
                           │
                           ▼
                        Ollama
                       Llama 3.1
                           │
                           ▼
                  Natural Language
                      Response
                           │
                           ▼
                          USER
```

---

# API Endpoints

The FastAPI application contains four endpoints.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Checks whether FastAPI is running |
| GET | `/api/access` | Performs the RBAC access evaluation |
| POST | `/api/approve` | Team Lead approves a pending request |
| POST | `/api/reject` | Team Lead rejects a pending request |

---

# 1. GET `/`

This endpoint checks whether the FastAPI application is running.

### Request

```text
GET http://127.0.0.1:8000/
```

### Response

```json
{
  "message": "RBAC Gateway API is active"
}
```

---

# 2. GET `/api/access`

This is the main RBAC access evaluation endpoint.

The Agent/LangGraph calls this endpoint when the user requests access.

Example:

```text
GET /api/access?user_id=U001&resource_id=R001
```

FastAPI checks the MySQL database to determine whether the user has permission.

The basic flow is:

```text
User Request
     │
     ▼
GET /api/access
     │
     ▼
RBAC Evaluation
     │
     ▼
MySQL
     │
     ├── Access Granted
     │
     └── Access Not Granted
              │
              ▼
        Pending Approval
```

### Example: Access Granted

```json
{
  "status": "GRANTED",
  "message": "Access granted for user 'U001' via group membership.",
  "user_id": "U001",
  "resource_id": "R001",
  "access_method": "GROUP_MEMBERSHIP",
  "resource_name": "Employee API"
}
```

### Example: Pending

```json
{
  "detail": {
    "status": "PENDING",
    "error": "Access Denied",
    "approval_status": "PENDING",
    "approval_token": "TOKEN_AI_PAYROLL_001",
    "request_id": 3,
    "user_id": "U005",
    "resource_id": "R002"
  }
}
```

The `/api/access` endpoint performs the RBAC evaluation. When the user does not have permission and an approval process is required, the current implementation returns the pending request information.

---

# 3. POST `/api/approve`

This endpoint is used by the Team Lead to approve a pending access request.

### Request

```text
POST /api/approve
```

JSON body:

```json
{
  "approval_token": "TOKEN_AI_PAYROLL_001"
}
```

FastAPI finds the request in MySQL and changes:

```text
PENDING → APPROVED
```

### Response

```json
{
  "status": "APPROVED",
  "message": "Access request approved successfully.",
  "request_id": 3,
  "user_id": "U005",
  "resource_id": "R002",
  "approval_token": "TOKEN_AI_PAYROLL_001"
}
```

---

# 4. POST `/api/reject`

This endpoint is used by the Team Lead to reject a pending access request.

### Request

```text
POST /api/reject
```

JSON body:

```json
{
  "approval_token": "TOKEN_AI_PAYROLL_001"
}
```

FastAPI updates the request in MySQL:

```text
PENDING → REJECTED
```

### Response

```json
{
  "status": "REJECTED",
  "message": "Access request rejected successfully.",
  "request_id": 3,
  "user_id": "U005",
  "resource_id": "R002",
  "approval_token": "TOKEN_AI_PAYROLL_001"
}
```

---

# Complete Workflow

## Step 1 — User Request

The user requests access to a resource.

Example:

```text
User     : U005
Resource : R002
```

The request enters the AI Agent.

---

## Step 2 — AI Agent

The Agent starts the LangGraph workflow.

Example:

```python
run_rbac_graph(
    user_id="U005",
    resource_id="R002"
)
```

The Agent does not directly decide whether the user has permission.

It starts and manages the workflow.

---

## Step 3 — LangGraph

LangGraph acts as the workflow orchestrator.

It calls:

```text
GET /api/access
```

and receives the RBAC result.

---

## Step 4 — FastAPI

FastAPI acts as the RBAC Gateway.

It receives the request and checks the MySQL database.

The RBAC engine evaluates:

- User
- Group membership
- Resource
- Group-resource permissions
- Existing access requests
- Approval status

---

# Case 1 — Access Granted

Example:

```text
U001 → R001
```

If the user has permission through group membership:

```text
MySQL
  ↓
Group Membership
  ↓
GRANTED
  ↓
LangGraph
  ↓
Ollama
  ↓
Natural Language Response
  ↓
User
```

Example response:

```text
Access has been granted to resource R001 through
your group membership.
```

---

# Case 2 — Approval Required

Example:

```text
U005 → R002
```

If the user does not have direct permission and an approval request is required:

```text
FastAPI
   ↓
PENDING
   ↓
LangGraph
   ↓
interrupt()
   ↓
WAIT
```

The LangGraph workflow pauses.

The Team Lead then decides whether to approve or reject the request.

---

# Case 3 — Team Lead Approves

The Team Lead calls:

```text
POST /api/approve
```

with:

```json
{
  "approval_token": "TOKEN_AI_PAYROLL_001"
}
```

FastAPI updates MySQL:

```text
PENDING
   ↓
APPROVED
```

The LangGraph workflow then resumes:

```python
Command(resume="APPROVED")
```

The workflow re-checks RBAC using the approved token.

```text
LangGraph
    ↓
Re-check RBAC
    ↓
GET /api/access
    ↓
FastAPI
    ↓
MySQL
    ↓
GRANTED
```

The final access decision is then passed to the response-generation stage.

---

# Case 4 — Team Lead Rejects

The Team Lead calls:

```text
POST /api/reject
```

with:

```json
{
  "approval_token": "TOKEN_AI_PAYROLL_001"
}
```

FastAPI updates MySQL:

```text
PENDING
   ↓
REJECTED
```

The user receives a response indicating that access was rejected.

---

# Role of Each Component

## AI Agent

The AI Agent is responsible for starting and coordinating the access request workflow.

```text
User
 ↓
AI Agent
 ↓
LangGraph
```

It connects the user request to the workflow.

---

## LangGraph

LangGraph is responsible for workflow orchestration.

It controls the sequence:

```text
CHECK RBAC
     ↓
GRANTED?
     │
     ├── YES → GENERATE RESPONSE
     │
     └── NO
          ↓
       PENDING?
          ↓
       interrupt()
          ↓
   Team Lead Decision
       │          │
       ▼          ▼
   APPROVED    REJECTED
       │          │
       ▼          ▼
 RE-CHECK RBAC  RESPONSE
       │
       ▼
    GRANTED
```

The major reason for using LangGraph is its ability to manage state and pause/resume the workflow for human approval.

---

## FastAPI

FastAPI is the API and RBAC Gateway layer.

It provides:

```text
GET  /
GET  /api/access
POST /api/approve
POST /api/reject
```

It communicates with MySQL and performs the RBAC-related operations.

---

## MySQL

MySQL stores the RBAC information.

It contains information such as:

```text
Users
Groups
Resources
User-Group relationships
Group-Resource permissions
Access Requests
Approval Tokens
Approval Status
```

The RBAC engine uses this data to make the access decision.

---

# GET vs POST

## GET

GET is used to retrieve or evaluate information.

In this project:

```text
GET /api/access
```

means:

```text
Evaluate the user's access to the requested resource.
```

Example:

```text
GET /api/access?user_id=U001&resource_id=R001
```

---

## POST

POST is used to submit an action that changes server-side state.

In this project:

```text
POST /api/approve
```

changes:

```text
PENDING → APPROVED
```

and:

```text
POST /api/reject
```

changes:

```text
PENDING → REJECTED
```

Therefore:

```text
GET
 ↓
RBAC access evaluation

POST
 ↓
Approval/Rejection action
```

---

# Ollama and Llama 3.1

Ollama is used to run the Llama 3.1 model locally.

The LLM is not the actual RBAC decision maker.

The RBAC engine makes the security decision.

The LLM generates a natural-language explanation based on the RBAC result.

```text
RBAC Decision
     ↓
GRANTED / PENDING / REJECTED / DENIED
     ↓
Ollama
     ↓
Llama 3.1
     ↓
Natural Language Response
     ↓
User
```

For example, the RBAC system may return:

```json
{
  "status": "GRANTED",
  "access_method": "GROUP_MEMBERSHIP"
}
```

Llama 3.1 can convert this into:

```text
Access has been granted to the requested resource
through your group membership.
```

The LLM does not independently grant access.

---

# Why This Architecture Is Used

The project separates responsibilities between the components.

```text
AI Agent
    ↓
Starts and coordinates the workflow

LangGraph
    ↓
Controls workflow and human-in-the-loop state

FastAPI
    ↓
Provides the RBAC API

MySQL
    ↓
Stores authorization data

RBAC Engine
    ↓
Makes the access decision

Ollama / Llama 3.1
    ↓
Generates the user-friendly response
```

This separation ensures that the LLM is not responsible for making the security decision.

The security decision comes from the RBAC logic and database.

---

# Running the Project

## 1. Start MySQL

Make sure MySQL is running and the RBAC database and tables have been created.

---

## 2. Start Ollama

Make sure Ollama is running and Llama 3.1 is available.

```bash
ollama run llama3.1
```

---

## 3. Start FastAPI

Activate the Python virtual environment:

```bash
venv\Scripts\activate
```

Run FastAPI:

```bash
uvicorn main:app --reload
```

FastAPI will run at:

```text
http://127.0.0.1:8000
```

---

## 4. Run the Agent

Open another terminal and activate the virtual environment:

```bash
venv\Scripts\activate
```

Then run:

```bash
python agent.py
```

---

# Example Complete Flow

```text
                         USER
                           │
                           ▼
                       agent.py
                           │
                           ▼
                       LangGraph
                           │
                           ▼
                  GET /api/access
                           │
                           ▼
                       FastAPI
                           │
                           ▼
                         MySQL
                           │
                ┌──────────┴──────────┐
                │                     │
             GRANTED               PENDING
                │                     │
                │                     ▼
                │                interrupt()
                │                     │
                │                Team Lead
                │                     │
                │             ┌───────┴───────┐
                │             │               │
                │          APPROVE          REJECT
                │             │               │
                │             ▼               ▼
                │       /api/approve    /api/reject
                │             │               │
                │             ▼               ▼
                │         APPROVED         REJECTED
                │             │
                │             ▼
                │       Resume LangGraph
                │             │
                │             ▼
                │        Re-check RBAC
                │             │
                └─────────────┘
                              │
                              ▼
                       Access Decision
                              │
                              ▼
                           Ollama
                              │
                         Llama 3.1
                              │
                              ▼
                   Natural Language Response
                              │
                              ▼
                             USER
```

---

# Important Design Principle

```text
LLM ≠ RBAC Decision Maker
```

The Llama 3.1 model does not decide whether the user should receive access.

The actual decision is made by the RBAC system using the database and authorization logic.

```text
MySQL + RBAC Logic
        ↓
  Access Decision
        ↓
     LangGraph
        ↓
   Llama 3.1
        ↓
User-friendly Response
```

This architecture provides a clear separation between:

1. **Authorization**
2. **Workflow orchestration**
3. **Human approval**
4. **Natural-language generation**
