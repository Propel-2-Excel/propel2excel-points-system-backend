/**
 * Google Apps Script to create Professional Availability Form
 * 
 * Instructions:
 * 1. Go to https://script.google.com/
 * 2. Create a new project
 * 3. Replace the code with this script
 * 4. Run the createProfessionalAvailabilityForm function
 * 5. Check your Google Drive for the new form
 * 6. Set up the webhook trigger (see setupWebhook function)
 */

function createProfessionalAvailabilityForm() {
  // Create the form
  const form = FormApp.create('Professional Availability - Propel2Excel Resume Reviews');
  
  // Set form description
  form.setDescription(`
Thank you for volunteering to review student resumes! Please fill out your availability for the upcoming weeks.

Your responses will help us automatically match you with students who have compatible schedules.

Questions? Contact us at propel@propel2excel.com
  `);
  
  // Basic Information Section
  form.addSectionHeaderItem()
    .setTitle('Professional Information')
    .setHelpText('Please provide your basic information');
  
  form.addTextItem()
    .setTitle('Full Name')
    .setRequired(true);
  
  form.addTextItem()
    .setTitle('Email Address')
    .setRequired(true);
  
  form.addTextItem()
    .setTitle('Professional Title')
    .setHelpText('e.g., Senior Software Engineer, Marketing Manager')
    .setRequired(true);
  
  form.addTextItem()
    .setTitle('Company/Organization')
    .setRequired(true);
  
  form.addTextItem()
    .setTitle('Industry Specializations')
    .setHelpText('e.g., Technology, Finance, Healthcare, Consulting (separate multiple with commas)')
    .setRequired(true);
  
  // Availability Section
  form.addSectionHeaderItem()
    .setTitle('Availability Information')
    .setHelpText('Please specify when you are available for 30-minute resume review sessions');
  
  // Availability period
  form.addDateItem()
    .setTitle('Availability Start Date')
    .setHelpText('When can you start taking review sessions?')
    .setRequired(true);
  
  form.addDateItem()
    .setTitle('Availability End Date')
    .setHelpText('Until when are you available? (Typically 2-4 weeks from start date)')
    .setRequired(true);
  
  // Preferred days
  const daysItem = form.addCheckboxItem()
    .setTitle('Preferred Days of the Week')
    .setRequired(true);
  daysItem.setChoices([
    daysItem.createChoice('Monday'),
    daysItem.createChoice('Tuesday'),
    daysItem.createChoice('Wednesday'),
    daysItem.createChoice('Thursday'),
    daysItem.createChoice('Friday'),
    daysItem.createChoice('Saturday'),
    daysItem.createChoice('Sunday')
  ]);
  
  // Time preferences
  const timeSlots = form.addCheckboxItem()
    .setTitle('Preferred Time Slots (Select all that work for you)')
    .setRequired(true);
  timeSlots.setChoices([
    timeSlots.createChoice('9:00 AM - 10:00 AM'),
    timeSlots.createChoice('10:00 AM - 11:00 AM'),
    timeSlots.createChoice('11:00 AM - 12:00 PM'),
    timeSlots.createChoice('12:00 PM - 1:00 PM'),
    timeSlots.createChoice('1:00 PM - 2:00 PM'),
    timeSlots.createChoice('2:00 PM - 3:00 PM'),
    timeSlots.createChoice('3:00 PM - 4:00 PM'),
    timeSlots.createChoice('4:00 PM - 5:00 PM'),
    timeSlots.createChoice('5:00 PM - 6:00 PM'),
    timeSlots.createChoice('6:00 PM - 7:00 PM'),
    timeSlots.createChoice('7:00 PM - 8:00 PM'),
    timeSlots.createChoice('8:00 PM - 9:00 PM')
  ]);
  
  // Time zone
  const timezoneItem = form.addListItem()
    .setTitle('Your Time Zone')
    .setRequired(true);
  timezoneItem.setChoices([
    timezoneItem.createChoice('Eastern Time (ET)'),
    timezoneItem.createChoice('Central Time (CT)'),
    timezoneItem.createChoice('Mountain Time (MT)'),
    timezoneItem.createChoice('Pacific Time (PT)'),
    timezoneItem.createChoice('Hawaii Time (HT)'),
    timezoneItem.createChoice('Alaska Time (AT)'),
    timezoneItem.createChoice('UTC'),
    timezoneItem.createChoice('Other (please specify in notes)')
  ]);
  
  // Specific availability
  form.addParagraphTextItem()
    .setTitle('Specific Available Times')
    .setHelpText('Please list specific days and times you are available. Format: "Monday 2-3 PM, Wednesday 10-11 AM, Friday 1-2 PM", etc.')
    .setRequired(false);
  
  // Review preferences
  form.addSectionHeaderItem()
    .setTitle('Review Preferences')
    .setHelpText('Help us match you with the right students');
  
  const experienceLevels = form.addCheckboxItem()
    .setTitle('Experience Levels You Prefer to Review')
    .setRequired(true);
  experienceLevels.setChoices([
    experienceLevels.createChoice('Entry Level (0-2 years)'),
    experienceLevels.createChoice('Mid Level (2-5 years)'),
    experienceLevels.createChoice('Senior Level (5+ years)'),
    experienceLevels.createChoice('Career Changers'),
    experienceLevels.createChoice('Recent Graduates'),
    experienceLevels.createChoice('No preference - all levels')
  ]);
  
  const industries = form.addCheckboxItem()
    .setTitle('Industries You Can Review')
    .setRequired(true);
  industries.setChoices([
    industries.createChoice('Technology/Software'),
    industries.createChoice('Finance/Banking'),
    industries.createChoice('Healthcare'),
    industries.createChoice('Consulting'),
    industries.createChoice('Marketing/Advertising'),
    industries.createChoice('Engineering'),
    industries.createChoice('Education'),
    industries.createChoice('Retail'),
    industries.createChoice('Non-Profit'),
    industries.createChoice('Government'),
    industries.createChoice('Startups'),
    industries.createChoice('Other (any industry)')
  ]);
  
  // Meeting preferences
  const meetingTypes = form.addCheckboxItem()
    .setTitle('Meeting Format Preferences')
    .setRequired(true);
  meetingTypes.setChoices([
    meetingTypes.createChoice('Video Call (Google Meet/Zoom)'),
    meetingTypes.createChoice('Phone Call'),
    meetingTypes.createChoice('Email Review Only'),
    meetingTypes.createChoice('No preference')
  ]);
  
  // Additional information
  form.addSectionHeaderItem()
    .setTitle('Additional Information');
  
  form.addParagraphTextItem()
    .setTitle('Special Notes or Requirements')
    .setHelpText('Any additional information about your availability, preferences, or special requirements?')
    .setRequired(false);
  
  form.addTextItem()
    .setTitle('Maximum Reviews Per Week')
    .setHelpText('How many resume reviews can you realistically handle per week?')
    .setRequired(false);
  
  // Confirmation
  const confirmationItem = form.addCheckboxItem()
    .setTitle('Confirmation')
    .setRequired(true);
  confirmationItem.setChoices([
    confirmationItem.createChoice('I understand that students will be matched based on my availability and I commit to responding to scheduled sessions promptly'),
    confirmationItem.createChoice('I agree to provide constructive feedback and maintain professional standards during reviews'),
    confirmationItem.createChoice('I understand I can update my availability by submitting a new form')
  ]);
  
  // Set up response destination (optional)
  const spreadsheet = SpreadsheetApp.create('Professional Availability Responses - ' + new Date().toDateString());
  form.setDestination(FormApp.DestinationType.SPREADSHEET, spreadsheet.getId());
  
  // Get the form URL
  const formUrl = form.getPublishedUrl();
  const editUrl = form.getEditUrl();
  
  console.log('✅ Professional Availability Form Created!');
  console.log('📝 Form URL (share this with professionals):', formUrl);
  console.log('✏️ Edit URL (for admins):', editUrl);
  console.log('📊 Responses Spreadsheet ID:', spreadsheet.getId());
  
  // Return URLs for easy access
  return {
    formUrl: formUrl,
    editUrl: editUrl,
    spreadsheetId: spreadsheet.getId()
  };
}

