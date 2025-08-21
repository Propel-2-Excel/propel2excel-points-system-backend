# Developer Handoff: Resume Review System Completion

## 🎯 **Project Status**

**Backend: 95% Complete** ✅  
**Discord Bot: 50% Complete** ⚠️  
**Google Forms: 0% Integrated** ❌

The backend infrastructure is fully built and ready. You need to:
1. Complete Discord bot command integration with backend APIs
2. Set up Google Forms webhook integration
3. Test the complete workflow

---

## 📋 **Google Forms Integration Tasks**

### **Step 1: Set Up Webhook Authentication**

You'll need these values from the environment:
```
FORM_WEBHOOK_SECRET=your-secret-token-here
BACKEND_URL=https://propel2excel-backend.onrender.com
```

### **Step 2: Add Google Apps Script to Resume Form**

1. Open the Google Form: `https://forms.gle/EKHLrqhHwt1bGQjd6`
2. Click **⋮ Menu** → **Script editor**
3. Replace all code with this:

```javascript
function onFormSubmit(e) {
  const responses = e.response.getItemResponses();
  const formData = {
    timestamp: new Date().toISOString(),
    student_email: e.response.getRespondentEmail(),
    responses: {}
  };
  
  // Extract all form responses
  responses.forEach(response => {
    const question = response.getItem().getTitle();
    const answer = response.getResponse();
    formData.responses[question] = answer;
  });
  
  // Send to backend
  try {
    const response = UrlFetchApp.fetch('REPLACE_WITH_BACKEND_URL/api/form-submission/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Form-Secret': 'REPLACE_WITH_SECRET_TOKEN'
      },
      payload: JSON.stringify(formData)
    });
    
    console.log('Form data sent to backend:', response.getResponseCode());
    
    if (response.getResponseCode() !== 200) {
      console.error('Backend error:', response.getContentText());
    }
    
  } catch (error) {
    console.error('Error sending to backend:', error);
  }
}
```

### **Step 3: Set Up Form Trigger**

1. In Script editor, click **Triggers** (clock icon)
2. Click **+ Add Trigger**
3. Configure:
   - **Function**: `onFormSubmit`
   - **Event source**: `From form`
   - **Event type**: `On form submit`
4. Save and authorize the script

### **Step 4: Test Form Integration**

1. Submit a test form response
2. Check the script execution log for success/errors
3. Verify data appears in backend via `!review_stats` command

---

## 🤖 **Discord Bot Integration Tasks**

### **Critical Issue to Fix**

The Discord bot commands exist but are showing placeholder messages instead of calling the backend APIs. All backend endpoints are ready and working.

### **Commands That Need Backend Integration**

#### **1. Fix `!add_professional` Command**

**File**: `cogs/resume_review.py` (lines 113-132)

**Current**: Shows "This is stored locally" message  
**Needed**: Call backend API to actually store professional

**Replace the try block with**:
```python
@commands.command()
@commands.has_permissions(administrator=True)
async def add_professional(self, ctx, name: str, email: str, *, specialties: str):
    """Admin command to add a professional to the resume review pool"""
    try:
        # Call backend API
        payload = {
            "action": "add-professional",
            "name": name,
            "email": email,
            "specialties": specialties
        }
        
        result = await self._backend_request(payload)
        
        embed = discord.Embed(
            title="✅ Professional Added",
            description="Professional has been added to the resume review pool",
            color=0x00ff00
        )
        embed.add_field(name="Name", value=name, inline=True)
        embed.add_field(name="Email", value=email, inline=True)
        embed.add_field(name="Specialties", value=specialties, inline=False)
        embed.add_field(name="Professional ID", value=str(result.get('professional_id', 'N/A')), inline=True)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error adding professional: {e}")
```

#### **2. Fix `!list_professionals` Command**

**File**: `cogs/resume_review.py` (lines 135-158)

**Current**: Shows "Backend integration needed" message  
**Needed**: Call backend API to list actual professionals

**Replace the try block with**:
```python
@commands.command()
@commands.has_permissions(administrator=True)
async def list_professionals(self, ctx):
    """Admin command to list available professionals"""
    try:
        # Call backend API
        payload = {"action": "list-professionals"}
        result = await self._backend_request(payload)
        
        professionals = result.get('professionals', [])
        
        if not professionals:
            await ctx.send("📝 No professionals found in the system.")
            return
        
        embed = discord.Embed(
            title="👥 Available Professionals",
            description=f"Resume review professionals in our network ({len(professionals)} total)",
            color=0x0099ff
        )
        
        for prof in professionals[:10]:  # Show first 10
            rating_display = f"{prof['rating']:.1f}⭐" if prof['rating'] > 0 else "No ratings yet"
            embed.add_field(
                name=f"{prof['name']} (ID: {prof['id']})",
                value=f"**Specialties**: {prof['specialties']}\n**Reviews**: {prof['total_reviews']} | **Rating**: {rating_display}",
                inline=False
            )
        
        if len(professionals) > 10:
            embed.set_footer(text=f"Showing first 10 of {len(professionals)} professionals")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error listing professionals: {e}")
```

