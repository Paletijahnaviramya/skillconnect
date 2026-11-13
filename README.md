# SkillConnect – Intelligent Local Employment Platform

A Flask + SQLite academic prototype that connects women service providers with flexible local work.

## Features

### Women service providers
- Register and sign in with a provider account
- Maintain locality, skills, availability and profile description
- Upload up to five portfolio photos (JPG, PNG, WEBP; max 4 MB each) or add image URLs
- Browse and filter open opportunities
- Receive transparent rule-based recommendations (skill 60%, locality 30%, flexibility 10%)
- Apply for opportunities and track application status
- Save/shortlist opportunities
- Join peer skill circles
- View an illustrative earnings estimate

### Customers / employers
- Register and sign in
- Publish opportunities with category, locality, work type and estimated payment
- View platform listings

### Admin
- View registered users
- Review applications and update their status (Applied, Shortlisted, Selected, Rejected)
- View platform statistics and local skill demand

### Community and insights
- Dashboard statistics and opportunity trends
- Skill circles for peer learning and sharing
- Growth recommendations and skill-gap learning tips
- Customer reviews/testimonials data endpoints

## Run locally (Windows PowerShell)

1. Extract the ZIP.
2. Open PowerShell in the folder that contains `app.py` and `requirements.txt`.
3. Run:

```powershell
py -m pip install -r requirements.txt
py app.py
```

4. Open http://127.0.0.1:5000

If PowerShell says `requirements.txt` cannot be found, run `dir` and check that you are in the inner `SkillConnect` folder. The file must be alongside `app.py`.

## Demo accounts

| Role | Phone | Password |
|---|---|---|
| Woman provider | 9000000001 | demo |
| Customer | 9000000005 | demo |
| Admin | 9000000004 | admin |

Other seeded providers: 9000000002 / demo and 9000000003 / demo.

## Render deployment

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Add environment variable `SECRET_KEY` with a long random value.
- Connect the GitHub repository containing the contents of this project folder.

The app initializes/migrates its SQLite schema when imported by Gunicorn. **Important:** Render free web services use ephemeral local storage; SQLite data and uploaded portfolio photos can be lost when the service restarts, redeploys or spins down. Use a persistent database/object storage for a production deployment.

## Project structure

```text
SkillConnect/
  app.py
  requirements.txt
  README.md
  templates/
    index.html
  static/
    style.css
    app.js
    uploads/       # created when portfolio photos are uploaded
```

## Academic prototype limitations

- Matching is a transparent weighted rules engine, not a trained machine-learning model.
- Earnings estimates are illustrative, not guaranteed income.
- Demo credentials are for local evaluation only.
- Before real public use, implement password hashing, CSRF protection, stronger validation/rate limiting, consent and privacy controls, secure production configuration, and persistent storage.
