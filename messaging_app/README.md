# Messaging App

A Django REST API for real-time messaging with role-based permissions.

## Features

- JWT authentication
- Role-based access (Admin, Host, Guest)
- Conversations with multiple participants
- Message read receipts
- Real-time messaging capability

## API Documentation UI


## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Run server
python manage.py runserver
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/login/` - Login
- `POST /api/v1/auth/logout/` - Logout
- `GET /api/v1/auth/profile/` - User profile

### Conversations
- `GET /api/v1/conversations/` - List conversations
- `POST /api/v1/conversations/` - Create conversation
- `GET /api/v1/conversations/{id}/` - Get conversation
- `POST /api/v1/conversations/{id}/add_participant/` - Add participant
- `POST /api/v1/conversations/{id}/leave/` - Leave conversation

### Messages
- `GET /api/v1/messages/` - List messages
- `POST /api/v1/messages/` - Send message
- `GET /api/v1/messages/unread/` - Unread messages
- `POST /api/v1/messages/{id}/mark_read/` - Mark as read

## User Roles

- **Admin**: Full system access
- **Host**: Manage conversations and users
- **Guest**: Send messages, join conversations

## Environment Variables

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
```

## Tech Stack

- Django REST Framework
- JWT tokens
- SQLite/PostgreSQL
- Python 3.8+