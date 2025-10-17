# from concurrent.futures import thread
from flask import current_app as app, url_for, redirect, session
from server import db
from authlib.integrations.flask_client import OAuth
from apiflask import APIBlueprint, abort
from os import environ as env
from urllib.parse import quote_plus, urlencode
import csv
from server.controllers.auth import auth_required_decorator
from server.models import User, Ticket
from server.hackpsu_api import get_user_info

admin = APIBlueprint("admin", __name__, url_prefix="/admin")


@admin.route("/ticketdata")
@auth_required_decorator(roles=["admin"])
def getTicketData():
    mentors = User.query.filter_by(role="mentor").all()
    totalTickets = 0
    sumAverageMentorRating = 0
    totalMentors = 0
    avgTime = 0
    totalTickets = 0

    for mentor in mentors:
        totalTickets += len(mentor.ratings)
        if len(mentor.ratings) != 0:
            sumAverageMentorRating += sum(mentor.ratings) / len(mentor.ratings)
            totalMentors += 1
    
    for ticket in Ticket.query.all():
        if ticket.claimedAt is not None:
            avgTime += (ticket.claimedAt - ticket.createdAt).total_seconds()
            totalTickets += 1

    if totalMentors != 0:
        averageRating = sumAverageMentorRating/totalMentors
    else:
        averageRating = 0
    
    if totalTickets != 0:
        avgTimeToClaim = avgTime/totalTickets
    else:
        avgTimeToClaim = 0

    return {"total": totalTickets, "averageRating": averageRating, "averageTime": avgTimeToClaim}

# Admin Stats
@admin.route("/userdata")
@auth_required_decorator(roles=["admin"])
def getUserData():
    users = User.query.all()
    uids = [str(u.id) for u in users]

    # Get user info from HackPSU API (uses Bearer token automatically)
    info = get_user_info(uids)

    userData = []
    for user in users:
        # Don't use user.map() as it gets name/email from current session (admin's session)
        # Instead, build the user data manually with API data
        api_info = info.get(user.id, {})

        userMap = {
            "id": user.id,
            "name": api_info.get('name', 'Unknown User'),
            "email": api_info.get('email', 'No Email'),
            "role": user.role,
            "location": user.location,
            "zoomlink": user.zoomlink,
            "discord": user.discord,
            "phone": user.phone,
            "resolved_tickets": (
                user.resolved_tickets if user.role == "mentor" else "Not Applicable"
            ),
            "ratings": (
                sum(user.ratings) / len(user.ratings)
                if user.role == "mentor" and user.ratings and len(user.ratings) != 0
                else None
            ),
            "reviews": user.reviews if user.reviews != None else [],
        }

        userData.append(userMap)

    return userData


@admin.route("/alltickets")
@auth_required_decorator(roles=["admin"])
def getAllTickets():
    """Get all tickets with creator and mentor information"""
    tickets = Ticket.query.order_by(Ticket.createdAt.desc()).all()

    # Get all unique user IDs (creators and claimants)
    user_ids = set()
    for ticket in tickets:
        if ticket.creator_id:
            user_ids.add(str(ticket.creator_id))
        if ticket.claimant_id:
            user_ids.add(str(ticket.claimant_id))

    # Fetch user info from HackPSU API
    info = get_user_info(list(user_ids))

    ticketData = []
    for ticket in tickets:
        # Get creator info (prefer stored name/email, fallback to API)
        creator_name = ticket.creator_name if ticket.creator_name else info.get(ticket.creator_id, {}).get('name', 'Unknown User')
        creator_email = ticket.creator_email if ticket.creator_email else info.get(ticket.creator_id, {}).get('email', 'No Email')

        # Get mentor info (prefer stored name, fallback to API)
        mentor_name = None
        if ticket.claimant_id:
            mentor_name = ticket.claimant_name if ticket.claimant_name else info.get(ticket.claimant_id, {}).get('name', 'Unknown Mentor')

        ticketData.append({
            "id": ticket.id,
            "question": ticket.question,
            "creator_name": creator_name,
            "creator_email": creator_email,
            "creator_discord": ticket.creator.discord if ticket.creator else "",
            "creator_phone": ticket.creator.phone if ticket.creator else "",
            "mentor_name": mentor_name,
            "mentor_id": ticket.claimant_id,
            "status": ticket.status,
            "active": ticket.active,
            "createdAt": ticket.createdAt.isoformat() if ticket.createdAt else None,
            "claimedAt": ticket.claimedAt.isoformat() if ticket.claimedAt else None,
            "location": ticket.location,
            "tags": ticket.tags
        })

    return ticketData
