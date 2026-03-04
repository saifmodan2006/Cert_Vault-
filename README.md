# CertVault - Certificate Management Platform

**CertVault** is a modern, secure, and professional web application designed to help users manage, store, and share their professional certificates and credentials. Built with Flask, it offers a robust set of features for individuals and professionals to keep their achievements organized and accessible.

## 🚀 Key Features

- **Secure Authentication**: User registration, login, and profile management with encrypted passwords.
- **Certificate Dashboard**: A clean interface to view all certificates with advanced filtering by title, issuer, or tags.
- **Support for Multiple Formats**: Upload certificates in PDF, PNG, JPG, and other popular image formats.
- **Smart Tracking**: Track issue dates and expiry dates. Get visual indicators for expiring or expired documents.
- **Public & Private Sharing**: Keep certificates private or generate secure, unique public links to share your achievements with others.
- **Activity Logging**: Maintain a history of your actions (uploads, edits, logins) for better tracking.
- **Download & Export**: Easy one-click downloads for all your stored certificates.
- **Responsive Design**: Modern UI that looks great on both desktop and mobile devices.

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Database**: SQLite (SQLAlchemy)
- **Security**: Flask-Bcrypt (Hashing), Flask-Login (Sessions)
- **Production Server**: Waitress
- **Frontend**: HTML5, Vanilla CSS3 (Professional Aesthetics)

## 📦 Installation & Setup

### Prerequisites
- Python 3.8+
- Git

### Initial Setup
1. **Clone the repository**:
   ```bash
   git clone https://github.com/saifmodan2006/Cert_Vault-.git
   cd Cert_Vault-
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the environment**:
   - Windows: `.\venv\Scripts\activate`
   - Linux/macOS: `source venv/bin/activate`

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**:
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your_secret_key_here
   DATABASE_URL=sqlite:///certificate_platform.db
   ```

## 🚀 Running the Application

### Development Mode
For development with auto-reload enabled:
```bash
./run_dev.bat
```
Visit `http://127.0.0.1:5000` in your browser.

### Production Mode
To run the app using the high-performance Waitress server:
```bash
./run_prod.bat
```
Visit `http://localhost:8000`.

## 🔒 Security & Privacy
- Sensitive files like `.env`, `venv/`, and `.db` are excluded from the repository via `.gitignore`.
- User uploads are isolated into unique folders.
- Public sharing is disabled by default and must be explicitly enabled per certificate.

## 📄 License
This project is for personal use and management. See [LICENSE](LICENSE) for details (if applicable).