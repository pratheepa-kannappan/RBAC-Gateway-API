import json
import requests
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command

# CONFIGURATION

FASTAPI_URL = "http://127.0.0.1:8000/api/access"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1"

# LANGGRAPH STATE

class RBACState(TypedDict, total=False):
    # USER REQUEST
    user_id: str
    resource_id: str

    # Token supplied with request
    token: Optional[str]

    # Token created/returned for Team Lead approval
    approval_token: Optional[str]

    # FASTAPI RESPONSE

    status_code: int
    rbac_response: dict

    # ACCESS INFORMATION

    access_status: Optional[str]
    access_method: Optional[str]

    # APPROVAL INFORMATION

    approval_status: Optional[str]
    request_id: Optional[int]
    notified_lead: Optional[str]
    lead_email: Optional[str]


    # HUMAN DECISION
    human_decision: Optional[str]


    # FINAL RESPONSE
    final_response: str



# NODE 1
# CHECK RBAC

def check_rbac(state: RBACState):

    user_id = state["user_id"]
    resource_id = state["resource_id"]

    # Determine which token to send
    #
    # After Team Lead approval:
    #     approval_token is used
    #
    # Normal request:
    #     original token is used

    approval_token = state.get("approval_token")
    original_token = state.get("token")

    if approval_token:
        token = approval_token
    else:
        token = original_token

    print("\n")
    print("=" * 60)
    print("LANGGRAPH NODE: CHECK RBAC")
    print("=" * 60)

    print(f"User     : {user_id}")
    print(f"Resource : {resource_id}")

    if token:
        print(f"Token    : {token}")
    else:
        print("Token    : None")

    # BUILD FASTAPI PARAMETERS

    params = {
        "user_id": user_id,
        "resource_id": resource_id
    }

    if token:
        params["token"] = token

    # CALL FASTAPI

    try:

        response = requests.get(
            FASTAPI_URL,
            params=params,
            timeout=10
        )

        # Parse JSON

        try:

            response_data = response.json()

        except ValueError:

            response_data = {
                "error": "Invalid JSON response from FastAPI"
            }

        print("\nFastAPI Status:", response.status_code)

        print("FastAPI Response:")

        print(
            json.dumps(
                response_data,
                indent=2
            )
        )

        # GET ACTUAL RBAC DATA

        detail = response_data.get(
            "detail",
            {}
        )

        if isinstance(detail, dict) and detail:

            rbac_data = detail

        else:

            rbac_data = response_data

        # EXTRACT INFORMATION

        access_status = rbac_data.get(
            "status"
        )

        access_method = rbac_data.get(
            "access_method"
        )

        approval_status = rbac_data.get(
            "approval_status"
        )

        new_approval_token = rbac_data.get(
            "approval_token"
        )

        request_id = rbac_data.get(
            "request_id"
        )

        notified_lead = rbac_data.get(
            "notified_lead"
        )

        lead_email = rbac_data.get(
            "lead_email"
        )

        # CREATE STATE UPDATE

        result = {

            "status_code": response.status_code,

            "rbac_response": response_data,

            "access_status": access_status,

            "access_method": access_method,

            "approval_status": approval_status,

            "request_id": request_id,

            "notified_lead": notified_lead,

            "lead_email": lead_email
        }

        # If FastAPI returned an approval token,
        # store it in LangGraph state.

        if new_approval_token:

            result["approval_token"] = new_approval_token

        return result

    # FASTAPI CONNECTION ERROR

    except requests.exceptions.ConnectionError:

        print(
            "\nERROR: FastAPI server is not running."
        )

        return {

            "status_code": 500,

            "rbac_response": {
                "error": "FastAPI server is not running."
            },

            "access_status": "ERROR"
        }
    # OTHER ERROR

    except Exception as e:

        print(
            f"\nError calling FastAPI: {str(e)}"
        )

        return {

            "status_code": 500,

            "rbac_response": {
                "error": str(e)
            },

            "access_status": "ERROR"
        }

# ROUTER AFTER RBAC

