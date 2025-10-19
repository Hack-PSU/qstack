"""
Gotify notification service for QStack
Sends push notifications when new tickets are submitted
"""
import requests
from os import environ as env
from flask import current_app as app


def send_ticket_notification(ticket_data):
    """
    Send a push notification via Gotify when a new ticket is submitted

    Args:
        ticket_data: Dictionary containing ticket information (question, tags, location, etc.)

    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    gotify_token = env.get("GOTIFY_TOKEN")
    gotify_url = env.get("GOTIFY_URL", "https://notify.hackpsu.org")

    if not gotify_token:
        app.logger.warning("GOTIFY_TOKEN not configured, skipping notification")
        return False

    try:
        # Prepare notification message
        title = f"New Help Request: {ticket_data.get('question', 'Untitled')}"

        # Format tags for display
        tags = ticket_data.get('tags', [])
        tags_str = ", ".join(tags) if tags else "No tags"

        # Build message body
        message = f"""
Location: {ticket_data.get('location', 'Not specified')}
Tags: {tags_str}

{ticket_data.get('content', '')[:200]}{'...' if len(ticket_data.get('content', '')) > 200 else ''}
        """.strip()

        # Send notification to Gotify
        response = requests.post(
            f"{gotify_url}/message",
            json={
                "title": title,
                "message": message,
                "priority": 5  # Default priority for new tickets
            },
            params={"token": gotify_token},
            timeout=5  # 5 second timeout to avoid blocking
        )

        response.raise_for_status()
        app.logger.info(f"Notification sent successfully for ticket: {ticket_data.get('question')}")
        return True

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Failed to send Gotify notification: {str(e)}")
        return False
    except Exception as e:
        app.logger.error(f"Unexpected error sending notification: {str(e)}")
        return False
