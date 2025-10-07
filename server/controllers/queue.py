from flask import (
    current_app as app,
    url_for,
    redirect,
    session,
    request,
    send_file,
    jsonify,
)
from server import db
from authlib.integrations.flask_client import OAuth
from apiflask import APIBlueprint, abort
from server.models import User, Ticket
from server.controllers.auth import auth_required_decorator
from server.hackpsu_api import get_user_info

queue = APIBlueprint("queue", __name__, url_prefix="/queue")


@queue.route("/get")
@auth_required_decorator(roles=["hacker", "mentor", "admin"])
def get():
    tickets = []
    for ticket in Ticket.query.all():
        if ticket.status != "awaiting_feedback":
            tickets.append(dict(ticket.map()))
    return jsonify(tickets)


@queue.route("/claim", methods=["POST"])
@auth_required_decorator(roles=["mentor", "admin"])
def claim():
    user = User.query.filter_by(id=session["user_id"]).first()

    data = request.get_json()
    ticket_id = int(data["id"])

    ticket = Ticket.query.get(ticket_id)
    if ticket.claimant_id is not None:
        return abort(400, "Ticket already claimed")

    ticket.status = "claimed"
    ticket.claimant = user
    ticket.active = False
    user.claimed = ticket
    ticket.claimedAt = db.func.now()

    db.session.commit()
    return {"message": "Ticket claimed!"}


@queue.route("/unclaim", methods=["POST"])
@auth_required_decorator(roles=["mentor", "admin"])
def unclaim():
    user = User.query.filter_by(id=session["user_id"]).first()

    data = request.get_json()
    ticket_id = int(data["id"])

    ticket = Ticket.query.get(ticket_id)
    if ticket.claimant_id is None:
        return abort(400, "Ticket is not claimed")

    ticket.active = True
    ticket.claimant = None
    ticket.claimant_id = None
    ticket.status = None
    user.claimed = None
    ticket.claimedAt = None

    db.session.commit()

    return {"message": "Ticket unclaimed!"}


@queue.route("/resolve", methods=["POST"])
@auth_required_decorator(roles=["mentor", "hacker", "admin"])
def resolve():
    user = User.query.filter_by(id=session["user_id"]).first()

    data = request.get_json()
    ticket_id = int(data["id"])
    ticket = Ticket.query.get(ticket_id)
    ticket.status = "awaiting_feedback"
    
    if not user.resolved_tickets:
        user.resolved_tickets = 0

    user.resolved_tickets = user.resolved_tickets + 1

    user.claimed = None
    db.session.commit()

    return {"message": "Ticket resolved! Awaiting user feedback"}


@queue.route("/claimed")
@auth_required_decorator(roles=["mentor", "admin"])
def claimed():
    user = User.query.filter_by(id=session["user_id"]).first()

    for ticket in Ticket.query.filter(Ticket.claimant_id is not None).all():
        if ticket.claimant_id == user.id and ticket.status == "claimed":
            return {"claimed": ticket.id}

    return {"claimed": None}


# Leaderboard
@queue.route("/ranking", methods=["GET"])
@auth_required_decorator(roles=["mentor", "admin"])
def ranking():
    mentors = User.query.filter_by(role="mentor")
    uids = [str(u.id) for u in mentors]

    # Get user info from HackPSU API (uses Bearer token automatically)
    info = get_user_info(uids)

    ranking = []
    for mentor in mentors:
        if mentor.ratings and len(mentor.ratings) > 0:
            mentor_rating = sum(mentor.ratings) / len(mentor.ratings)
            mentor_name = info.get(mentor.id, {}).get('name', 'Unknown Mentor')
            ranking.append(
                (
                    mentor.resolved_tickets,
                    len(mentor.ratings),
                    mentor_name,
                    mentor_rating,
                )
            )

    ranking = sorted(ranking, key=lambda x: (x[0], x[2]), reverse=True)

    rankings = []
    val = 1
    for rank in ranking:
        status = {
            "rank": val,
            "num_resolved_tickets": rank[0],
            "num_ratings": rank[1],
            "name": rank[2],
            "average_rating": rank[3],
        }
        val += 1
        rankings.append(status)

    return rankings
