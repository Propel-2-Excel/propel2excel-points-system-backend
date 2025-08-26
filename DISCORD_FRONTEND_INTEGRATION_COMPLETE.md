# Discord Integration - Complete Frontend Implementation Guide

## 🎯 Overview

This guide provides everything needed to implement Discord username validation and secure verification in your student registration flow. The system ensures only Discord server members can register and includes security protections against account hijacking.

**Key Features:**
- ✅ **Discord Validation**: Verify server membership during registration
- ✅ **Secure Verification**: Two-factor verification prevents account hijacking
- ✅ **Auto-linking**: New users get Discord features immediately
- ✅ **Backward Compatibility**: Existing users can still link via code

## 🔒 Security Architecture

### **Two-Factor Verification Flow**
```
1. User enters Discord username → Validation API checks server membership
2. Registration stores username as "unverified" → No auto-linking for security
3. User must use !link command from their actual Discord account
4. Backend verifies Discord account matches registration username
5. Only then is Discord account linked and verified
```

### **Security Protections**
- **Identity Verification**: Only the real Discord user can complete verification
- **Anti-Hijacking**: Prevents linking someone else's Discord account
- **One-to-One Linking**: Each Discord account can only link to one website account
- **No Relinking**: Verified accounts cannot be changed

## 🔌 API Endpoints

### 1. Discord Username Validation
**URL**: `POST /api/validate-discord-user/`  
**Authentication**: None required (public endpoint)  
**Content-Type**: `application/json`

#### Request
```json
{
  "discord_username": "JaneDoe#1234"
}
```

#### Response Examples

**✅ Valid User Found**
```json
{
  "valid": true,
  "message": "User found in Propel2Excel Server",
  "discord_username": "JaneDoe#1234",
  "discord_id": "123456789012345678",
  "display_name": "Jane Doe",
  "username": "JaneDoe#1234"
}
```

**❌ User Not Found**
```json
{
  "valid": false,
  "message": "User 'JaneDoe#1234' not found in Propel2Excel Server",
  "discord_username": "JaneDoe#1234",
  "discord_id": null
}
```

**⚠️ Validation Error**
```json
{
  "discord_username": [
    "This field is required."
  ]
}
```

### 2. User Registration (Enhanced)
**URL**: `POST /api/users/register/`  
**Authentication**: None required  
**Content-Type**: `application/json`

#### Request
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "university": "Stanford University",
  "role": "student",
  "password": "securepassword123",
  "discord_data": {
    "discord_username": "JaneDoe#1234"
  }
}
```

#### Response
```json
{
  "message": "Account created successfully! Discord verification required.",
  "user": {
    "id": 123,
    "username": "johndoe",
    "email": "john@example.com",
    "discord_verified": false,
    "discord_username_unverified": "JaneDoe#1234"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  },
  "discord_verification_required": true,
  "discord_username_pending": "JaneDoe#1234"
}
```

## 🎨 Complete Implementation Example

```javascript
class SecureDiscordRegistration {
  constructor() {
    this.isValidating = false;
    this.isRegistering = false;
    this.validationResult = null;
    this.currentUser = null;
  }

