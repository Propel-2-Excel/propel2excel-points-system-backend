# Frontend Integration Guide: Discord Username Validation

## 🎯 Overview

This guide shows how to integrate Discord username validation into your student registration flow. The validation ensures only Discord server members can register on the platform.

**Important**: We validate against Discord **username** (unique), not display name (can be duplicate).

## 🔌 API Endpoint

**URL**: `POST /api/validate-discord-user/`  
**Authentication**: None required (public endpoint)  
**Content-Type**: `application/json`

## 📋 Integration Steps

### Step 1: Basic API Call

```javascript
async function validateDiscordUsername(discordUsername) {
  try {
    const response = await fetch('/api/validate-discord-user/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        discord_username: discordUsername
      })
    });

    const data = await response.json();
    return { success: response.ok, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}
```

### Step 2: Handle Response Types

The API returns different response formats based on the validation result:

#### ✅ Valid User Found
```javascript
{
  "valid": true,
  "message": "User found in Propel2Excel Server",
  "discord_username": "JaneDoe#1234",
  "discord_id": "123456789012345678",
  "display_name": "Jane Doe", 
  "username": "JaneDoe#1234"
}
```

#### ❌ User Not Found
```javascript
{
  "valid": false,
  "message": "User 'JaneDoe#1234' not found in Propel2Excel Server",
  "discord_username": "JaneDoe#1234",
  "discord_id": null
}
```

#### ⚠️ Input Validation Errors
```javascript
{
  "discord_username": [
    "This field is required."
  ]
}
// OR
{
  "discord_username": [
    "Ensure this field has no more than 50 characters."
  ]
}
```

### Step 3: Complete Integration Example

```javascript
// Complete registration flow with Discord validation
class DiscordRegistrationFlow {
  constructor() {
    this.isValidating = false;
    this.validationResult = null;
    this.isRegistering = false;
  }

  // Step 1: Discord Validation
  async handleDiscordValidation(discordUsername) {
    this.showLoadingState('validating');
    
    try {
      const result = await this.validateDiscordUsername(discordUsername.trim());
      
      if (!result.success) {
        this.showError('Connection error. Please try again.');
        return false;
      }

      // Check for input validation errors
      if (result.data.discord_username) {
        this.showValidationErrors(result.data.discord_username);
        return false;
      }

      // Check Discord validation result
      if (result.data.valid) {
        this.showSuccess(`✅ Discord account verified! Welcome ${result.data.display_name}`);
        
        // Store Discord data for registration
        this.validationResult = result.data;
        
        // Enable registration form
        this.enableRegistrationForm();
        return true;
      } else {
        this.showError(`❌ ${result.data.message}`);
        
        // Show join server prompt for all validation failures
        this.showJoinServerPrompt();
        return false;
      }
      
    } catch (error) {
      this.showError('Validation failed. Please try again.');
      return false;
    } finally {
      this.hideLoadingState();
    }
  }

  // Step 2: Account Registration with Discord Data
  async handleRegistration(formData) {
    if (!this.validationResult) {
      this.showError('Please validate your Discord account first.');
      return false;
    }

    this.showLoadingState('registering');

    try {
      const registrationData = {
        // Standard registration fields
        username: formData.username,
        email: formData.email,
        first_name: formData.first_name,
        last_name: formData.last_name,
        university: formData.university,
        role: 'student',
        password: formData.password,
        
        // Include UNVERIFIED Discord data (for security - requires verification)
        discord_data: {
          discord_username: this.validationResult.username  // Store as unverified
        }
      };

      const result = await this.createAccount(registrationData);

      if (result.success) {
        this.showSuccess(`🎉 ${result.data.message}`);
        
        // Store tokens
        this.storeAuthTokens(result.data.tokens);
        
        // Handle Discord verification flow
        if (result.data.discord_verification_required) {
          this.showDiscordVerificationPrompt(result.data.discord_username_pending);
        } else {
          this.redirectToDashboard();
        }
        return true;
      } else {
        this.showRegistrationErrors(result.data);
        return false;
      }

    } catch (error) {
      this.showError('Registration failed. Please try again.');
      return false;
    } finally {
      this.hideLoadingState();
    }
  }

  async validateDiscordUsername(discordUsername) {
    const response = await fetch('/api/validate-discord-user/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ discord_username: discordUsername })
    });

    return {
      success: response.ok,
      data: await response.json()
    };
  }

  async createAccount(registrationData) {
    const response = await fetch('/api/users/register/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(registrationData)
    });

    return {
      success: response.ok,
      data: await response.json()
    };
  }

  showJoinServerPrompt() {
    const message = `
      <div class="discord-join-prompt">
        <h3>Join Our Discord Server</h3>
        <p>To register, you must first join our Discord server:</p>
        <a href="https://discord.gg/your-server-invite" target="_blank" class="btn btn-discord">
          Join Discord Server
        </a>
        <p><small>After joining, come back and try validation again.</small></p>
      </div>
    `;
    this.showMessage(message);
  }

  showDiscordVerificationPrompt(discordUsername) {
    const message = `
      <div class="discord-verification-prompt">
        <h3>🔒 Verify Your Discord Account</h3>
        <p>Account created! To enable Discord features and bot commands:</p>
        
        <div class="verification-steps">
          <ol>
            <li>Go to your <strong>Profile page</strong></li>
            <li>Click <strong>"Link Discord Account"</strong> to get a 6-digit code</li>
            <li>In Discord, type: <code>!link [your-code]</code></li>
            <li>Make sure you're using: <strong>${discordUsername}</strong></li>
          </ol>
        </div>
        
        <div class="security-notice">
          <p><small>🔐 <strong>Security:</strong> This verifies you actually own the Discord account. 
          Only the real ${discordUsername} can complete this verification.</small></p>
        </div>
        
        <div class="action-buttons">
          <button onclick="this.redirectToProfile()" class="btn btn-primary">
            Go to Profile
          </button>
          <button onclick="this.skipVerification()" class="btn btn-secondary">
            Skip for Now
          </button>
        </div>
      </div>
    `;
    this.showModal(message);
  }


}
```

