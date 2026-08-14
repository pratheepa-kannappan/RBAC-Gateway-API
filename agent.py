import requests

from langgraph_agent import (
    run_rbac_graph,
    resume_rbac_graph
)


# FASTAPI CONFIGURATION

APPROVE_URL = (
    "http://127.0.0.1:8000/api/approve"
)

# START AGENT WORKFLOW
def run_agent_workflow(
    user_id: str,
    resource_id: str,
    token: str = None,
    thread_id: str = None
):

    print("\n")
    print("=" * 60)
    print(
        f"Processing Request: "
        f"User={user_id} | Resource={resource_id}"
    )
    print("=" * 60)

    # Start LangGraph
    

    result = run_rbac_graph(

        user_id=user_id,

        resource_id=resource_id,

        token=token,

        thread_id=thread_id
    )

    
    # Print result
    

    print("\n")
    print("=" * 60)
    print("WORKFLOW RESULT")
    print("=" * 60)

    if result.get("final_response"):

        print(
            result["final_response"]
        )

    else:

        print(
            "Workflow is paused waiting for "
            "Team Lead approval."
        )

    print("=" * 60)

    return result


# TEAM LEAD APPROVAL


def approve_request(
    approval_token: str
):

    print("\n")
    print("=" * 60)
    print("TEAM LEAD APPROVAL")
    print("=" * 60)

    print(
        f"Approval Token: {approval_token}"
    )

    try:

        response = requests.post(

            APPROVE_URL,

            json={

                "approval_token":
                    approval_token
            },

            timeout=10
        )

        print(
            "\nFastAPI Approval Status:",
            response.status_code
        )

        try:

            data = response.json()

        except ValueError:

            data = {
                "error":
                    "Invalid JSON response"
            }

        print(
            "FastAPI Approval Response:"
        )

        import json

        print(
            json.dumps(
                data,
                indent=2
            )
        )

        return response.status_code, data

    except Exception as e:

        print(
            "\nApproval request failed:",
            str(e)
        )

        return 500, {
            "error": str(e)
        }

# RESUME AFTER TEAM LEAD APPROVAL


def resume_after_approval(
    thread_id: str
):

    print("\n")
    print("=" * 60)
    print("RESUMING APPROVAL WORKFLOW")
    print("=" * 60)

    print(
        f"Thread ID: {thread_id}"
    )


    # Command(resume="APPROVED")
    # happens inside resume_rbac_graph()
   

    result = resume_rbac_graph(

        thread_id=thread_id,

        decision="APPROVED"
    )

    print("\n")
    print("=" * 60)
    print("FINAL WORKFLOW RESULT")
    print("=" * 60)

    print(
        result.get(
            "final_response",
            "No final response generated."
        )
    )

    print("=" * 60)

    return result



# COMPLETE APPROVAL FLOW


def complete_approval_flow(
    user_id: str,
    resource_id: str,
    original_token: str = None,
    approval_token: str = None,
    thread_id: str = None
):


    # STEP 1
    # START WORKFLOW


    result = run_agent_workflow(

        user_id=user_id,

        resource_id=resource_id,

        token=original_token,

        thread_id=thread_id
    )

    # Get approval token from FastAPI response
  
    detail = result.get(
        "rbac_response",
        {}
    ).get(
        "detail",
        {}
    )

    if not approval_token:

        approval_token = detail.get(
            "approval_token"
        )

    # Get thread ID


    if not thread_id:

        if original_token:

            thread_id = (
                f"{user_id}_"
                f"{resource_id}_"
                f"{original_token}"
            )

        else:

            thread_id = (
                f"{user_id}_"
                f"{resource_id}_"
                f"NO_TOKEN"
            )


    # STEP 2
    # CHECK WHETHER APPROVAL IS REQUIRED
 

    approval_status = result.get(
        "approval_status"
    )

    if approval_status != "PENDING":

        print(
            "\nApproval is not pending."
        )

        return result

    if not approval_token:

        print(
            "\nNo approval token found."
        )

        return result


    # STEP 3
    # TEAM LEAD APPROVES


    approval_status_code, approval_response = (
        approve_request(
            approval_token
        )
    )


    # Approval failed


    if approval_status_code != 200:

        print(
            "\nTeam Lead approval failed."
        )

        return result

 
    # Verify APPROVED


    if approval_response.get(
        "status"
    ) != "APPROVED":

        print(
            "\nRequest was not approved."
        )

        return result

    # STEP 4
    # RESUME LANGGRAPH


    return resume_after_approval(
        thread_id
    )


# MAIN


if __name__ == "__main__":

    # TEST 1 — NORMAL GROUP ACCESS
    #
    # U001 has access to R001 through group membership.
    #
    # Expected:
    # FastAPI -> 200
    # RBAC    -> GRANTED


    run_agent_workflow(
        user_id="U001",
        resource_id="R001"
    )

    # TEST 2 — COMPLETE TEAM LEAD APPROVAL FLOW
    #
    # Flow:
    #
    # User requests R002
    #        ↓
    # FastAPI
    #        ↓
    # 403 PENDING
    #        ↓
    # LangGraph interrupt()
    #        ↓
    # Team Lead approves
    #        ↓
    # /api/approve
    #        ↓
    # APPROVED
    #        ↓
    # Command(resume="APPROVED")
    #        ↓
    # LangGraph resumes
    #        ↓
    # FastAPI with approval token
    #        ↓
    # 200 GRANTED
    #


    complete_approval_flow(
        user_id="U005",
        resource_id="R002",
        original_token="TOKEN_AI_PAYROLL_001"
    )
