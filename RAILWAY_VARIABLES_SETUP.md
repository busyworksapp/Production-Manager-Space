# Railway Environment Variables Setup Guide

## Step 1: Access Railway Dashboard

1. Go to [railway.app](https://railway.app)
2. Log in with your GitHub account
3. Click on your **Production-Manager-Space** project
4. You'll see your deployment with the Flask app

## Step 2: Navigate to Variables

1. In the project view, click on your **app service** (the one running the Python Flask app)
2. Look for the **Variables** tab at the top (next to Deploy, Logs, Metrics, etc.)
3. Click on **Variables**

## Step 3: Add Database Environment Variables

Add the following variables one by one. Click **+ New Variable** for each:

### 3.1 Database Host
- **Key:** `DB_HOST`
- **Value:** Your MySQL database hostname (e.g., `mysql.railway.app` or your actual host)
- Click **Add**

### 3.2 Database Port
- **Key:** `DB_PORT`
- **Value:** `3306` (standard MySQL port)
- Click **Add**

### 3.3 Database User
- **Key:** `DB_USER`
- **Value:** Your MySQL username (e.g., `root`)
- Click **Add**

### 3.4 Database Password
- **Key:** `DB_PASSWORD`
- **Value:** Your MySQL password (the strong one you created)
- Click **Add**

### 3.5 Database Name
- **Key:** `DB_NAME`
- **Value:** `pms` (or whatever you named your database)
- Click **Add**

## Step 4: Add Security Variables

### 4.1 JWT Secret Key (IMPORTANT - SECURITY)
- **Key:** `JWT_SECRET_KEY`
- **Value:** Generate a strong random string (copy one of the options below):

**Option 1 - Using PowerShell (recommended):**
```powershell
[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

**Option 2 - Using Python:**
```python
import secrets
import base64
print(base64.b64encode(secrets.token_bytes(32)).decode())
```

**Option 3 - Pre-generated examples (use ONE of these):**
```
sN8kL9mP2xQ7rT4vZ1wB3cD6eF9gH0jK2lM5nO8pR1sT4uV7wX0yZ3aB6cD9eF2gH5jK8lM1nO4pR7sT0uV3wX6yZ9aB2cD5eF8gH1jK4lM7nO0pR3sT6uV1wX4yZ7aB0cD3eF6gH9jK2lM5nO8pR1sT4uV7wX0yZ3aB6cD9eF2gH5jK8lM1nO4pR7sT0uV3wX6yZ9aB2cD5eF8gH1jK4lM7nO0pR3sT6uV1wX4yZ7aB0cD3eF6gH9jK2lM5nO8pR1sT4uV7wX0yZ3aB6cD9eF2gH5jK8lM1nO4pR7sT0uV3wX6yZ9aB2cD5eF8gH1jK4lM7nO
```

- Click **Add**

## Step 5: Add Redis URL (Optional but Recommended)

### 5.1 Redis Connection URL
- **Key:** `REDIS_URL`
- **Value:** `redis://default:<password>@<host>:<port>` 

If you have a Redis instance on Railway:
- Get the connection string from your Redis service variables
- Or use format: `redis://:<password>@<host>:6379`

Example: `redis://:mypassword123@redis.railway.app:6379`

- Click **Add**

## Step 6: Add App Configuration Variables (Optional)

### 6.1 Flask Environment
- **Key:** `FLASK_ENV`
- **Value:** `production`
- Click **Add**

### 6.2 Flask Debug
- **Key:** `FLASK_DEBUG`
- **Value:** `0` (disabled in production)
- Click **Add**

### 6.3 App Version
- **Key:** `APP_VERSION`
- **Value:** `1.0.0`
- Click **Add**

## Step 7: Add Twilio Variables (If Using WhatsApp/SMS)

### 7.1 Twilio Account SID
- **Key:** `TWILIO_ACCOUNT_SID`
- **Value:** Your Twilio Account SID (from Twilio console)
- Click **Add**

### 7.2 Twilio Auth Token
- **Key:** `TWILIO_AUTH_TOKEN`
- **Value:** Your Twilio Auth Token (keep this SECRET!)
- Click **Add**

### 7.3 Twilio Phone Number
- **Key:** `TWILIO_PHONE_NUMBER`
- **Value:** Your Twilio phone number (e.g., `+14155238886`)
- Click **Add**

## Step 8: Deploy with New Variables

1. After adding all variables, Railway will automatically redeploy
2. Watch the **Deploy** tab to see the build and deploy progress
3. You should see:
   - ✅ Building Docker image
   - ✅ Pushing to registry
   - ✅ Deploying
   - ✅ Running

## Step 9: Verify Deployment Success

1. Go to the **Logs** tab
2. Look for these success messages:
   ```
   ✓ Environment validation passed
   Application initialized successfully
   Database connection pool created on first use (once you make a request)
   ```

3. Click the **deployment URL** at the top right to visit your app
4. You should see the login page!

## Step 10: Test Login

1. Visit your Railway app URL
2. Login with credentials:
   - **Username:** `admin@barron`
   - **Password:** `Admin@2026!`
3. You should see the dashboard!

---

## Troubleshooting

### Issue: "Environment validation passed" but still database errors

**Solution:** The app boots successfully but needs to connect to the database on first request. Make sure all DB variables are set correctly.

### Issue: Connection refused error

**Cause:** Database variables don't match your actual MySQL server

**Solution:**
1. Verify `DB_HOST` is correct (not `localhost` for remote databases)
2. Verify `DB_USER` and `DB_PASSWORD` match
3. Verify `DB_PORT` is `3306` (or correct port for your setup)

### Issue: JWT Secret Key issues

**Cause:** Using special characters that break the connection string

**Solution:** Use the base64-encoded key from Step 4, or keep it simple alphanumeric

### Issue: Redis connection errors

**Cause:** `REDIS_URL` format is wrong or Redis is not available

**Solution:** 
- If you don't have Redis, you can skip this variable
- The app will warn but still work
- Only set `REDIS_URL` if you have an actual Redis instance

---

## Complete Variable Reference

| Variable | Required | Example Value |
|----------|----------|---|
| `DB_HOST` | ✅ Yes | `mysql.railway.app` |
| `DB_PORT` | ✅ Yes | `3306` |
| `DB_USER` | ✅ Yes | `root` |
| `DB_PASSWORD` | ✅ Yes | `your_strong_password` |
| `DB_NAME` | ✅ Yes | `pms` |
| `JWT_SECRET_KEY` | ✅ Yes | Base64 encoded 32-byte string |
| `FLASK_ENV` | ❌ Optional | `production` |
| `FLASK_DEBUG` | ❌ Optional | `0` |
| `REDIS_URL` | ❌ Optional | `redis://:<password>@host:6379` |
| `TWILIO_ACCOUNT_SID` | ❌ Optional | Account SID from Twilio |
| `TWILIO_AUTH_TOKEN` | ❌ Optional | Auth token from Twilio |
| `TWILIO_PHONE_NUMBER` | ❌ Optional | `+14155238886` |

---

## After Setup

Once all variables are configured and the app is running:

1. **Database will auto-migrate** on first connection (schema created)
2. **Test users are pre-seeded** (admin@barron / Admin@2026!)
3. **Logs will show all connections working**
4. **App is production-ready!**

For additional help, refer to:
- [Railway Documentation](https://docs.railway.app)
- [Railway Variables Guide](https://docs.railway.app/deploy/variables)