/**
 * Set up webhook to send form responses to Django backend
 * Run this AFTER creating the form and updating the URLs below
 */
function setupWebhook() {
  // ⚠️ UPDATE THESE URLs TO MATCH YOUR SETUP
  const BACKEND_WEBHOOK_URL = 'https://your-backend-url.com/api/forms/professional-availability/';
  const FORM_SECRET = 'your-webhook-secret-here'; // Match settings.FORM_WEBHOOK_SECRET
  
  // Get the form (replace with your form ID)
  const formId = 'REPLACE_WITH_YOUR_FORM_ID';
  const form = FormApp.openById(formId);
  
  // Create trigger for form submissions
  ScriptApp.newTrigger('onFormSubmit')
    .to(form)
    .onFormSubmit()
    .create();
  
  console.log('✅ Webhook trigger created for form submissions');
}

/**
 * This function is triggered when someone submits the form
 * It sends the response data to the Django backend
 */
function onFormSubmit(e) {
  try {
    // ⚠️ UPDATE THESE URLs TO MATCH YOUR SETUP
    const BACKEND_WEBHOOK_URL = 'https://your-backend-url.com/api/forms/professional-availability/';
    const FORM_SECRET = 'your-webhook-secret-here'; // Match settings.FORM_WEBHOOK_SECRET
    
    const formResponse = e.response;
    const itemResponses = formResponse.getItemResponses();
    
    // Extract response data
    const responseData = {
      form_type: 'professional_availability',
      response_id: formResponse.getId(),
      timestamp: formResponse.getTimestamp().toISOString(),
      respondent_email: formResponse.getRespondentEmail(),
      responses: {}
    };
    
    // Parse all responses
    itemResponses.forEach(itemResponse => {
      const question = itemResponse.getItem().getTitle();
      const answer = itemResponse.getResponse();
      responseData.responses[question] = answer;
    });
    
    // Parse specific fields for availability matching
    responseData.parsed_data = {
      name: responseData.responses['Full Name'] || '',
      email: responseData.responses['Email Address'] || '',
      professional_title: responseData.responses['Professional Title'] || '',
      company: responseData.responses['Company/Organization'] || '',
      specializations: responseData.responses['Industry Specializations'] || '',
      start_date: responseData.responses['Availability Start Date'] || '',
      end_date: responseData.responses['Availability End Date'] || '',
      preferred_days: responseData.responses['Preferred Days of the Week'] || [],
      time_slots: responseData.responses['Preferred Time Slots (Select all that work for you)'] || [],
      timezone: responseData.responses['Your Time Zone'] || 'UTC',
      specific_times: responseData.responses['Specific Available Times'] || '',
      experience_levels: responseData.responses['Experience Levels You Prefer to Review'] || [],
      industries: responseData.responses['Industries You Can Review'] || [],
      meeting_types: responseData.responses['Meeting Format Preferences'] || [],
      notes: responseData.responses['Special Notes or Requirements'] || '',
      max_reviews_per_week: responseData.responses['Maximum Reviews Per Week'] || ''
    };
    
    // Send to backend
    const payload = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Form-Secret': FORM_SECRET
      },
      payload: JSON.stringify(responseData)
    };
    
    const response = UrlFetchApp.fetch(BACKEND_WEBHOOK_URL, payload);
    
    if (response.getResponseCode() === 200) {
      console.log('✅ Successfully sent form response to backend');
    } else {
      console.error('❌ Failed to send to backend:', response.getContentText());
    }
    
  } catch (error) {
    console.error('❌ Error in onFormSubmit:', error);
  }
}

/**
 * Test function to verify webhook is working
 */
function testWebhook() {
  const testData = {
    form_type: 'professional_availability',
    response_id: 'test_response_123',
    timestamp: new Date().toISOString(),
    respondent_email: 'test@example.com',
    responses: {
      'Full Name': 'John Doe',
      'Email Address': 'john@example.com',
      'Professional Title': 'Senior Software Engineer',
      'Industry Specializations': 'Technology, Software Development'
    }
  };
  
  // Send test request
  const BACKEND_WEBHOOK_URL = 'https://your-backend-url.com/api/forms/professional-availability/';
  const FORM_SECRET = 'your-webhook-secret-here';
  
  const payload = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Form-Secret': FORM_SECRET
    },
    payload: JSON.stringify(testData)
  };
  
  try {
    const response = UrlFetchApp.fetch(BACKEND_WEBHOOK_URL, payload);
    console.log('Test response:', response.getContentText());
  } catch (error) {
    console.error('Test error:', error);
  }
}
