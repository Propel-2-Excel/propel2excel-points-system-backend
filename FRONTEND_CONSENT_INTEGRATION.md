# Frontend Integration: Media Consent & Onboarding

## Overview

The backend now supports media consent preferences and onboarding completion tracking for the Propel2Excel (P2E) points system. This document outlines what the frontend needs to implement to provide a complete user experience.

## Backend API Endpoints Available

### 1. Update Media Consent
**Endpoint:** `POST /api/users/consent/`

**Purpose:** Update user's media consent decision

**Request Body:**
```json
{
    "media_consent": true  // or false
}
```

**Response:**
```json
{
    "success": true,
    "message": "Consent status updated successfully",
    "data": {
        "media_consent": true,
        "media_consent_date": "2024-01-15T10:30:00Z",
        "onboarding_step": "consent_completed"
    }
}
```

### 2. Complete Onboarding
**Endpoint:** `POST /api/users/complete_onboarding/`

**Purpose:** Mark user's onboarding flow as complete

**Request Body:** None (uses authenticated user)

**Response:**
```json
{
    "success": true,
    "message": "Onboarding marked as complete",
    "data": {
        "onboarding_completed": true,
        "completion_date": "2024-01-15T10:40:00Z"
    }
}
```

### 3. Get User Profile (Updated)
**Endpoint:** `GET /api/users/profile/`

**Response now includes:**
```json
{
    "id": 1,
    "username": "student123",
    "email": "student@university.edu",
    // ... existing fields ...
    
    // New consent fields
    "media_consent": true,
    "media_consent_date": "2024-01-15T10:30:00Z",
    "onboarding_completed": true,
    "onboarding_completed_date": "2024-01-15T10:40:00Z"
}
```

## Frontend Implementation Requirements

### 1. Onboarding Flow Components

#### Media Consent Component
**Purpose:** Explain P2E media usage and collect consent

**Requirements:**
- [ ] Clear explanation of what media consent means
- [ ] Examples of how student content might be used (marketing materials, social media, website)
- [ ] Prominent opt-in/opt-out buttons or toggle
- [ ] Legal compliance text (optional but recommended)
- [ ] Call the consent API endpoint when user makes decision


#### Onboarding Progress Tracker
**Requirements:**
- [ ] Track which onboarding steps are complete
- [ ] Show progress indicator (e.g., "Step 3 of 5")
- [ ] Call completion endpoint when all steps done
- [ ] Handle users who skip or come back later

### 2. Profile/Settings Integration

#### Consent Management Section
**Purpose:** Allow users to view and change their consent preference

**Requirements:**
- [ ] Display current consent status
- [ ] Show when consent was last updated
- [ ] Toggle to change consent preference
- [ ] Confirmation dialog for consent changes
- [ ] Success/error messaging

**Example Settings UI:**
```
Settings > Privacy Preferences

Media Consent
├─ Current Status: ✅ Opted In
├─ Last Updated: January 15, 2024
├─ [ Toggle Switch ]
└─ "You can change this preference anytime"
```

### 3. API Integration Code Examples

#### JavaScript/TypeScript Implementation

```javascript
// API service functions
const consentAPI = {
  // Update media consent
  async updateConsent(mediaConsent) {
    const response = await fetch('/api/users/consent/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAccessToken()}`
      },
      body: JSON.stringify({ media_consent: mediaConsent })
    });
    return response.json();
  },

  // Complete onboarding
  async completeOnboarding() {
    const response = await fetch('/api/users/complete_onboarding/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getAccessToken()}`
      }
    });
    return response.json();
  },

  // Get user profile (existing endpoint, now with consent fields)
  async getUserProfile() {
    const response = await fetch('/api/users/profile/', {
      headers: {
        'Authorization': `Bearer ${getAccessToken()}`
      }
    });
    return response.json();
  }
};

// Usage examples
async function handleConsentDecision(userConsent) {
  try {
    const result = await consentAPI.updateConsent(userConsent);
    if (result.success) {
      console.log('Consent updated successfully');
      // Move to next onboarding step or update UI
    }
  } catch (error) {
    console.error('Failed to update consent:', error);
    // Show error message to user
  }
}

