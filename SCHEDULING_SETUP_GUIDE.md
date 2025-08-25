# Automatic Meeting Scheduling Setup Guide

This guide will help you set up the automatic meeting scheduling feature that matches students with professionals based on overlapping availability.

## 🎯 **Overview**

The new system includes:
- Professional availability Google Form
- Automatic availability matching algorithm
- Discord bot commands for scheduling
- Calendar event creation (optional)
- Email notifications

## 📋 **Prerequisites**

1. **Google Account** with access to Google Forms and Apps Script
2. **Django Backend** running with the new models migrated
3. **Discord Bot** with admin permissions
4. **Email Service** configured (for notifications)

## 🚀 **Step 1: Set Up Professional Availability Form**

### Create the Google Form:

1. Go to https://script.google.com/
2. Create a new project
3. Copy the code from `professional_availability_form_setup.js`
4. Update the webhook URL and secret in the script:
   ```javascript
   const BACKEND_WEBHOOK_URL = 'https://your-backend-url.com/api/forms/professional-availability/';
   const FORM_SECRET = 'your-webhook-secret-here';
   ```
5. Run the `createProfessionalAvailabilityForm()` function
6. Copy the form URL from the console output

### Set Up Webhook Integration:

1. In your Django settings, add:
   ```python
   FORM_WEBHOOK_SECRET = 'your-webhook-secret-here'  # Must match Apps Script
   ```
2. Run the `setupWebhook()` function in Apps Script
3. Test with the `testWebhook()` function

## 🔧 **Step 2: Run Database Migrations**

Apply the new database models:

```bash
cd /path/to/your/project
python manage.py makemigrations
python manage.py migrate
```

## 🤖 **Step 3: Update Bot Environment**

Ensure your bot has the required environment variables:

```bash
# .env or environment variables
BACKEND_API_URL=https://your-backend-url.com
BOT_SHARED_SECRET=your-bot-secret
```

## 📧 **Step 4: Configure Email Notifications (Optional)**

Add email settings to your Django configuration:

```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # or your email provider
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'propel@propel2excel.com'
```

## 📅 **Step 5: Calendar Integration (Optional)**

### Google Calendar API Setup:

1. Go to https://console.cloud.google.com/
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create service account credentials
5. Download the JSON key file
6. Add to your Django settings:

```python
# settings.py
GOOGLE_CALENDAR_CREDENTIALS = '/path/to/service-account-key.json'
GOOGLE_CALENDAR_ID = 'your-calendar-id@group.calendar.google.com'
```

### Install Required Packages:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-dateutil
```

## 🎮 **Step 6: Test the System**

### Test Professional Form:
1. Fill out the professional availability form
2. Check Django admin for new Professional and ProfessionalAvailability records
3. Verify webhook is working in Apps Script logs

### Test Bot Commands:
1. Have a student submit a resume review request: `!resume`
2. Admin checks pending reviews: `!pending_reviews`
3. Admin finds matches: `!suggest_matches @student`
4. Admin schedules session: `!schedule_session @student "John Doe" "Monday 2:00 PM"`

## 🔄 **Step 7: Workflow Overview**

### For Students:
1. `!resume` → Gets form link
2. Submits form with availability preferences
3. Receives notification when matched
4. Attends scheduled session

### For Professionals:
1. Fills out availability form
2. System automatically matches with students
3. Receives email notification about scheduled sessions
4. Conducts review sessions

### For Admins:
1. `!pending_reviews` → See students awaiting matches
2. `!suggest_matches @student` → Find compatible professionals
3. `!schedule_session @student "Professional Name" "Time"` → Create session
4. Monitor sessions in Django admin

## 🛠️ **Available Bot Commands**

### Student Commands:
- `!resume` - Start resume review process
- `!review_status` - Check status of review request

### Admin Commands:
- `!pending_reviews` - List students with availability data
- `!suggest_matches @student` - Find professionals with overlapping times
- `!schedule_session @student "John Doe" "Monday 2:00 PM"` - Schedule session
- `!review_stats` - Show program statistics
- `!add_professional "Name" "Specialties"` - Add professional to pool
- `!list_professionals` - View available professionals

## 📊 **API Endpoints**

### New Backend Endpoints:
- `GET /api/scheduled-sessions/` - List scheduled sessions
- `POST /api/scheduled-sessions/` - Create new session
- `GET /api/professional-availability/` - List availability records
- `POST /api/forms/professional-availability/` - Webhook for form submissions

### Bot Integration Actions:
- `pending-reviews` - Get pending review requests
- `suggest-matches` - Find availability overlaps
- `schedule-session` - Create scheduled session
- `add-professional-availability` - Add availability record

## 🔍 **Matching Algorithm**

The system uses a simple but effective matching algorithm:

1. **Student submits availability** (e.g., "Monday afternoon", "Wednesday 2-3 PM")
2. **Professional submits availability** (e.g., "Monday 2-4 PM", "Wednesday afternoon")
3. **Algorithm finds overlaps** by matching:
   - Common days of the week
   - Common time periods
   - Exact time matches
4. **Results ranked by**:
   - Professional rating/experience
   - Number of overlapping time slots
   - Professional specialization match

## 🎯 **Example Workflow**

```
1. Student: !resume
   → Fills form: "Available Monday 2-3 PM, Wednesday afternoon"

2. Professional: Fills availability form
   → "Available Monday 1-4 PM, Wednesday 2-5 PM"

3. Admin: !suggest_matches @student
   → Bot shows: "John Doe - overlaps: Monday 2-3 PM, Wednesday afternoon"

4. Admin: !schedule_session @student "John Doe" "Monday 2:30 PM"
   → Session created, both parties notified

5. Session occurs, feedback collected
```

## 🔧 **Troubleshooting**

### Common Issues:

1. **Webhook not receiving data**:
   - Check FORM_WEBHOOK_SECRET matches between Django and Apps Script
   - Verify webhook URL is publicly accessible
   - Check Apps Script execution logs

2. **No matches found**:
   - Ensure professional availability records exist and are active
   - Check that availability formats are consistent
   - Verify time zone handling

3. **Bot commands failing**:
   - Check BOT_SHARED_SECRET configuration
   - Verify backend is running and accessible
   - Check bot permissions in Discord

### Debug Commands:

```bash
# Check migrations
python manage.py showmigrations

# Create test data
python manage.py shell
>>> from core.models import Professional, ProfessionalAvailability
>>> # Create test records...

# Check logs
tail -f /path/to/django/logs/django.log
```

## 📈 **Future Enhancements**

1. **Advanced Matching**:
   - Time zone conversion
   - Recurring availability
   - Professional capacity limits

2. **Calendar Integration**:
   - Automatic Google Calendar events
   - Zoom meeting links
   - Reminders and notifications

3. **Analytics**:
   - Match success rates
   - Session completion tracking
   - Professional utilization metrics

## 📞 **Support**

For questions or issues:
- Check Django admin for data consistency
- Review Apps Script execution logs
- Monitor Discord bot logs
- Contact: propel@propel2excel.com

---

*This system is designed to be robust and scalable. Start with the basic setup and gradually add advanced features as needed.*