#### **3. Fix `!match_review` Command**

**File**: `cogs/resume_review.py` (lines 161-205)

**Current Issue**: Takes `professional_name` but backend expects `professional_id`  
**Needed**: Change parameter and call backend API

**Replace the entire command with**:
```python
@commands.command()
@commands.has_permissions(administrator=True)
async def match_review(self, ctx, user: discord.Member, professional_id: int):
    """Admin command to match a student with a professional"""
    try:
        # Call backend API
        payload = {
            "action": "match-review",
            "discord_id": str(user.id),
            "professional_id": professional_id
        }
        
        result = await self._backend_request(payload)
        
        embed = discord.Embed(
            title="🤝 Review Match Created",
            description="Student has been matched with a professional",
            color=0x00ff00
        )
        embed.add_field(name="Student", value=user.mention, inline=True)
        embed.add_field(name="Professional", value=result.get('professional', 'Unknown'), inline=True)
        embed.add_field(name="Status", value=result.get('status', 'matched'), inline=True)
        embed.add_field(
            name="Next Steps",
            value="Both parties will be contacted to coordinate the review session",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # Notify the student
        try:
            student_embed = discord.Embed(
                title="🎉 Review Match Found!",
                description="Great news! We've found a professional to review your resume.",
                color=0x00ff00
            )
            student_embed.add_field(name="Professional", value=result.get('professional', 'Your reviewer'), inline=True)
            student_embed.add_field(
                name="Next Steps",
                value="You'll receive an email shortly with scheduling details",
                inline=False
            )
            student_embed.add_field(name="Contact", value="propel@propel2excel.com", inline=True)
            
            await user.send(embed=student_embed)
            
        except discord.Forbidden:
            await ctx.send(f"⚠️ Could not send DM to {user.mention} - please notify them manually")
        
    except Exception as e:
        await ctx.send(f"❌ Error creating match: {e}")
```

#### **4. Fix `!review_stats` Command**

**File**: `cogs/resume_review.py` (lines 208-231)

**Current**: Shows placeholder statistics  
**Needed**: Call backend API for real statistics

**Replace the try block with**:
```python
@commands.command()
@commands.has_permissions(administrator=True)
async def review_stats(self, ctx):
    """Admin command to show resume review statistics"""
    try:
        # Call backend API
        payload = {"action": "review-stats"}
        stats = await self._backend_request(payload)
        
        embed = discord.Embed(
            title="📊 Resume Review Statistics",
            description="Current resume review program metrics",
            color=0x0099ff
        )
        
        # Current status breakdown
        embed.add_field(
            name="📋 Current Status",
            value=f"**Total Requests**: {stats.get('total_requests', 0)}\n"
                  f"**Pending Matches**: {stats.get('pending_requests', 0)}\n"
                  f"**Matched**: {stats.get('matched_requests', 0)}\n"
                  f"**Completed**: {stats.get('completed_requests', 0)}",
            inline=True
        )
        
        # System metrics
        embed.add_field(
            name="👥 System Metrics",
            value=f"**Active Professionals**: {stats.get('total_professionals', 0)}\n"
                  f"**Average Rating**: {stats.get('average_rating', 0):.1f}/5.0\n"
                  f"**Cancelled**: {stats.get('cancelled_requests', 0)}",
            inline=True
        )
        
        # Recent activity
        embed.add_field(
            name="📈 Last 7 Days",
            value=f"**New Requests**: {stats.get('recent_requests', 0)}\n"
                  f"**Completions**: {stats.get('recent_completions', 0)}",
            inline=True
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error fetching stats: {e}")
```

#### **5. Fix `!review_status` Command**

**File**: `cogs/resume_review.py` (lines 86-109)

**Current**: Shows generic "check email" message  
**Needed**: Call backend API for actual status

