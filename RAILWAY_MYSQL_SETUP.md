# Railway MySQL Connection - Variable Mapping

## Your Railway MySQL Variables

You already have these provided by Railway:
```
MYSQLDATABASE = railway
MYSQLHOST = mainline.proxy.rlwy.net
MYSQLPASSWORD = JMucY1eZT1LFFdvYxg5QtgYnAwCDjvG
MYSQLPORT = 51104
MYSQLUSER = root
```

## What Your App Needs

Your Flask app is configured to look for these variable names:
```
DB_HOST
DB_PORT
DB_USER
DB_PASSWORD
DB_NAME
```

## ✅ ADD THESE VARIABLES TO RAILWAY

Go to Variables tab and add these exact mappings:

| App Variable | Value |
|---|---|
| `DB_HOST` | `mainline.proxy.rlwy.net` |
| `DB_PORT` | `51104` |
| `DB_USER` | `root` |
| `DB_PASSWORD` | `JMucY1eZT1LFFdvYxg5QtgYnAwCDjvG` |
| `DB_NAME` | `railway` |

## Add These Too

### JWT Secret Key (for security)
```
JWT_SECRET_KEY = your-secret-key-here
```

Generate one using:
```powershell
[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Or use this example:
```
MIAKZA7nP2xQ7rT4vZ1wB3cD6eF9gH0jK2lM5nO8pR1sT4uV7wX0yZ3aB6cD9eF2gH5jK8lM1
```

## Step-by-Step Instructions

1. **Go to Railway Dashboard**
   - Click on your project: `Production-Manager-Space`
   - Click on your **app service** (Flask app)

2. **Click Variables Tab**
   - Look at the top navigation

3. **Add Each Variable**
   - Click **+ New Variable** button
   - Enter `DB_HOST` as key
   - Enter `mainline.proxy.rlwy.net` as value
   - Click **Add**
   - Repeat for the other 4 database variables above

4. **Railway Auto-Redeploys**
   - After you add the variables, Railway will automatically rebuild and redeploy
   - Check the **Deploy** tab to watch the progress

5. **Check Logs**
   - Go to **Logs** tab
   - Look for: `✓ Environment validation passed`
   - Look for: `Database connection pool created`

6. **Test Your App**
   - Click the URL at the top right to visit your app
   - You should see the **Login Page**
   - Login with: `admin@barron` / `Admin@2026!`

---

## Why Not Use MYSQL* Variables Directly?

Railway provides generic MySQL variables (`MYSQLHOST`, `MYSQLPORT`, etc.) but your app is configured to look for app-specific ones (`DB_HOST`, `DB_PORT`, etc.). 

By creating these mapped variables, the app finds exactly what it needs without modifying code.

---

## ⚠️ Important Notes

- The `railway` database may be empty - that's OK
- The app will auto-create the schema on first connection
- Test users are seeded in the deployment
- This setup is secure - Railway variables are encrypted
