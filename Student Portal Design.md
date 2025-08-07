**STUDENT PORTAL DESIGN**

### **The Initial Login/Sign Up Page**

When a user clicks on the Propel to Excel website login page, they will see a page with two primary options: **Login** and **Sign Up**.

* **Login:** This is for existing users. They will enter their email and password to access their specific portal (student, company, etc.).  
* **Sign Up:** This is for new users. Clicking this button initiates the dynamic signup flow 

**The Sign Up Flow**

1. **Role Selection:** A new user clicks "Sign Up" and is immediately presented with a clear choice of roles: **Student, Company, Non-Profit Organization, University**. Since this is the student portal, the user will select **"Student." NOTE: Admin will not be an option and this role will be created internally.**   
2. **Discord Name Validation**   
* The user is presented with a simple form asking for their Discord name.  
* The student enters their full Discord username (e.g., JaneDoe\#1234).  
* The system performs a check to see if this user exists on the Propel2Excel Discord server.  
* Success: If the user is found, they are granted access to the next step of the signup process.  
* Failure: If the user is not found, an error message is displayed (e.g., "Sorry, your Discord name was not found. Please join our server to continue."), and they cannot proceed.  
3. **Student Registration Form**: Only after successfully validating their Discord name, the student is presented with the full registration form. This form will automatically store their Discord name, but they will need to provide the rest of their details:  
* Full Name  
* Email Address  
* Password  
* University/Institution  
* Major  
* Expected Graduation Year  
4. **Account Creation & Confirmation:** Once the student fills out and submits this form, their account is created. They receive a confirmation message and are then directed to their new **Student Dashboard**.

**Student Portal**

**Dashboard Page**

This page is designed to be the student's personalized home base. Upon logging in, this will be the landing page, and they are immediately presented with a clear and concise overview of their progress and key activities. This can be arranged as designer sees fit. Components on this page include:

* **The Header and Navigation**  
  * **Components:**  
* Portal Title/Logo: A clear visual identity at the top.  
* Welcome Message: A personalized greeting, such as "Hello, Jane Doe\!"  
* Navigation Links: Simple, clear links to:  
  * **Dashboard**: To return to this main page.  
    * **My Profile**: To manage their personal and Discord information.  
    * **Rewards**: To view and redeem points.  
  * Logout Button: A prominent button for a secure exit.

* #### **The Point Summary Card:** To immediately show the student their most important metric: their current points.

  * **Components:**  
    * Point Value: A large, bold number displaying the current point balance  
    * Call to Action: A button or link below/beside  the point total that says something like "Redeem Points" or "View Rewards," directing them to the next step in the point-earning journey. This will take them to the rewards page.  
*  **The Leaderboard**  
  * **Components:**  
    * Ranked List: A list of the top 10-20 students with the highest point totals (cummulative)  
    * Student Information: Each entry would display the student's rank, a name (either their Discord name or their full name, depending on privacy settings), and their total points  
    * Student's Own Rank: A specific entry highlighting the current user's own rank, even if they are not in the top 10\. This gives them a clear sense of their standing.  
* **Recent Activity Log:** To provide a chronological record of how points were earned or redeemed.  
  * **Components:**  
    * This should be a list of the most recent 5-10 activities with a short phrase for each entry e.g **“Attended Resume Workshop”** or “**Redeemed Merch”**  
    * Each entry should have a specific point charge for that activity (e.g., `+50`, `-100`).  
    * Each entry should also have a timestamp  
* **Analytics section:** To give students a deeper understanding of their engagement  
  * **Components:**  
    * **Point Breakdown Pie Chart:** A pie chart that visually represents the percentage of points earned from each type of activity. This helps students see where the majority of their points are coming from (e.g., workshops, profile completion, Discord engagement). This will reflect the breakdown based on their Cummulative point (all the points they have earned not the current points available)  
    * **Point Flow Line Chart:** A line graph that tracks the student's point balance over time. It will visually show when points were added or deducted, providing a historical view of their point activity and engagement trends. \- **Tomisin already has this**

**Rewards Page**  
This page will serve as the gateway to both point-based redemptions and exclusive, rank-based opportunities. The page will be clearly divided into two sections to avoid confusion.

*  **Header & Point Balance**  
  * **Current Points Display:** At the top of the page, the student's current point balance will be prominently displayed. This reminds them of their spending power and is a crucial context for the P2E rewards section.  
  * **Current Rank:** The student's current leaderboard rank will also be visible here. This provides immediate context for which exclusive opportunities might be available to them.  
* **P2E Rewards Catalog (Points-Based Redemption):** This section is a traditional e-commerce-style catalog where students can redeem their points for various rewards.  
* **Reward Tiles:** A grid of visual tiles, each representing a different P2E reward.  
* **Reward Information:** Each tile will clearly display:  
  * An image of the reward (e.g., a Propel to Excel t-shirt, a gift card logo).  
  * A brief, appealing description of the item.  
  * The **point cost** to redeem it.  
* **Dynamic Availability:** The system will check the student's point balance in real-time.  
  * **Available Rewards:** Rewards that the student has enough points for will be brightly displayed with a clickable "Redeem" button.  
  * **Unavailable Rewards:** Rewards that the student cannot afford will be visually grayed out and marked with "Requires X more points." This acts as a clear motivator to earn more.  
* **Redemption Process:** Clicking "Redeem" will trigger a confirmation message to prevent accidental spending. After confirmation, points will be deducted, and instructions on how to claim the reward will be provided.


*  **Exclusive Company Opportunities (Rank-Based Visibility):** This section is for more privileged rewards that cannot be bought with points. Instead, they are unlocked by achieving a certain rank on the leaderboard.  
* **Opportunities List:** This will be a list of exclusive internships, mentorships, or special events offered by partner companies.   
* **Rank-Based Visibility:** The student's rank will be checked for each opportunity.  
  * **Unlocked Opportunities:** If the student's rank meets the requirement, the opportunity will be fully visible, with a clear button to "Learn More" or "Apply." This section will be prominently displayed.  
  * **Locked Opportunities:** If the student's rank is too low, the opportunity will appear as a "teaser." It might show a blurred image, a title like "Exclusive Internship at \[Company Name\]," and a message that says, "Unlock this opportunity by reaching Rank \#X on the leaderboard." This serves as a powerful incentive to climb the ranks.  
* **Redemption History**  
  A separate, small section at the bottom of the page will display a log of the rewards a student has already redeemed. This provides a personal history of their “achievements” and "purchases" on the platform.

**Profile Page**

This page is designed to be a clean, user-friendly space where students can view and manage their personal details and see the status of their Discord integration. The layout will be simple and organized for easy navigation.

* #### **Header**

  * **Page Title:** A clear title, such as "My Profile" or "Account Information."  
  * **Edit/Save Button:** A button that toggles between "Edit Profile" and "Save Changes," allowing students to update their information.

* ####  **Personal Information:** This section displays the core details of the student's account.

* **Full Name:** Displayed as a read-only field.  
* **Email Address:** Displayed as a read-only field, since this is tied to their login credentials.  
* **University/Institution:** An editable field with an input box. This allows students to update their university information.  
* **Major:** An editable field with an input box.   
* **Expected Graduation Year:** An editable field, likely a dropdown or a simple input box, for them to update as needed.  
* **Discord Integration Status:** This is a critical section that highlights the successful connection to their Discord account.  
* **Discord Username:** A prominent display of their Discord name and discriminator (e.g., JaneDoe\#1234). This field is read-only, as it was validated during signup.  
* **Resume Status:** This is a dynamic field that provides clear feedback on the resume upload. The text will change depending on the status:  
  * **"Resume Uploaded"**: A green status indicator and a message confirming that their resume has been successfully received from Discord.  
  * **"No Resume Found"**: A red or yellow status indicator and a message prompting them to upload their resume to the designated Discord channel. This message will include a clear call-to-action or link to instructions.  
* **Profile Picture:** The profile picture associated with their Discord account will be displayed here, offering a visual connection to their Discord identity.  
* **Resume & Portfolio:** This section is a dedicated space for the student's professional documents and links.  
* **Resume View:** A place to view a preview of their most recently uploaded resume. This could be a small thumbnail or a downloadable link.  
* **Portfolio Links:** Editable fields where students can add links to their personal portfolio, GitHub, or LinkedIn profiles.