## 🎨 UI/UX Recommendations

### Registration Flow
1. **Discord Validation Step** (Before main form)
   ```html
   <div class="discord-validation-step">
     <h2>Verify Your Discord Account</h2>
     <p>Enter your Discord username to verify server membership</p>
     
     <div class="form-group">
       <label>Discord Username</label>
       <input 
         type="text" 
         id="discord_username"
         placeholder="JaneDoe#1234"
         maxlength="50"
         required
       />
       <small class="help-text">
         Include your discriminator (e.g., #1234)
       </small>
     </div>
     
     <button type="button" onclick="validateDiscord()" class="btn btn-primary">
       <span class="loading-spinner" style="display:none;"></span>
       Verify Discord Account
     </button>
     
     <div id="validation-message" class="message-area"></div>
   </div>
   ```

2. **Success State** → Show registration form
3. **Error State** → Show join server prompt

### Error Messages
```javascript
const ERROR_MESSAGES = {
  USER_NOT_FOUND: "Discord account not found in our server. Please join first!",
  VALIDATION_ERROR: "Please check your Discord username format.",
  CONNECTION_ERROR: "Unable to verify Discord account. Please try again.",
  SERVER_ERROR: "Validation service temporarily unavailable."
};
```

### Loading States
```css
.loading-state {
  opacity: 0.6;
  pointer-events: none;
}

.loading-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
```

## 🔒 Security Considerations

1. **Input Sanitization**: Always sanitize user input before API calls
2. **Rate Limiting**: Implement client-side rate limiting to prevent abuse
3. **CSRF Protection**: Include CSRF tokens if required by your backend
4. **Error Handling**: Don't expose internal error details to users

## 📱 Mobile Considerations

- Use appropriate input types for mobile keyboards
- Ensure validation UI works on smaller screens
- Consider auto-completion for Discord usernames
- Provide clear error messages for touch interfaces

## 🧪 Testing Checklist

### **Discord Validation**
- [ ] Valid Discord usernames (with #discriminator)
- [ ] Invalid Discord usernames 
- [ ] Empty/missing input
- [ ] Very long usernames (>50 chars)
- [ ] Special characters in usernames
- [ ] Network timeout scenarios
- [ ] Server error responses

### **Registration & Security**
- [ ] Account creation with Discord validation
- [ ] Discord verification prompt shows correctly
- [ ] Registration completes without auto-linking Discord
- [ ] Verification flow redirects to profile
- [ ] Skip verification option works

### **Security Scenarios**
- [ ] Identity verification (correct Discord user uses !link)
- [ ] Identity mismatch (wrong Discord user tries !link)
- [ ] Prevent relinking verified accounts
- [ ] Prevent double-linking same Discord to multiple accounts
- [ ] Mobile device testing
- [ ] Accessibility compliance

## 🚀 Performance Tips

1. **Debouncing**: Add 500ms debounce to validation calls
2. **Caching**: Cache positive validation results (optional)
3. **Timeouts**: Set 10-second timeout for API calls
4. **Loading States**: Always show loading indicators
5. **Progressive Enhancement**: Make form work without JavaScript as fallback

## 📊 Analytics Integration

Track validation events for insights:

```javascript
// Example analytics tracking
analytics.track('Discord Validation Started', {
  username_length: discordUsername.length,
  has_discriminator: discordUsername.includes('#')
});

analytics.track('Discord Validation Result', {
  success: result.valid,
  error_type: result.valid ? null : 'user_not_found'
});
```

## 🔧 Environment Configuration

The frontend should handle different environments:

```javascript
const API_BASE_URL = {
  development: 'http://localhost:8000',
  staging: 'https://staging-api.propel2excel.com',
  production: 'https://api.propel2excel.com'
}[process.env.NODE_ENV || 'development'];
```

## 📞 Support & Troubleshooting

### Common Issues
1. **"Connection timeout"** → Check backend/bot services are running
2. **"User not found"** → User needs to join Discord server first
3. **"Field required"** → Frontend validation needed before API call

### Debug Information
Include this info when reporting issues:
- Discord username attempted
- API response received
- Browser/device information
- Timestamp of validation attempt

---

**Ready to implement?** This validation step should be placed **before** your main registration form as per the Student Portal Design requirements.
