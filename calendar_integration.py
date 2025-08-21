"""
Google Calendar Integration for Propel2Excel Resume Review Sessions

This module provides functionality to automatically create calendar events
when review sessions are scheduled.

Setup:
1. Enable Google Calendar API in Google Cloud Console
2. Create service account credentials
3. Download JSON key file
4. Set GOOGLE_CALENDAR_CREDENTIALS in Django settings
5. Install: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Usage:
    from calendar_integration import create_review_session_event
    
    event_id = create_review_session_event(
        student_email="student@university.edu",
        professional_email="professional@company.com",
        start_time=datetime(2024, 1, 15, 14, 0),  # 2:00 PM
        duration_minutes=30,
        meeting_title="Resume Review Session",
        meeting_description="One-on-one resume review and career advice"
    )
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

try:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logging.warning("Google Calendar API libraries not installed. Calendar integration disabled.")

logger = logging.getLogger(__name__)

class CalendarIntegration:
    """Google Calendar integration for resume review sessions"""
    
    def __init__(self, credentials_path: str = None, calendar_id: str = None):
        """
        Initialize calendar integration
        
        Args:
            credentials_path: Path to service account JSON file
            calendar_id: Google Calendar ID to create events in
        """
        self.credentials_path = credentials_path
        self.calendar_id = calendar_id or 'primary'
        self.service = None
        
        if not GOOGLE_AVAILABLE:
            logger.warning("Google Calendar API not available")
            return
            
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API"""
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            logger.error(f"Google Calendar credentials not found: {self.credentials_path}")
            return
        
        try:
            # Authenticate with service account
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            
            self.service = build('calendar', 'v3', credentials=credentials)
            logger.info("Google Calendar API authenticated successfully")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Calendar API: {e}")
            self.service = None
    
    def create_event(
        self,
        start_time: datetime,
        end_time: datetime,
        title: str,
        description: str = "",
        attendees: list = None,
        location: str = "",
        meeting_link: str = ""
    ) -> Optional[str]:
        """
        Create a calendar event
        
        Args:
            start_time: Event start time
            end_time: Event end time
            title: Event title
            description: Event description
            attendees: List of attendee email addresses
            location: Event location
            meeting_link: Video meeting link
            
        Returns:
            Event ID if successful, None otherwise
        """
        if not self.service:
            logger.warning("Google Calendar service not available")
            return None
        
        try:
            # Prepare event data
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'America/New_York',  # Adjust as needed
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/New_York',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 30},       # 30 minutes before
                    ],
                },
            }
            
            # Add attendees if provided
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            # Add location if provided
            if location:
                event['location'] = location
            
            # Add meeting link if provided
            if meeting_link:
                if 'description' in event:
                    event['description'] += f"\n\nMeeting Link: {meeting_link}"
                else:
                    event['description'] = f"Meeting Link: {meeting_link}"
                
                # Add as conference data for better integration
                event['conferenceData'] = {
                    'createRequest': {
                        'requestId': f"resume-review-{start_time.timestamp()}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }
            
            # Create the event
            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event,
                conferenceDataVersion=1 if meeting_link else 0
            ).execute()
            
            logger.info(f"Calendar event created: {event.get('id')}")
            return event.get('id')
            
        except HttpError as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating calendar event: {e}")
            return None
    
    def update_event(self, event_id: str, **kwargs) -> bool:
        """
        Update an existing calendar event
        
        Args:
            event_id: Calendar event ID
            **kwargs: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            return False
        
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields
            for key, value in kwargs.items():
                if key in ['start_time', 'end_time']:
                    time_key = 'start' if key == 'start_time' else 'end'
                    event[time_key] = {
                        'dateTime': value.isoformat(),
                        'timeZone': 'America/New_York',
                    }
                elif key == 'title':
                    event['summary'] = value
                elif key == 'attendees':
                    event['attendees'] = [{'email': email} for email in value]
                else:
                    event[key] = value
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            logger.info(f"Calendar event updated: {event_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to update calendar event {event_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating calendar event {event_id}: {e}")
            return False
    
    def delete_event(self, event_id: str) -> bool:
        """
        Delete a calendar event
        
        Args:
            event_id: Calendar event ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            return False
        
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Calendar event deleted: {event_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to delete calendar event {event_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting calendar event {event_id}: {e}")
            return False

# Global calendar integration instance
_calendar_integration = None

def get_calendar_integration() -> Optional[CalendarIntegration]:
    """Get calendar integration instance"""
    global _calendar_integration
    
    if _calendar_integration is None:
        try:
            from django.conf import settings
            credentials_path = getattr(settings, 'GOOGLE_CALENDAR_CREDENTIALS', None)
            calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary')
            
            if credentials_path:
                _calendar_integration = CalendarIntegration(credentials_path, calendar_id)
            else:
                logger.warning("GOOGLE_CALENDAR_CREDENTIALS not configured")
                
        except Exception as e:
            logger.error(f"Failed to initialize calendar integration: {e}")
    
    return _calendar_integration

def create_review_session_event(
    student_email: str,
    professional_email: str,
    start_time: datetime,
    duration_minutes: int = 30,
    meeting_title: str = "Resume Review Session",
    meeting_description: str = "",
    meeting_link: str = ""
) -> Optional[str]:
    """
    Create a calendar event for a resume review session
    
    Args:
        student_email: Student's email address
        professional_email: Professional's email address
        start_time: Session start time
        duration_minutes: Session duration in minutes
        meeting_title: Event title
        meeting_description: Event description
        meeting_link: Video meeting link
        
    Returns:
        Calendar event ID if successful, None otherwise
    """
    calendar = get_calendar_integration()
    if not calendar:
        logger.warning("Calendar integration not available")
        return None
    
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    # Prepare description
    description = meeting_description or f"""
Resume Review Session

Student: {student_email}
Professional: {professional_email}
Duration: {duration_minutes} minutes

Please join the session on time and have your resume ready for review.
For questions, contact propel@propel2excel.com
    """.strip()
    
    # Create the event
    return calendar.create_event(
        start_time=start_time,
        end_time=end_time,
        title=meeting_title,
        description=description,
        attendees=[student_email, professional_email],
        meeting_link=meeting_link
    )

def update_session_event(
    event_id: str,
    **kwargs
) -> bool:
    """
    Update a resume review session calendar event
    
    Args:
        event_id: Calendar event ID
        **kwargs: Fields to update
        
    Returns:
        True if successful, False otherwise
    """
    calendar = get_calendar_integration()
    if not calendar:
        return False
    
    return calendar.update_event(event_id, **kwargs)

def cancel_session_event(event_id: str) -> bool:
    """
    Cancel (delete) a resume review session calendar event
    
    Args:
        event_id: Calendar event ID
        
    Returns:
        True if successful, False otherwise
    """
    calendar = get_calendar_integration()
    if not calendar:
        return False
    
    return calendar.delete_event(event_id)

# Example usage and testing functions
def test_calendar_integration():
    """Test function for calendar integration"""
    from datetime import datetime, timedelta
    
    # Test event creation
    test_start_time = datetime.now() + timedelta(days=1)
    event_id = create_review_session_event(
        student_email="test.student@university.edu",
        professional_email="test.professional@company.com",
        start_time=test_start_time,
        duration_minutes=30,
        meeting_title="Test Resume Review Session",
        meeting_description="This is a test event for calendar integration"
    )
    
    if event_id:
        print(f"✅ Test event created successfully: {event_id}")
        
        # Test event update
        success = update_session_event(
            event_id,
            title="Updated Test Resume Review Session",
            description="This event has been updated"
        )
        
        if success:
            print("✅ Test event updated successfully")
        else:
            print("❌ Failed to update test event")
            
        # Clean up - delete test event
        if cancel_session_event(event_id):
            print("✅ Test event deleted successfully")
        else:
            print("❌ Failed to delete test event")
    else:
        print("❌ Failed to create test event")

if __name__ == "__main__":
    # Run test if called directly
    test_calendar_integration()