async function finishOnboarding() {
  try {
    const result = await consentAPI.completeOnboarding();
    if (result.success) {
      console.log('Onboarding completed');
      // Redirect to dashboard or main app
    }
  } catch (error) {
    console.error('Failed to complete onboarding:', error);
  }
}
```

### 4. State Management

#### User Profile State
**Requirements:**
- [ ] Add consent fields to user state/context
- [ ] Update state when consent changes
- [ ] Persist onboarding completion status

**Example State Structure:**
```javascript
const userState = {
  // ... existing user fields ...
  mediaConsent: null,           // null, true, or false
  mediaConsentDate: null,       // ISO date string
  onboardingCompleted: false,   // boolean
  onboardingCompletedDate: null // ISO date string
};
```

### 5. User Experience Flows

#### New User Onboarding
1. **User registers** → Normal registration flow
2. **Show welcome/intro** → Existing onboarding steps
3. **Media consent step** → NEW: Show consent component
4. **Additional steps** → Any other onboarding steps
5. **Complete onboarding** → Call completion endpoint
6. **Redirect to app** → Normal app flow

#### Existing User Consent Management
1. **User goes to settings** → Show current consent status
2. **User changes preference** → Show confirmation dialog
3. **User confirms** → Call consent API
4. **Update UI** → Show success message and new status

#### First-time consent handling
- **If `media_consent` is `null`** → User hasn't decided yet
- **If `media_consent` is `true`** → User has opted in
- **If `media_consent` is `false`** → User has opted out

### 6. Error Handling

**Required error scenarios:**
- [ ] Network errors when calling consent API
- [ ] Authentication errors (expired tokens)
- [ ] Server errors (500 responses)
- [ ] Validation errors (missing required fields)

**Example Error Handling:**
```javascript
async function handleConsentUpdate(consent) {
  try {
    const result = await consentAPI.updateConsent(consent);
    if (result.success) {
      showSuccessMessage('Consent preference updated');
    } else {
      showErrorMessage(result.error || 'Failed to update consent');
    }
  } catch (error) {
    if (error.status === 401) {
      // Redirect to login
      redirectToLogin();
    } else {
      showErrorMessage('Something went wrong. Please try again.');
    }
  }
}
```


### 8. Testing Requirements

#### Unit Tests
- [ ] Test consent API integration functions
- [ ] Test state updates when consent changes
- [ ] Test error handling scenarios

#### Integration Tests
- [ ] Test complete onboarding flow
- [ ] Test consent preference changes
- [ ] Test UI updates after API calls

#### User Acceptance Tests
- [ ] New user can complete onboarding with consent decision
- [ ] Existing user can change consent preference in settings
- [ ] Consent status displays correctly throughout app
- [ ] Error messages are helpful and actionable

## Design Considerations

### Privacy & Legal
- **Clear language** about what consent means
- **Easy withdrawal** - users should be able to change their mind
- **No dark patterns** - don't trick users into consenting
- **Persistent access** - consent settings should be easy to find


## Implementation Priority

### Phase 1 (MVP)
1. Basic consent component in onboarding
2. API integration for consent and completion
3. Profile display of consent status

### Phase 2 (Enhanced)
1. Settings page for consent management
2. Enhanced onboarding progress tracking
3. Comprehensive error handling

### Phase 3 (Polish)
1. Advanced UI animations and transitions
2. Detailed accessibility improvements
3. Analytics for consent conversion rates

## Questions for Frontend Team

1. **Onboarding Flow**: Where in the current onboarding flow should consent be collected?
2. **UI Framework**: What component library/design system should be used for consent UI?
3. **State Management**: How is user profile state currently managed (Redux, Context, etc.)?
4. **Routing**: Should consent be a separate route or modal in existing onboarding?
5. **Error Handling**: What's the current pattern for API error handling and user messaging?
6. **Testing**: What testing framework is being used for component and integration tests?

## Support & Resources

- **Backend API**: All endpoints are implemented and tested
- **Database**: Migrations have been applied to production
- **Admin Interface**: Consent data is visible in Django admin for support
- **Documentation**: This document and the original specification in `BACKEND_INTEGRATION_CONSENT.md`

For technical questions about the backend implementation or API endpoints, contact the backend development team.
