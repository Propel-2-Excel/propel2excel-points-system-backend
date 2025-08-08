# 1-Week MVP Scope: Propel2Excel Points System

## 🔑 User Roles & Access

1. **User Authentication & Role-based Login**
    - Signup/Login for:
        - Admin
        - Student
        - Company
        - University
    - Users land in the correct **role-specific dashboard**
    - Store profile info: name, email, role, company/university, etc.

2. **Dashboard Access Control**
    - Admin: Access all dashboards (students, companies, universities)
    - Student: Access own dashboard only
    - Company: Access limited dashboards (aggregated student data, not names unless permission)

## 🧩 Points System (Core Logic)

3. **Points Structure**
    - Resume upload: +20 pts
    - Event attendance: +15 pts
    - Resource share: +10 pts
    - Liking/interacting: +2 pts
    - Posting a LinkedIn update: +5 pts

4. **Points Log**
    - Show students:
        - Total points
        - History with activity name & timestamp

## 🎁 Incentives System

5. **Incentives Dashboard (Student View)**
    - Display redeemable incentives:
        - Azure Certification – 50 pts
        - Hackathon – 100 pts
        - Resume Review – 75 pts
    - Show points required, sponsor, status (available/unlocked/redeemed)

6. **Incentive Redemption**
    - Students redeem if requirements met
    - Reduce points on redemption

7. **Admin Incentive Management**
    - Add/edit/remove incentives
    - View redemptions & approval status

## 📊 Company Reporting (Preview Feature)

8. **Company Dashboard**
    - Examples:
        - “300 students reached 100+ pts”
        - “Top 10 incentives redeemed: Azure Certs (120), Hackathon (89)...”
    - Sample breakdown:
        - % students in top quartile by points
        - Most engaged activities
        - % passed/failed for selected incentives

## 🔄 Website + Discord Integration

9. **Connection Points Setup**
    - Connect dashboard to main website (single login or iframe)
    - Discord Integration:
        - Set up webhook/dummy endpoint for simulated activity tracking
        - Ex: “If user posts in Discord, log +5 pts” (simulate 10+ Discord-triggered activities)

## 📦 Final Week 1 Deliverables

- Frontend: Live demoable dashboards
- Backend: Auth, points logic, reporting, redemptions
- DB: Role-specific tables (users, activities, incentives, logs)
- Admin panel: Incentives & user tracking
- GitHub repo w/ setup/README
- Walkthrough/demo video

*Plus*:
- Full Discord+API integrations (real-time tracking)
- Resume validation (upload/approve)
- Detailed reporting with filters
- Full analytics for company/university roles
- User notifications/badge/gamification
- Incentive approval workflow
- Slack/LinkedIn integrations
- Scalability tuning

## Tech Stack

- **Discord Bot:** Python, discord.py
- **Backend API/DB:** Django, Django REST Framework, PostgreSQL
- **Frontend:** React, Tailwind CSS

Other: Leaderboard

## Day-to-Day Expectations

- **Sunday:** Research
- **Monday:** Figure out technologies, plan, split tasks, setup discord bot
- **Tuesday:** Setup DB, frontend, backend, GitHub
- **Wednesday:** Basic frontend design
- **Thursday/Friday:** Continue frontend, backend, DB
- **Saturday:** Admin Panel, final touches

## Sample Week Plan

**Monday: Kickoff & Setup**
- Review goals, tech stack, communication setup
- Backend: setup Django, PostgreSQL, Discord bot
- Frontend: setup React, Tailwind
- Admin/Docs: start README, admin panel

**Tuesday: DB & Initial Components**
- Backend: DB tables (Users, Activities, Incentives, Logs), API for auth/points
- Frontend: dashboards (points, activities), leaderboard placeholder
- Admin: admin panel views, document schema

**Wednesday: Bot & Integration**
- Backend: Discord bot, event listeners, API `/api/user/{id}/add-points`
- Frontend: point redemption store, API connections
- Admin: detailed activity log

**Thursday: Redemption & Integration**
- Backend: `/api/redeem` logic/test, bot test
- Frontend: redemption store functionality
- Admin: manage incentive items

**Friday: Final Integration**
- End-to-end testing
- Bugfix
- Finalize API/frontend/admin

**Saturday: Code Review & Docs**
- Code review & refactor
- Complete docs (setup, instructions, deploy)
- UI/UX polish

**Sunday: Demo & Recap**
- Demo: Discord→website→redemption
- Review progress/challenges
- Roadmap for Week 2

---

