## **User Story — Admin Dashboard for Propel to Excel Student Portal**

**Title:** Admin manages student accounts, activities, and rewards in the Propel to Excel Student Portal.

**As an** Admin (internal role, not publicly available during signup),  
 \~**I want** a dedicated dashboard that allows me to view, manage, and update student information, points, rewards, and leaderboard standings.  
 \~**So that** I can ensure smooth operation of the portal, maintain accurate records, and oversee student engagement effectively.

---

### **Acceptance Criteria**

1. **Login & Access**

   * Admins can log in using their admin credentials.

   * Admin accounts are created internally by the system super-admin.

   * Upon login, admins are directed to the **Admin Dashboard** instead of the student dashboard.

2. **Dashboard Overview Page**

   * Displays total number of registered students.

   * Shows active students (logged in within last 30 days).

   * Shows total cumulative points awarded across the platform.

   * Highlights top 5 students on the leaderboard.

   * Displays recent student activities (latest 10 actions across all users).

3. **Student Management**

   * Search students by name, email, or Discord username.

   * View full student profile (same as student profile page, with ability to edit).

   * Manually adjust points (add or deduct) with reason tracking.

   * Reset passwords for students.

   * Update or correct profile information (major, graduation year, university).

   * Suspend/reactivate accounts.

4. **Points & Leaderboard Management**

   * View full leaderboard with sorting and filtering options.

   * Adjust leaderboard standings by editing points.

   * See point history for any student, including activity source and timestamp.

5. **Rewards Management**

   * Add, edit, or remove rewards from the **P2E Rewards Catalog**.

   * Set point costs for each reward.

   * Mark rewards as available/unavailable.

   * Track reward redemptions (who redeemed, when, and fulfillment status).

   * Manage rank-based opportunities (set rank requirement, add details, set visibility).

6. **Activity Tracking**

   * View all student activities (engagement logs: workshops, events, redemptions).

   * Filter activities by type, date, or student.

   * Export activity logs to CSV for reporting.

7. **Analytics & Reporting**

   * Access engagement analytics (e.g., most popular rewards, most active students, points earned per activity type).

   * View cumulative points distribution charts.

   * Track growth trends in student signups.

   * Export reports in PDF or CSV format.

8. **Admin Account Controls**

   * Add new admins (only for super-admins).

   * Edit or deactivate admin accounts.

   * View admin activity logs for accountability.

---

### **Example Admin Workflow**

1. **Log in** with admin credentials.

2. **Check Dashboard**: See how many students joined this week and who’s leading on the leaderboard.

3. **Manage Students**: Search for “JaneDoe\#1234” → View profile → Add \+50 points for attending a workshop.

4. **Update Rewards**: Add a new reward “Propel Hoodie” costing 500 points.

5. **View Analytics**: See that most points this month came from “Tech Talks” attendance.

6. **Export Report**: Download monthly engagement stats for the board meeting.

---

	

  