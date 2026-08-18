from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
import uuid
from database import get_db_connection

# FASTAPI APPLICATION
app = FastAPI(
    title="RBAC Gateway API",
    description="Role-Based Access Control Gateway",
    version="2.0.0"
)

# REQUEST MODELS
class ApprovalRequest(BaseModel):
    approval_token: str
class RejectionRequest(BaseModel):
    approval_token: str
class AccessRequest(BaseModel):
    user_id: str
    resource_id: str

# TEAM LEAD NOTIFICATION
def notify_team_lead(
    lead_name: str,
    lead_email: str,
    user_id: str,
    resource_id: str,
    approval_token: str,
    request_id: int
):

    print("\n" + "=" * 60)
    print("TEAM LEAD NOTIFICATION")
    print("=" * 60)
    print(f"Team Lead      : {lead_name}")
    print(f"Email          : {lead_email}")
    print(f"User           : {user_id}")
    print(f"Resource       : {resource_id}")
    print(f"Request ID     : {request_id}")
    print(f"Approval Token : {approval_token}")
    print("=" * 60)
    print("Waiting for Team Lead decision...")
    print("=" * 60 + "\n")

# HOME

@app.get("/")
def home():

    return {
        "message": "RBAC Gateway API is active"
    }

# GET /api/access
#
# IMPORTANT:
#
# THIS ENDPOINT ONLY CHECKS ACCESS.
#
# IT DOES NOT:
# - create a token
# - create an access request
# - notify Team Lead
# - insert anything into the database
#
# Possible results:
#
# GRANTED
# PENDING
# REJECTED
# DENIED

