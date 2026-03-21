# Smart Recover

Smart Recover is a lightweight university lost-and-found web app with a Python backend, browser frontend, file-backed storage, and Gmail SMTP notification support.

## Features

- University email sign-up and login validation using `@bennett.edu.in`
- User profile storage with name, email, and university ID
- Lost item and found item reporting with image upload
- Restricted access to the found-items list until a user submits at least one lost-item report
- Automatic matching suggestions using item-name similarity, keyword overlap, and location similarity
- Claim verification flow with proof text and stored claim history
- Office-based pickup workflow after admin approval with a generated pickup token
- Real email sending through Gmail SMTP when configured, plus stored delivery logs in the app
- Admin view for pending claim review and suspicious-activity monitoring

## How to run

1. Copy `.env.example` to `.env`.
2. Put the Gmail App Password for `smartrecoverlostandfound@gmail.com` into `SMTP_APP_PASSWORD`.
3. Start the server:

```powershell
py app.py
```

4. Open `http://127.0.0.1:8000`.

## Vercel note

This project can be deployed to Vercel with the included `api/index.py` and `vercel.json`, but Vercel's Python runtime is serverless. The app therefore falls back to temporary storage on Vercel (`/tmp`), which is not durable. That means accounts, sessions, and lost/found data may reset between cold starts or deployments. For a real production deployment on Vercel, move storage to a database first.

## Demo admin account

Log in with `s24bcau0044@bennett.edu.in` to see the admin panel.

## Email setup

Use a Gmail App Password, not the normal Gmail password. Smart Recover will send mail from `smartrecoverlostandfound@gmail.com` when SMTP is configured; otherwise it will still log the email events in the dashboard with a queued status.