**Replace the try block with**:
```python
@commands.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def review_status(self, ctx):
    """Check status of your resume review request"""
    try:
        # Call backend API
        payload = {
            "action": "review-status",
            "discord_id": str(ctx.author.id)
        }
        
        result = await self._backend_request(payload)
        
        embed = discord.Embed(
            title="📊 Review Status",
            description=f"{ctx.author.mention}'s resume review status",
            color=0x0099ff
        )
        
        if not result.get('has_request'):
            embed.add_field(
                name="Status", 
                value="No review request found. Use `!resume` to get started!", 
                inline=False
            )
        else:
            status = result.get('status', 'unknown')
            status_messages = {
                'pending': '⏳ Waiting for professional match',
                'matched': '🤝 Matched with professional',
                'scheduled': '📅 Review session scheduled',
                'completed': '✅ Review completed',
                'cancelled': '❌ Request cancelled'
            }
            
            embed.add_field(
                name="Status", 
                value=status_messages.get(status, f"Status: {status}"), 
                inline=False
            )
            
            if result.get('professional'):
                embed.add_field(name="Professional", value=result['professional'], inline=True)
            
            if result.get('scheduled_time'):
                embed.add_field(name="Scheduled Time", value=result['scheduled_time'], inline=True)
            
            embed.add_field(
                name="Submitted", 
                value=result.get('submission_date', 'Unknown'), 
                inline=True
            )
        
        embed.add_field(
            name="Need Help?",
            value="Contact propel@propel2excel.com",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error checking status: {e}")
```

---

## 🚀 **Additional New Commands to Add**

Add these new admin commands to `cogs/resume_review.py`:

### **6. Add `!pending_reviews` Command**

```python
@commands.command()
@commands.has_permissions(administrator=True)
async def pending_reviews(self, ctx):
    """Show students waiting for professional matching"""
    try:
        # Call backend API
        payload = {"action": "review-stats"}
        stats = await self._backend_request(payload)
        
        pending_count = stats.get('pending_requests', 0)
        
        embed = discord.Embed(
            title="⏳ Pending Review Requests",
            description=f"Students waiting for professional matching",
            color=0xffaa00
        )
        
        embed.add_field(
            name="Pending Students",
            value=f"**{pending_count}** students waiting for matches",
            inline=False
        )
        
        if pending_count > 0:
            embed.add_field(
                name="Next Steps",
                value="1. Use `!list_professionals` to see available reviewers\n"
                      "2. Use `!match_review @student <professional_id>` to create matches",
                inline=False
            )
        else:
            embed.add_field(
                name="Status",
                value="✅ All students have been matched!",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error fetching pending reviews: {e}")
```

---

## 🧪 **Testing Checklist**

### **Backend Testing**
- [ ] Google Form submission creates ReviewRequest in database
- [ ] `!add_professional` actually stores professional data
- [ ] `!list_professionals` shows real professionals from database
- [ ] `!match_review` updates ReviewRequest status to 'matched'
- [ ] `!review_stats` shows real statistics from database

### **Integration Testing**
- [ ] Form webhook authentication works with `X-Form-Secret`
- [ ] Bot API calls work with `X-Bot-Secret`  
- [ ] Student Discord ID properly links form submissions to users
- [ ] Email notifications work (manual coordination for now)

### **User Workflow Testing**
1. [ ] Student uses `!resume` → Gets form link
2. [ ] Student submits form → Data appears in backend
3. [ ] Admin uses `!pending_reviews` → Shows waiting student
4. [ ] Admin uses `!add_professional` → Adds reviewer to pool
5. [ ] Admin uses `!match_review @student 1` → Creates match
6. [ ] Student uses `!review_status` → Shows matched status
7. [ ] Admin uses `!review_stats` → Shows updated statistics

---

## 🌟 **Quick Win Workflow Summary**

After you complete the integration:

**Admin Workflow:**
1. `!add_professional "John Smith" john@email.com "Tech, Software Engineering"`
2. `!pending_reviews` (see students waiting)
3. `!list_professionals` (get professional IDs)
4. `!match_review @student 1` (match with professional ID 1)
5. Manual email coordination for scheduling

**Student Experience:**
1. `!resume` → Gets form link
2. Submits form with availability
3. `!review_status` → Checks progress
4. Receives email with review coordination

---

## 📞 **Environment Variables Needed**

Make sure these are set in your deployment:

```bash
# Existing variables
DISCORD_TOKEN=your_discord_bot_token
BOT_SHARED_SECRET=your_existing_secret
BACKEND_API_URL=https://propel2excel-backend.onrender.com

# New variable for form integration
FORM_WEBHOOK_SECRET=generate-a-secure-random-token-here
```

---

## 🎯 **Priority Order**

1. **HIGH**: Fix Discord bot commands to call backend APIs
2. **HIGH**: Set up Google Forms webhook integration  
3. **MEDIUM**: Test complete end-to-end workflow
4. **LOW**: Add additional convenience commands

The backend is ready to go - you just need to connect the frontend pieces!

---

*Good luck! The infrastructure is solid, you're just wiring up the final connections. 🚀*