@app.get("/api/access")
def check_access(
    user_id: str,
    resource_id: str,
    token: str = None
):

    conn = get_db_connection()

    if not conn:

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database connection failed"
            }
        )

    cursor = conn.cursor(
        dictionary=True,
        buffered=True
    )

    try:

        # STEP 1
        # CHECK GROUP-BASED ACCESS

        rbac_query = """
        SELECT
            r.resource_name,
            r.api_endpoint
        FROM user_groups_1 ug

        JOIN group_resources_1 gr
            ON ug.group_id = gr.group_id

        JOIN resources_1 r
            ON gr.resource_id = r.r_id

        WHERE ug.user_id = %s
          AND r.r_id = %s
        """

        cursor.execute(
            rbac_query,
            (
                user_id,
                resource_id
            )
        )

        permission = cursor.fetchone()

        # GROUP ACCESS FOUND
        if permission:

            return {

                "status": "GRANTED",

                "message": (
                    f"Access granted for user "
                    f"'{user_id}' via group membership."
                ),

                "user_id": user_id,

                "resource_id": resource_id,

                "access_method": (
                    "GROUP_MEMBERSHIP"
                ),

                "resource_name": (
                    permission["resource_name"]
                ),

                "data": (
                    "Sensitive payload retrieved from "
                    f"{permission['api_endpoint']}"
                )
            }
        # STEP 2
        # IF TOKEN WAS PROVIDED, CHECK IT

        if token:

            token_query = """
            SELECT
                request_id,
                user_id,
                resource_id,
                approval_token,
                status
            FROM access_requests_1
            WHERE user_id = %s
              AND resource_id = %s
              AND approval_token = %s
            """
            cursor.execute(
                token_query,
                (
                    user_id,
                    resource_id,
                    token
                )
            )
            token_request = cursor.fetchone()

            # TOKEN FOUND

            if token_request:
                # APPROVED TOKEN
                
                if token_request["status"] == "APPROVED":

                    return {

                        "status": "GRANTED",

                        "message": (
                            "Access granted via approved "
                            "Team Lead token."
                        ),

                        "user_id": user_id,

                        "resource_id": resource_id,

                        "access_method": (
                            "APPROVED_TOKEN"
                        ),

                        "request_id": (
                            token_request["request_id"]
                        ),

                        "data": (
                            "Sensitive payload retrieved "
                            "using approved request token."
                        )
                    }

                # PENDING TOKEN

                if token_request["status"] == "PENDING":

                    lead_query = """
                    SELECT DISTINCT
                        u.user_id AS lead_id,
                        u.name AS lead_name,
                        u.email AS lead_email
                    FROM group_resources_1 gr

                    JOIN groups_1 g
                        ON gr.group_id = g.group_id

                    JOIN users_1 u
                        ON g.team_lead_id = u.user_id

                    WHERE gr.resource_id = %s
                    """

                    cursor.execute(
                        lead_query,
                        (resource_id,)
                    )

                    lead_info = cursor.fetchone()

                    return {

                        "status": "PENDING",

                        "message": (
                            "Access request is waiting "
                            "for Team Lead approval."
                        ),

                        "user_id": user_id,

                        "resource_id": resource_id,

                        "access_method": (
                            "PENDING_APPROVAL"
                        ),

                        "request_id": (
                            token_request["request_id"]
                        ),

                        "approval_token": (
                            token_request["approval_token"]
                        ),

                        "approval_status": "PENDING",

                        "notified_lead": (
                            lead_info["lead_name"]
                            if lead_info
                            else "Unknown"
                        ),

                        "lead_email": (
                            lead_info["lead_email"]
                            if lead_info
                            else None
                        )
                    }

                # REJECTED TOKEN

                if token_request["status"] == "REJECTED":

                    return {

                        "status": "REJECTED",

                        "message": (
                            "The access request was "
                            "rejected by the Team Lead."
                        ),

                        "user_id": user_id,

                        "resource_id": resource_id,

                        "access_method": (
                            "REJECTED_TOKEN"
                        ),

                        "request_id": (
                            token_request["request_id"]
                        ),

                        "approval_token": (
                            token_request["approval_token"]
                        ),

                        "approval_status": "REJECTED"
                    }

            # INVALID TOKEN

            return {

                "status": "DENIED",

                "message": (
                    "The supplied approval token is "
                    "invalid for this user and resource."
                ),

                "user_id": user_id,

                "resource_id": resource_id,

                "access_method": "INVALID_TOKEN",

                "approval_status": "DENIED"
            }

        # STEP 3
        # NO TOKEN
        #
        # CHECK WHETHER A REQUEST ALREADY EXISTS

        pending_query = """
        SELECT
            request_id,
            user_id,
            resource_id,
            approval_token,
            status,
            created_at
        FROM access_requests_1
        WHERE user_id = %s
          AND resource_id = %s
          AND status = 'PENDING'
        ORDER BY created_at DESC
        LIMIT 1
        """

        cursor.execute(
            pending_query,
            (
                user_id,
                resource_id
            )
        )

        existing_pending = cursor.fetchone()

        # EXISTING PENDING REQUEST

        if existing_pending:

            lead_query = """
            SELECT DISTINCT
                u.user_id AS lead_id,
                u.name AS lead_name,
                u.email AS lead_email
            FROM group_resources_1 gr

            JOIN groups_1 g
                ON gr.group_id = g.group_id

            JOIN users_1 u
                ON g.team_lead_id = u.user_id

            WHERE gr.resource_id = %s
            """

            cursor.execute(
                lead_query,
                (resource_id,)
            )

            lead_info = cursor.fetchone()

            return {

                "status": "PENDING",

                "message": (
                    "An access request is already "
                    "pending Team Lead approval."
                ),

                "user_id": user_id,

                "resource_id": resource_id,

                "access_method": (
                    "PENDING_APPROVAL"
                ),

                "request_id": (
                    existing_pending["request_id"]
                ),

                "approval_token": (
                    existing_pending["approval_token"]
                ),

                "approval_status": "PENDING",

                "notified_lead": (
                    lead_info["lead_name"]
                    if lead_info
                    else "Unknown"
                ),

                "lead_email": (
                    lead_info["lead_email"]
                    if lead_info
                    else None
                )
            }

        # STEP 4
        # NO ACCESS
        #
        # IMPORTANT:
        #
        # DO NOT CREATE A REQUEST HERE.
        #
        # The agent must call:
        #
        # POST /api/request-access
        #
        # if it wants to request Team Lead approval.

        return {

            "status": "DENIED",

            "message": (
                "User does not have access to this resource."
            ),

            "user_id": user_id,

            "resource_id": resource_id,

            "access_method": "NO_PERMISSION",

            "approval_status": "NOT_REQUESTED"
        }

    except Exception as e:

        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal RBAC Server Error",
                "message": str(e)
            }
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass

        try:
            conn.close()
        except Exception:
            pass