def route_after_rbac(
    state: RBACState
):

    status_code = state.get(
        "status_code"
    )

    access_status = state.get(
        "access_status"
    )

    approval_status = state.get(
        "approval_status"
    )

    print("\n")
    print("=" * 60)
    print("LANGGRAPH ROUTER")
    print("=" * 60)

    # GRANTED

    if (
        status_code == 200
        and access_status == "GRANTED"
    ):

        print(
            "Decision: ACCESS GRANTED"
        )

        return "generate_response"

    # PENDING

    if approval_status == "PENDING":

        print(
            "Decision: APPROVAL REQUIRED"
        )

        return "approval_check"

    # REJECTED

    if approval_status == "REJECTED":

        print(
            "Decision: ACCESS REJECTED"
        )

        return "generate_response"

    # DENIED / ERROR

    print(
        "Decision: ACCESS NOT GRANTED"
    )

    return "generate_response"

# NODE 2
# APPROVAL CHECK
def approval_check(
    state: RBACState
):

    print("\n")
    print("=" * 60)
    print("LANGGRAPH NODE: APPROVAL CHECK")
    print("=" * 60)

    approval_status = state.get(
        "approval_status"
    )

    approval_token = state.get(
        "approval_token"
    )

    request_id = state.get(
        "request_id"
    )

    notified_lead = state.get(
        "notified_lead"
    )

    lead_email = state.get(
        "lead_email"
    )

    print(
        f"Approval Status : {approval_status}"
    )

    print(
        f"Approval Token  : {approval_token}"
    )

    print(
        f"Request ID      : {request_id}"
    )

    print(
        f"Team Lead       : {notified_lead}"
    )

    print(
        f"Lead Email      : {lead_email}"
    )

    return {

        "approval_status": approval_status,

        "approval_token": approval_token,

        "request_id": request_id,

        "notified_lead": notified_lead,

        "lead_email": lead_email
    }

# ROUTER AFTER APPROVAL CHECK

def route_after_approval_check(
    state: RBACState
):

    approval_status = state.get(
        "approval_status"
    )

    print("\n")
    print("=" * 60)
    print("APPROVAL ROUTER")
    print("=" * 60)

    print(
        "Approval Status:",
        approval_status
    )

    # PENDING

    if approval_status == "PENDING":

        return "waiting_for_approval"

    # APPROVED

    if approval_status == "APPROVED":
        return "check_rbac"

    # REJECTED

    if approval_status == "REJECTED":
        return "generate_response"
    return "generate_response"


# NODE 3
# WAIT FOR TEAM LEAD

def waiting_for_approval(
    state: RBACState
):

    print("\n")
    print("=" * 60)
    print("LANGGRAPH NODE: WAITING FOR APPROVAL")
    print("=" * 60)

    user_id = state.get(
        "user_id"
    )

    resource_id = state.get(
        "resource_id"
    )

    approval_token = state.get(
        "approval_token"
    )

    request_id = state.get(
        "request_id"
    )

    notified_lead = state.get(
        "notified_lead"
    )

    lead_email = state.get(
        "lead_email"
    )

    print(
        f"User      : {user_id}"
    )

    print(
        f"Resource  : {resource_id}"
    )

    print(
        f"Token     : {approval_token}"
    )

    print(
        f"Request ID: {request_id}"
    )

    print(
        f"Team Lead : {notified_lead}"
    )

    print(
        f"Email     : {lead_email}"
    )

    print("\n")
    print("=" * 60)
    print("LANGGRAPH INTERRUPT")
    print("=" * 60)

    # PAUSE WORKFLOW

    decision = interrupt({

        "type": "TEAM_LEAD_APPROVAL",

        "message": (
            "Team Lead approval is required."
        ),

        "user_id": user_id,

        "resource_id": resource_id,

        "request_id": request_id,

        "approval_token": approval_token,

        "team_lead": notified_lead,

        "lead_email": lead_email
    })


    # WORKFLOW RESUMED

    print("\n")
    print("=" * 60)
    print("LANGGRAPH RESUMED")
    print("=" * 60)

    print(
        "Team Lead Decision:",
        decision
    )

    # APPROVED

    if (
        isinstance(decision, str)
        and decision.upper() == "APPROVED"
    ):

        print(
            "Decision received: APPROVED"
        )

        return {

            "human_decision": "APPROVED",

            "approval_status": "APPROVED",

            # Important:
            # Use the approval token returned by
            # the original FastAPI request.

            "token": approval_token,

            "approval_token": approval_token
        }

    
    # REJECTED

    if (
        isinstance(decision, str)
        and decision.upper() == "REJECTED"
    ):

        print(
            "Decision received: REJECTED"
        )

        return {

            "human_decision": "REJECTED",

            "approval_status": "REJECTED"
        }


    print(
        "Unknown Team Lead decision."
    )

    return {

        "human_decision": "UNKNOWN"
    }

