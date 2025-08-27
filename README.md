# Discord Points System

A career-focused Discord bot that motivates and rewards student achievement through a points system, real-time activity tracking, moderation tools, and interactive rewards - creating an engaging, supportive, and growth-driven online community.

## 🚀 MVP Features

### User Roles & Access
- **Admin**: Full access to all dashboards and management
- **Student**: Access to own dashboard, points tracking, and incentive redemption
- **Company**: Limited access to aggregated student data
- **University**: Limited access to student analytics

### Points System
- Professional resume review: Professional review process
- Event attendance: +15 pts
- Resource share: +10 pts
- Like/interaction: +2 pts
- LinkedIn post: +5 pts
- Discord activity: +5 pts

### Resume Review System
- **Enhanced Process**: Professional review workflow with form submission
- **Google Forms Integration**: Structured data collection for better matching
- **Professional Network**: Curated reviewers across multiple industries
- **Admin Tools**: Complete management system for review coordination
- **Email Integration**: Professional communication via propel@propel2excel.com

### Incentives
- Azure Certification (50 pts)
- Hackathon Entry (100 pts)
- Resume Review (75 pts)

## 🛠️ Tech Stack

- **Backend**: Django 4.2 + Django REST Framework
- **Database**: SQLite (development) / PostgreSQL (production)
- **Authentication**: JWT tokens
- **Discord Integration**: discord.py
- **API Documentation**: drf-spectacular (Swagger)

## 📦 Installation & Setup

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd propel2excel-points-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` using the keys below (never commit real secrets):
   ```env
   SECRET_KEY=django-insecure-change-me
   DEBUG=True
   DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db>
   # Bot integration
   DISCORD_TOKEN=
   BACKEND_API_URL=http://127.0.0.1:8000
   BOT_SHARED_SECRET=
   ```

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## 🔗 API Endpoints

### Authentication
- `POST /api/users/register/` - Register new user
- `POST /api/users/login/` - Login user
- `GET /api/users/profile/` - Get current user profile

### Points System
- `POST /api/users/{id}/add_points/` - Add points for activity
- `GET /api/points-logs/` - View points history
- `GET /api/activities/` - List available activities

### Incentives
- `GET /api/incentives/` - List available incentives
- `POST /api/redemptions/redeem/` - Redeem incentive
- `GET /api/redemptions/` - View redemption history

### Admin Only
- `POST /api/redemptions/{id}/approve/` - Approve redemption
- `POST /api/redemptions/{id}/reject/` - Reject redemption

## 📚 API Documentation

Visit `/api/docs/` for interactive Swagger documentation.

## 🎮 Discord Bot Setup

1. Create a Discord application and bot (enable Message Content + Server Members intents)
2. Put the token in `.env` as `DISCORD_TOKEN`
3. Start backend: `python manage.py runserver`
4. Start bot: `python bot.py`
5. The bot posts activities to `/api/bot` using `X-Bot-Secret`

## 🗄️ Database Schema

### Core Tables
- `users` - User accounts with roles and points
- `activities` - Points-earning activities
- `points_log` - History of all points earned
- `incentives` - Available rewards
- `redemptions` - Incentive redemption history
- `user_status` - User warnings and suspensions

## 🚧 Development Roadmap

### Week 1 (Current)
- ✅ Django models and API setup
- ✅ User authentication and roles
- ✅ Points system core logic
- ✅ Incentive redemption system
- 🔄 Discord bot integration
- 🔄 Frontend dashboard

### Week 2 (Future)
- Advanced analytics and reporting
- Company/university dashboards
- Real-time notifications
- Enhanced Discord integration
- Performance optimization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