# POST /api/request-access
#
# THIS ENDPOINT CREATES A NEW APPROVAL REQUEST.
#
# Flow:
#
# Agent
#   ↓
# POST /api/request-access
#   ↓
# Find Team Lead
#   ↓
# Generate approval token
#   ↓
# INSERT PENDING
#   ↓
# Notify Team Lead

@app.post("/api/request-access")
def request_access(
    request: AccessRequest,
    background_tasks: BackgroundTasks
):

    conn = get_db_connection()

    if not conn:

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database connection failed"
            }
        )

    cursor = conn.cursor(
        dictionary=True,
        buffered=True
    )

    try:

        user_id = request.user_id
        resource_id = request.resource_id
        # STEP 1
        # CHECK WHETHER USER ALREADY HAS ACCESS

        rbac_query = """
        SELECT
            r.resource_name,
            r.api_endpoint
        FROM user_groups_1 ug

        JOIN group_resources_1 gr
            ON ug.group_id = gr.group_id

        JOIN resources_1 r
            ON gr.resource_id = r.r_id

        WHERE ug.user_id = %s
          AND r.r_id = %s
        """

        cursor.execute(
            rbac_query,
            (
                user_id,
                resource_id
            )
        )
        permission = cursor.fetchone()
        if permission:
            return {
                "status": "GRANTED",

                "message": (
                    "User already has access through "
                    "group membership. No approval "
                    "request was created."
                ),

                "user_id": user_id,

                "resource_id": resource_id,

                "access_method": (
                    "GROUP_MEMBERSHIP"
                )
            }
        # STEP 2
        # CHECK EXISTING PENDING REQUEST

        pending_query = """
        SELECT
            request_id,
            user_id,
            resource_id,
            approval_token,
            status
        FROM access_requests_1
        WHERE user_id = %s
          AND resource_id = %s
          AND status = 'PENDING'
        ORDER BY created_at DESC
        LIMIT 1
        """

        cursor.execute(
            pending_query,
            (
                user_id,
                resource_id
            )
        )

        existing_pending = cursor.fetchone()

        if existing_pending:

            return {

                "status": "PENDING",

                "message": (
                    "An access request is already "
                    "pending Team Lead approval."
                ),

                "user_id": user_id,

                "resource_id": resource_id,

                "request_id": (
                    existing_pending["request_id"]
                ),

                "approval_token": (
                    existing_pending["approval_token"]
                ),

                "approval_status": "PENDING"
            }

        # STEP 3
        # FIND TEAM LEAD

        lead_query = """
        SELECT DISTINCT
            u.user_id AS lead_id,
            u.name AS lead_name,
            u.email AS lead_email
        FROM group_resources_1 gr

        JOIN groups_1 g
            ON gr.group_id = g.group_id

        JOIN users_1 u
            ON g.team_lead_id = u.user_id

        WHERE gr.resource_id = %s
        """

        cursor.execute(
            lead_query,
            (resource_id,)
        )

        lead_info = cursor.fetchone()

        if not lead_info:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "DENIED",
                    "error": "Access Denied",
                    "message": (
                        "No Team Lead is configured "
                        "for this resource."
                    ),
                    "user_id": user_id,
                    "resource_id": resource_id
                }
            )
        # STEP 4
        # GENERATE APPROVAL TOKEN

        approval_token = (
            f"TOKEN_{uuid.uuid4().hex[:8].upper()}"
        )

        # STEP 5
        # CREATE PENDING REQUEST

        insert_query = """
        INSERT INTO access_requests_1
        (
            user_id,
            resource_id,
            approval_token,
            status
        )
        VALUES
        (
            %s,
            %s,
            %s,
            'PENDING'
        )
        """

        cursor.execute(
            insert_query,
            (
                user_id,
                resource_id,
                approval_token
            )
        )

        conn.commit()

        request_id = cursor.lastrowid

        # STEP 6
        # NOTIFY TEAM LEAD

        background_tasks.add_task(
            notify_team_lead,
            lead_info["lead_name"],
            lead_info["lead_email"],
            user_id,
            resource_id,
            approval_token,
            request_id
        )

        # STEP 7
        # RESPONSE

        return {
            "status": "PENDING",
            "message": (
                "Access request created successfully "
                "and sent to the Team Lead."
            ),
            "user_id": user_id,
            "resource_id": resource_id,
            "request_id": request_id,
            "approval_token": approval_token,
            "approval_status": "PENDING",
            "notified_lead": (
                lead_info["lead_name"]
            ),

            "lead_email": (
                lead_info["lead_email"]
            )
        }

    except HTTPException:
        raise

    except Exception as e:

        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail={
                "error": (
                    "Access request creation failed"
                ),
                "message": str(e)
            }
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass

        try:
            conn.close()
        except Exception:
            pass

