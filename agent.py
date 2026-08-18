import requests
import json

from langgraph_agent import (
    run_rbac_graph,
    resume_rbac_graph
)

# FASTAPI CONFIGURATION

BASE_URL = "http://127.0.0.1:8000"

ACCESS_URL = (
    f"{BASE_URL}/api/access"
)

REQUEST_ACCESS_URL = (
    f"{BASE_URL}/api/request-access"
)

APPROVE_URL = (
    f"{BASE_URL}/api/approve"
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
    #
    # LangGraph calls:
    #
    # GET /api/access
    #
    # This endpoint ONLY checks the current access state.
    # It does NOT create an approval token.

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


# CREATE ACCESS REQUEST

def request_access(
    user_id: str,
    resource_id: str
):

    print("\n")
    print("=" * 60)
    print("CREATE ACCESS REQUEST")
    print("=" * 60)

    print(
        f"User     : {user_id}"
    )

    print(
        f"Resource : {resource_id}"
    )

    try:

        response = requests.post(

            REQUEST_ACCESS_URL,

            json={

                "user_id":
                    user_id,

                "resource_id":
                    resource_id
            },

            timeout=10
        )

        print(
            "\nFastAPI Request Status:",
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
            "FastAPI Request Response:"
        )

        print(
            json.dumps(
                data,
                indent=2
            )
        )

        return response.status_code, data

    except Exception as e:

        print(
            "\nAccess request failed:",
            str(e)
        )

        return 500, {
            "error": str(e)
        }


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
    # CHECK CURRENT ACCESS

    print("\n")
    print("=" * 60)
    print("STEP 1 — CHECK CURRENT ACCESS")
    print("=" * 60)

    result = run_agent_workflow(

        user_id=user_id,

        resource_id=resource_id,

        token=original_token,

        thread_id=thread_id
    )

    # Get current access status

    access_status = result.get(
        "access_status"
    )

    approval_status = result.get(
        "approval_status"
    )

    print(
        "\nCurrent Access Status:",
        access_status
    )

    print(
        "Current Approval Status:",
        approval_status
    )

    # STEP 2
    # CREATE ACCESS REQUEST IF REQUIRED

    if access_status == "GRANTED":

        print(
            "\nAccess already granted."
        )

        return result

    # If request is already pending, don't create
    # another request.

    if approval_status == "PENDING":

        print(
            "\nApproval request is already pending."
        )

    else:

        print("\n")
        print("=" * 60)
        print("STEP 2 — REQUEST APPROVAL")
        print("=" * 60)

        request_status_code, request_response = (
            request_access(

                user_id=user_id,

                resource_id=resource_id
            )
        )

        # Request creation failed

        if request_status_code not in (200, 201):

            print(
                "\nFailed to create access request."
            )

            return result

        # Get approval token

        approval_token = (
            request_response.get(
                "approval_token"
            )
        )

        if not approval_token:

            detail = request_response.get(
                "detail",
                {}
            )

            approval_token = (
                detail.get(
                    "approval_token"
                )
            )

        if not approval_token:

            print(
                "\nNo approval token returned."
            )

            return result

        print(
            "\nApproval Token:",
            approval_token
        )

    # STEP 3
    # CREATE / IDENTIFY THREAD

    if not thread_id:

        if approval_token:

            thread_id = (
                f"{user_id}_"
                f"{resource_id}_"
                f"{approval_token}"
            )

        elif original_token:

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

    print(
        "\nThread ID:",
        thread_id
    )

    # STEP 4
    # CHECK AGAIN
    #
    # The access request now exists in MySQL.
    #
    # GET /api/access
    #
    # should now return:
    #
    # PENDING
    #
    # LangGraph will then reach interrupt().


    print("\n")
    print("=" * 60)
    print("STEP 3 — RECHECK ACCESS")
    print("=" * 60)

    result = run_agent_workflow(

        user_id=user_id,

        resource_id=resource_id,

        token=approval_token,

        thread_id=thread_id
    )

    # STEP 5
    # VERIFY PENDING

    approval_status = result.get(
        "approval_status"
    )

    if approval_status != "PENDING":

        print(
            "\nExpected PENDING approval."
        )

        print(
            "Actual approval status:",
            approval_status
        )

        return result

    print("\n")
    print("=" * 60)
    print("WORKFLOW PAUSED")
    print("=" * 60)

    print(
        "Waiting for Team Lead approval."
    )

    print(
        f"Approval Token: {approval_token}"
    )

    print(
        f"Thread ID: {thread_id}"
    )

    # STEP 6
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

    # STEP 7
    # VERIFY APPROVAL


    if approval_response.get(
        "status"
    ) != "APPROVED":

        print(
            "\nRequest was not approved."
        )

        return result

    print("\n")
    print("=" * 60)
    print("TEAM LEAD APPROVED")
    print("=" * 60)

    print(
        "Status: APPROVED"
    )

    # STEP 8
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
    # Flow:
    #
    # User
    #   ↓
    # Agent
    #   ↓
    # LangGraph
    #   ↓
    # GET /api/access
    #   ↓
    # GRANTED
    #
    # No approval request is created.

    run_agent_workflow(

        user_id="U001",

        resource_id="R001"
    )

    # TEST 2 — COMPLETE TEAM LEAD APPROVAL FLOW
    #
    # Flow:
    #
    # User
    #   ↓
    # Agent
    #   ↓
    # LangGraph
    #   ↓
    # GET /api/access
    #   ↓
    # NOT_REQUESTED
    #   ↓
    # POST /api/request-access
    #   ↓
    # Approval Token Created
    #   ↓
    # GET /api/access
    #   ↓
    # PENDING
    #   ↓
    # interrupt()
    #   ↓
    # Team Lead
    #   ↓
    # POST /api/approve
    #   ↓
    # APPROVED
    #   ↓
    # Command(resume="APPROVED")
    #   ↓
    # LangGraph resumes
    #   ↓
    # GET /api/access + approved token
    #   ↓
    # GRANTED


    complete_approval_flow(

        user_id="U005",

        resource_id="R002"
    )