# ROUTER AFTER HUMAN DECISION

def route_after_human_decision(
    state: RBACState
):

    decision = state.get(
        "human_decision"
    )

    print("\n")
    print("=" * 60)
    print("HUMAN DECISION ROUTER")
    print("=" * 60)

    print(
        "Human Decision:",
        decision
    )

    # APPROVED

    if decision == "APPROVED":

        print(
            "Decision: RECHECK RBAC WITH APPROVED TOKEN"
        )

        return "check_rbac"

    # REJECTED


    if decision == "REJECTED":

        print(
            "Decision: ACCESS REJECTED"
        )

        return "generate_response"

    # UNKNOWN

    return "generate_response"


# NODE 4
# GENERATE NATURAL LANGUAGE RESPONSE

def generate_response(
    state: RBACState
):

    print("\n")
    print("=" * 60)
    print("LANGGRAPH NODE: GENERATE RESPONSE")
    print("=" * 60)

    user_id = state.get(
        "user_id"
    )

    resource_id = state.get(
        "resource_id"
    )

    status_code = state.get(
        "status_code"
    )

    access_status = state.get(
        "access_status"
    )

    approval_status = state.get(
        "approval_status"
    )

    rbac_response = state.get(
        "rbac_response",
        {}
    )

    # GRANTED

    if (
        status_code == 200
        and access_status == "GRANTED"
    ):

        prompt = f"""
You are an enterprise access management assistant.

User ID: {user_id}
Resource ID: {resource_id}

Access Status: GRANTED

RBAC Response:
{json.dumps(rbac_response, indent=2)}

Instructions:
- Clearly state that access has been granted.
- Mention the access method.
- Be professional.
- Do not invent information.
- Keep the response under 80 words.
"""

    # PENDING

    elif approval_status == "PENDING":

        prompt = f"""
You are an enterprise access management assistant.

User ID: {user_id}
Resource ID: {resource_id}

Access Status: PENDING

RBAC Response:
{json.dumps(rbac_response, indent=2)}

Instructions:
- Tell the user that access is pending Team Lead approval.
- Do not say access has been granted.
- Do not invent a Team Lead decision.
- Keep the response under 80 words.
"""
    # REJECTED

    elif approval_status == "REJECTED":

        prompt = f"""
You are an enterprise access management assistant.

User ID: {user_id}
Resource ID: {resource_id}

Access Status: REJECTED

RBAC Response:
{json.dumps(rbac_response, indent=2)}

Instructions:
- Clearly state that access was rejected.
- Do not say access was granted.
- Do not invent a reason.
- Keep the response under 80 words.
"""

    # DENIED / ERROR

    else:

        prompt = f"""
You are an enterprise access management assistant.

User ID: {user_id}
Resource ID: {resource_id}

Access Status: DENIED

RBAC Response:
{json.dumps(rbac_response, indent=2)}

Instructions:
- Clearly state that access is not available.
- Explain only the reason present in the RBAC response.
- Do not invent information.
- Keep the response under 80 words.
"""

    # CALL OLLAMA

    try:

        response = requests.post(

            OLLAMA_URL,

            json={

                "model": OLLAMA_MODEL,

                "prompt": prompt,

                "stream": False
            },

            timeout=120
        )

        response.raise_for_status()

        ai_response = response.json().get(
            "response",
            ""
        )

        if not ai_response:

            ai_response = (
                "Unable to generate an AI response."
            )

        return {

            "final_response": ai_response
        }

    except Exception as e:

        return {

            "final_response": (
                f"Unable to generate AI response: {str(e)}"
            )
        }