# POST /api/approve
# PENDING → APPROVED

@app.post("/api/approve")
def approve_access(
    request: ApprovalRequest
):

    conn = get_db_connection()

    if not conn:

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database connection failed"
            }
        )

    cursor = conn.cursor(
        dictionary=True,
        buffered=True
    )

    try:
        # FIND REQUEST

        select_query = """
        SELECT
            request_id,
            user_id,
            resource_id,
            approval_token,
            status
        FROM access_requests_1
        WHERE approval_token = %s
        """

        cursor.execute(
            select_query,
            (request.approval_token,)
        )

        access_request = cursor.fetchone()

        if not access_request:

            raise HTTPException(
                status_code=404,
                detail={
                    "error": (
                        "Approval request not found"
                    ),
                    "approval_token": (
                        request.approval_token
                    )
                }
            )

        # CHECK STATUS

        if access_request["status"] != "PENDING":

            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Request is not pending",
                    "current_status": (
                        access_request["status"]
                    ),
                    "approval_token": (
                        request.approval_token
                    )
                }
            )

        # APPROVE

        update_query = """
        UPDATE access_requests_1
        SET status = 'APPROVED'
        WHERE approval_token = %s
          AND status = 'PENDING'
        """

        cursor.execute(
            update_query,
            (request.approval_token,)
        )
        conn.commit()
        return {
            "status": "APPROVED",
            "message": (
                "Access request approved successfully."
            ),
            "request_id": (
                access_request["request_id"]
            ),
            "user_id": (
                access_request["user_id"]
            ),
            "resource_id": (
                access_request["resource_id"]
            ),
            "approval_token": (
                access_request["approval_token"]
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Approval processing failed",
                "message": str(e)
            }
        )
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
# POST /api/reject
# PENDING → REJECTED

@app.post("/api/reject")
def reject_access(
    request: RejectionRequest
):

    conn = get_db_connection()

    if not conn:

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database connection failed"
            }
        )

    cursor = conn.cursor(
        dictionary=True,
        buffered=True
    )

    try:
        # FIND REQUEST
        select_query = """
        SELECT
            request_id,
            user_id,
            resource_id,
            approval_token,
            status
        FROM access_requests_1
        WHERE approval_token = %s
        """
        cursor.execute(
            select_query,
            (request.approval_token,)
        )

        access_request = cursor.fetchone()

        if not access_request:

            raise HTTPException(
                status_code=404,
                detail={
                    "error": (
                        "Approval request not found"
                    ),
                    "approval_token": (
                        request.approval_token
                    )
                }
            )

        # CHECK STATUS
        if access_request["status"] != "PENDING":

            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Request is not pending",
                    "current_status": (
                        access_request["status"]
                    ),
                    "approval_token": (
                        request.approval_token
                    )
                }
            )

        # REJECT
        update_query = """
        UPDATE access_requests_1
        SET status = 'REJECTED'
        WHERE approval_token = %s
          AND status = 'PENDING'
        """

        cursor.execute(
            update_query,
            (request.approval_token,)
        )

        conn.commit()

        return {

            "status": "REJECTED",

            "message": (
                "Access request rejected successfully."
            ),

            "request_id": (
                access_request["request_id"]
            ),

            "user_id": (
                access_request["user_id"]
            ),

            "resource_id": (
                access_request["resource_id"]
            ),

            "approval_token": (
                access_request["approval_token"]
            )
        }

    except HTTPException:
        raise

    except Exception as e:

        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Rejection processing failed",
                "message": str(e)
            }
        )

    finally:
        try:
            cursor.close()
        except Exception:
            pass

        try:
            conn.close()
        except Exception:
            pass