  // Step 1: Discord Username Validation
  async validateDiscordUsername(discordUsername) {
    this.showLoadingState('validating');
    this.clearMessages();

    try {
      const response = await fetch('/api/validate-discord-user/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          discord_username: discordUsername.trim()
        })
      });

      const data = await response.json();

      if (!response.ok) {
        this.showError('Connection error. Please try again.');
        return false;
      }

      // Handle validation errors
      if (data.discord_username) {
        this.showValidationErrors(data.discord_username);
        return false;
      }

      // Handle Discord validation result
      if (data.valid) {
        this.showSuccess(`✅ Discord account verified! Welcome ${data.display_name}`);
        this.validationResult = data;
        this.enableRegistrationForm();
        return true;
      } else {
        this.showError(`❌ ${data.message}`);
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

  // Step 2: Secure Registration
  async registerUser(formData) {
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
        
        // Discord data (stored as unverified for security)
        discord_data: {
          discord_username: this.validationResult.username
        }
      };

      const response = await fetch('/api/users/register/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(registrationData)
      });

      const data = await response.json();

      if (!response.ok) {
        this.showRegistrationErrors(data);
        return false;
      }

      // Store authentication tokens
      this.storeAuthTokens(data.tokens);
      this.currentUser = data.user;

      // Handle Discord verification requirement
      if (data.discord_verification_required) {
        this.showDiscordVerificationPrompt(data.discord_username_pending);
      } else {
        this.redirectToDashboard();
      }

      return true;

    } catch (error) {
      this.showError('Registration failed. Please try again.');
      return false;
    } finally {
      this.hideLoadingState();
    }
  }

  // Step 3: Discord Verification Prompt
  showDiscordVerificationPrompt(discordUsername) {
    const modal = `
      <div class="discord-verification-modal">
        <div class="modal-content">
          <h2>🔒 Verify Your Discord Account</h2>
          
          <div class="verification-info">
            <p><strong>Account created successfully!</strong></p>
            <p>To enable Discord features and bot commands, you need to verify your Discord account.</p>
          </div>

          <div class="verification-steps">
            <h3>Verification Steps:</h3>
            <ol>
              <li>Go to your <strong>Profile page</strong></li>
              <li>Click <strong>"Link Discord Account"</strong> to get a 6-digit code</li>
              <li>In Discord, type: <code>!link [your-code]</code></li>
              <li>Make sure you're using: <strong>${discordUsername}</strong></li>
            </ol>
          </div>

          <div class="security-notice">
            <h4>🔐 Security Notice</h4>
            <p>This verification ensures you actually own the Discord account. 
            Only the real <strong>${discordUsername}</strong> can complete this verification.</p>
          </div>

          <div class="action-buttons">
            <button onclick="this.goToProfile()" class="btn btn-primary">
              Go to Profile
            </button>
            <button onclick="this.skipVerification()" class="btn btn-secondary">
              Skip for Now
            </button>
          </div>
        </div>
      </div>
    `;

    this.showModal(modal);
  }

  // Helper Methods
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

  showLoadingState(type) {
    const button = document.querySelector(`[data-loading="${type}"]`);
    if (button) {
      button.disabled = true;
      button.innerHTML = '<span class="spinner"></span> Loading...';
    }
  }

  hideLoadingState() {
    const buttons = document.querySelectorAll('[data-loading]');
    buttons.forEach(button => {
      button.disabled = false;
      button.innerHTML = button.getAttribute('data-original-text') || 'Submit';
    });
  }

  showSuccess(message) {
    this.showMessage(`<div class="alert alert-success">${message}</div>`);
  }

  showError(message) {
    this.showMessage(`<div class="alert alert-error">${message}</div>`);
  }

  showMessage(content) {
    const messageArea = document.getElementById('message-area');
    if (messageArea) {
      messageArea.innerHTML = content;
      messageArea.scrollIntoView({ behavior: 'smooth' });
    }
  }

  clearMessages() {
    const messageArea = document.getElementById('message-area');
    if (messageArea) {
      messageArea.innerHTML = '';
    }
  }

  enableRegistrationForm() {
    const form = document.getElementById('registration-form');
    if (form) {
      form.style.display = 'block';
      form.scrollIntoView({ behavior: 'smooth' });
    }
  }

  storeAuthTokens(tokens) {
    localStorage.setItem('access_token', tokens.access);
    localStorage.setItem('refresh_token', tokens.refresh);
  }

  goToProfile() {
    window.location.href = '/profile';
  }

  skipVerification() {
    this.hideModal();
    this.redirectToDashboard();
  }

  redirectToDashboard() {
    window.location.href = '/dashboard';
  }

  showModal(content) {
    // Implementation depends on your modal system
    // Example with a simple modal:
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = content;
    document.body.appendChild(modal);
  }

  hideModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) {
      modal.remove();
    }
  }
}
```

## 🎨 UI/UX Implementation

### Registration Page Structure

```html
<div class="registration-container">
  <!-- Step 1: Discord Validation -->
  <div class="discord-validation-step">
    <h2>Verify Your Discord Account</h2>
    <p>Enter your Discord username to verify server membership</p>
    
    <div class="form-group">
      <label for="discord_username">Discord Username</label>
      <input 
        type="text" 
        id="discord_username"
        name="discord_username"
        placeholder="JaneDoe#1234"
        maxlength="50"
        required
      />
      <small class="help-text">
        Include your discriminator (e.g., #1234) for faster verification
      </small>
    </div>
    
    <button 
      type="button" 
      onclick="registration.validateDiscordUsername(document.getElementById('discord_username').value)"
      class="btn btn-primary"
      data-loading="validating"
      data-original-text="Verify Discord Account"
    >
      Verify Discord Account
    </button>
    
    <div id="message-area" class="message-area"></div>
  </div>

  <!-- Step 2: Registration Form (Hidden until Discord verified) -->
  <div id="registration-form" class="registration-form" style="display: none;">
    <h2>Complete Your Registration</h2>
    
    <form onsubmit="registration.registerUser(this); return false;">
      <div class="form-group">
        <label for="username">Username</label>
        <input type="text" id="username" name="username" required />
      </div>
      
      <div class="form-group">
        <label for="email">Email</label>
        <input type="email" id="email" name="email" required />
      </div>
      
      <div class="form-row">
        <div class="form-group">
          <label for="first_name">First Name</label>
          <input type="text" id="first_name" name="first_name" required />
        </div>
        <div class="form-group">
          <label for="last_name">Last Name</label>
          <input type="text" id="last_name" name="last_name" required />
        </div>
      </div>
      
      <div class="form-group">
        <label for="university">University</label>
        <input type="text" id="university" name="university" required />
      </div>
      
      <div class="form-group">
        <label for="password">Password</label>
        <input type="password" id="password" name="password" required />
      </div>
      
      <button 
        type="submit" 
        class="btn btn-success"
        data-loading="registering"
        data-original-text="Create Account"
      >
        Create Account
      </button>
    </form>
  </div>
</div>
```

### CSS Styling

```css
/* Loading States */
.loading-state {
  opacity: 0.6;
  pointer-events: none;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Message Areas */
.message-area {
  margin-top: 1rem;
  min-height: 20px;
}

.alert {
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.alert-success {
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
}

.alert-error {
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}

/* Discord Join Prompt */
.discord-join-prompt {
  text-align: center;
  padding: 2rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.btn-discord {
  background: #7289da;
  color: white;
  padding: 12px 24px;
  border-radius: 6px;
  text-decoration: none;
  display: inline-block;
  margin: 1rem 0;
}

.btn-discord:hover {
  background: #5b6eae;
  color: white;
}

/* Verification Modal */
.discord-verification-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.verification-steps ol {
  margin: 1rem 0;
  padding-left: 1.5rem;
}

.verification-steps li {
  margin-bottom: 0.5rem;
}

.security-notice {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  padding: 1rem;
  border-radius: 6px;
  margin: 1rem 0;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #545b62;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover {
  background: #1e7e34;
}

/* Form Styling */
.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.help-text {
  font-size: 12px;
  color: #6c757d;
  margin-top: 0.25rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .action-buttons {
    flex-direction: column;
  }
}
```

## 🧪 Testing Checklist

### **Discord Validation Testing**
- [ ] Valid Discord usernames (with #discriminator)
- [ ] Valid Discord usernames (without discriminator)
- [ ] Invalid Discord usernames
- [ ] Empty/missing input
- [ ] Very long usernames (>50 chars)
- [ ] Special characters in usernames
- [ ] Network timeout scenarios
- [ ] Server error responses

### **Registration Flow Testing**
- [ ] Account creation with Discord validation
- [ ] Discord verification prompt shows correctly
- [ ] Registration completes without auto-linking Discord
- [ ] Verification flow redirects to profile
- [ ] Skip verification option works
- [ ] Authentication tokens are stored correctly

### **Security Testing**
- [ ] Identity verification (correct Discord user uses !link)
- [ ] Identity mismatch (wrong Discord user tries !link)
- [ ] Prevent relinking verified accounts
- [ ] Prevent double-linking same Discord to multiple accounts
- [ ] Input sanitization prevents XSS
- [ ] CSRF protection works

### **User Experience Testing**
- [ ] Loading states display correctly
- [ ] Error messages are clear and helpful
- [ ] Success messages guide next steps
- [ ] Mobile responsiveness
- [ ] Accessibility compliance (ARIA labels, keyboard navigation)
- [ ] Form validation prevents invalid submissions

## 🔧 Environment Configuration

```javascript
// API Configuration
const API_CONFIG = {
  development: {
    baseUrl: 'http://localhost:8000',
    discordValidationUrl: 'http://localhost:8000/api/validate-discord-user/',
    registrationUrl: 'http://localhost:8000/api/users/register/'
  },
  staging: {
    baseUrl: 'https://staging-api.propel2excel.com',
    discordValidationUrl: 'https://staging-api.propel2excel.com/api/validate-discord-user/',
    registrationUrl: 'https://staging-api.propel2excel.com/api/users/register/'
  },
  production: {
    baseUrl: 'https://api.propel2excel.com',
    discordValidationUrl: 'https://api.propel2excel.com/api/validate-discord-user/',
    registrationUrl: 'https://api.propel2excel.com/api/users/register/'
  }
};

const currentEnv = process.env.NODE_ENV || 'development';
const config = API_CONFIG[currentEnv];
```

## 📊 Analytics Integration

```javascript
// Track Discord validation events
function trackDiscordValidation(discordUsername, result) {
  analytics.track('Discord Validation', {
    username_length: discordUsername.length,
    has_discriminator: discordUsername.includes('#'),
    success: result.valid,
    error_type: result.valid ? null : 'user_not_found',
    timestamp: new Date().toISOString()
  });
}

// Track registration completion
function trackRegistration(hasDiscordVerification) {
  analytics.track('Registration Completed', {
    has_discord_verification: hasDiscordVerification,
    timestamp: new Date().toISOString()
  });
}

// Track verification completion
function trackVerificationCompletion() {
  analytics.track('Discord Verification Completed', {
    timestamp: new Date().toISOString()
  });
}
```

## 🚀 Performance Optimization

### **Debouncing Validation**
```javascript
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Use debounced validation for better UX
const debouncedValidation = debounce((username) => {
  registration.validateDiscordUsername(username);
}, 500);
```

### **Caching Positive Results**
```javascript
// Optional: Cache successful validations for 5 minutes
const validationCache = new Map();

function getCachedValidation(username) {
  const cached = validationCache.get(username);
  if (cached && Date.now() - cached.timestamp < 300000) {
    return cached.result;
  }
  return null;
}

function cacheValidation(username, result) {
  validationCache.set(username, {
    result,
    timestamp: Date.now()
  });
}
```

## 📞 Support & Troubleshooting

### **Common Issues & Solutions**

| Issue | Cause | Solution |
|-------|-------|----------|
| "Connection timeout" | Backend/bot services down | Check if Django server and bot are running |
| "User not found" | User not in Discord server | User needs to join server first |
| "Field required" | Empty input | Add frontend validation before API call |
| "Validation unavailable" | Bot HTTP server down | Restart bot service |
| "CSRF token missing" | Missing CSRF protection | Include CSRF token in requests |

### **Debug Information**
When reporting issues, include:
- Discord username attempted
- API response received
- Browser/device information
- Timestamp of validation attempt
- Network tab information (status codes, response times)

### **Error Handling Best Practices**
```javascript
// Comprehensive error handling
async function handleApiCall(url, data) {
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Include CSRF token if required
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      if (response.status === 500) {
        throw new Error('Server error. Please try again later.');
      } else if (response.status === 400) {
        const errorData = await response.json();
        throw new Error(JSON.stringify(errorData));
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    }

    return await response.json();
  } catch (error) {
    console.error('API call failed:', error);
    throw error;
  }
}
```

## 🎯 Success Metrics

Track these metrics to measure implementation success:

1. **Validation Success Rate**: % of Discord validations that succeed
2. **Registration Completion Rate**: % who complete registration after Discord validation
3. **Verification Completion Rate**: % who complete Discord verification after registration
4. **Bot Usage Rate**: % of new users who use bot commands (should be ~100% for verified users)
5. **Error Distribution**: Most common validation failures (guide Discord server invites)

## ✅ **Ready to Implement!**

This guide provides everything needed to implement the secure Discord integration. The backend is production-ready and all security features are implemented. 

**Key Points:**
- ✅ **Backend**: Fully implemented and tested
- ✅ **Security**: Two-factor verification prevents hijacking
- ✅ **UX**: Single-page flow with clear guidance
- ✅ **Compatibility**: Works with existing users

**Next Steps:**
1. Implement the registration form with Discord validation
2. Add the verification prompt after successful registration
3. Test with real Discord usernames from your server
4. Deploy and monitor success rates

**Questions?** Refer to the backend team for API-specific issues or security concerns.