# BUILD LANGGRAPH

builder = StateGraph(
    RBACState
)

# ADD NODES


builder.add_node(
    "check_rbac",
    check_rbac
)

builder.add_node(
    "approval_check",
    approval_check
)

builder.add_node(
    "waiting_for_approval",
    waiting_for_approval
)

builder.add_node(
    "generate_response",
    generate_response
)

# START → CHECK RBAC


builder.add_edge(
    START,
    "check_rbac"
)

# CHECK RBAC → ROUTER

builder.add_conditional_edges(

    "check_rbac",

    route_after_rbac,

    {

        "approval_check":
            "approval_check",

        "generate_response":
            "generate_response"
    }
)

# APPROVAL CHECK → ROUTER

builder.add_conditional_edges(

    "approval_check",

    route_after_approval_check,

    {

        "waiting_for_approval":
            "waiting_for_approval",

        "check_rbac":
            "check_rbac",

        "generate_response":
            "generate_response"
    }
)


# WAITING FOR APPROVAL → HUMAN DECISION ROUTER

builder.add_conditional_edges(

    "waiting_for_approval",

    route_after_human_decision,

    {

        "check_rbac":
            "check_rbac",

        "generate_response":
            "generate_response"
    }
)


# GENERATE RESPONSE → END


builder.add_edge(
    "generate_response",
    END
)


# CHECKPOINT


checkpointer = InMemorySaver()


# COMPILE GRAPH

rbac_graph = builder.compile(
    checkpointer=checkpointer
)


# START RBAC WORKFLOW


def run_rbac_graph(
    user_id: str,
    resource_id: str,
    token: Optional[str] = None,
    thread_id: Optional[str] = None
):

    # CREATE SAFE THREAD ID
   

    if thread_id is None:

        if token:

            thread_id = (
                f"{user_id}_"
                f"{resource_id}_"
                f"{token}"
            )

        else:

            thread_id = (
                f"{user_id}_"
                f"{resource_id}_"
                f"NO_TOKEN"
            )

    print("\n")
    print("=" * 60)

    print(
        f"Processing Request: "
        f"User={user_id} | Resource={resource_id}"
    )

    print(
        f"Thread ID : {thread_id}"
    )

    print("=" * 60)

    # INITIAL STATE


    initial_state: RBACState = {

        "user_id": user_id,

        "resource_id": resource_id,

        "token": token,

        "approval_token": None,

        "approval_status": None,

        "human_decision": None
    }

    # LANGGRAPH CONFIG

    config = {

        "configurable": {

            "thread_id": thread_id
        }
    }


    # START GRAPH

    result = rbac_graph.invoke(

        initial_state,

        config=config
    )

    return result

# RESUME AFTER TEAM LEAD DECISION

def resume_rbac_graph(
    thread_id: str,
    decision: str
):

    print("\n")
    print("=" * 60)
    print("RESUMING LANGGRAPH WORKFLOW")
    print("=" * 60)

    print(
        f"Thread ID : {thread_id}"
    )

    print(
        f"Decision  : {decision}"
    )

    print("=" * 60)


    # SAME THREAD ID IS CRITICAL

    config = {

        "configurable": {

            "thread_id": thread_id
        }
    }

    # COMMAND RESUME


    result = rbac_graph.invoke(

        Command(
            resume=decision
        ),

        config=config
    )

    return result

# CHECK WHETHER WORKFLOW IS INTERRUPTED


def is_workflow_interrupted(
    thread_id: str
):

    config = {

        "configurable": {

            "thread_id": thread_id
        }
    }

    state = rbac_graph.get_state(
        config
    )

    return bool(
        state.next
    )


# DIRECT TEST

if __name__ == "__main__":

    result = run_rbac_graph(

        user_id="U005",

        resource_id="R002",

        token="TOKEN_AI_PAYROLL_001"
    )

    print("\n")
    print("=" * 60)
    print("WORKFLOW RESULT")
    print("=" * 60)

    print(
        result.get(
            "final_response",
            "Workflow paused or no response generated."
        )
    )

    print("=" * 60)
