# Railway Deployment Setup Guide

## Current Status
The application has been pushed to Railway and is attempting to start, but **environment variables are not configured**.

## ⚠️ Critical: Set Environment Variables in Railway

### Step 1: Access Railway Dashboard
1. Go to [railway.app](https://railway.app)
2. Navigate to your project: **Production-Manager-Space**
3. Click on your service (the one with the Flask app)
4. Go to the **Variables** tab

### Step 2: Add Database Variables

If you have a MySQL service linked in Railway, the following should be auto-populated:
- `DB_HOST` - Railway proxy hostname for MySQL (e.g., `mainline.proxy.rlwy.net`)
- `DB_PORT` - MySQL port (e.g., `51104`)
- `DB_USER` - Database user (e.g., `root`)
- `DB_PASSWORD` - Database password
- `DB_NAME` - Database name (e.g., `railway`)

**If not auto-populated**, add them manually:
```
DB_HOST=mainline.proxy.rlwy.net
DB_PORT=51104
DB_USER=root
DB_PASSWORD=<your_password>
DB_NAME=railway
```

### Step 3: Add Application Variables

Add these variables in the Railway dashboard:

```
JWT_SECRET_KEY=<generate-a-64-character-random-string>
FLASK_ENV=production
FLASK_DEBUG=False
```

### Step 4: Add Twilio Credentials (Optional)

If you want SMS/WhatsApp integration:
```
TWILIO_ACCOUNT_SID=<your-account-sid>
TWILIO_AUTH_TOKEN=<your-auth-token>
TWILIO_FROM_PHONE=+14155238886
```

## Generate JWT_SECRET_KEY

Use Python to generate a secure key:
```bash
python -c "import secrets; import string; alphabet = string.ascii_letters + string.digits + '!@#$%^&*_-=+[]{}()'; print(''.join(secrets.choice(alphabet) for _ in range(64)))"
```

## Testing Locally

Before deploying to Railway, test locally:

```bash
# Terminal 1 - Start MySQL (if using local MySQL)
mysql -u root -p

# Terminal 2 - Run the app
python app.py
```

Visit http://localhost:5000 and login with:
- Username: `admin@barron`
- Password: `Admin@2026!`

## After Setting Variables

1. Go back to Railway dashboard
2. The app should automatically redeploy
3. Check the **Logs** tab to verify startup
4. Once running, visit your Railway URL: `https://production-manager-space-production.up.railway.app`

## Troubleshooting

### "ModuleNotFoundError: No module named 'main'"
- ✅ Fixed - Using `Procfile` with `wsgi:app` entry point

### Missing environment variables error
- Check Railway Variables tab
- Ensure all 5+ required variables are set
- Redeploy after adding variables

### Database connection timeout
- Verify database service is running in Railway
- Check DB_HOST, DB_PORT, DB_USER, DB_PASSWORD are correct
- Ensure firewall allows connections

### "Worker failed to boot"
- Check Railway Logs for detailed error messages
- Verify all environment variables are set
- Run `python app.py` locally to test

## Production Checklist

Before going live:
- [ ] All environment variables set in Railway
- [ ] JWT_SECRET_KEY is a strong random value
- [ ] Database service is connected
- [ ] FLASK_DEBUG=False for production
- [ ] Twilio credentials added if using SMS/WhatsApp
- [ ] Test login with admin credentials
- [ ] Verify all API endpoints work

## Local Development vs Railway

**Local Development (.env file):**
- Variables can be hardcoded in `.env`
- `FLASK_DEBUG=True` for auto-reload
- `FLASK_ENV=development`

**Railway Production:**
- Set variables in Railway Dashboard UI
- `FLASK_DEBUG=False` for stability
- `FLASK_ENV=production`
- Automatic HTTPS
- Automatic scaling
