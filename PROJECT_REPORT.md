# Smart Recover Project Report

## 1. Project Title

**Smart Recover: A University Lost-and-Found Web Application**

## 2. Project Overview

Smart Recover is a web-based lost-and-found management system designed for university campuses. The application was built to solve the common problems of unverified claims, poor coordination between students and finders, and the lack of a secure, accountable process for returning lost property.

The system allows verified university users to report lost and found items, receive smart match suggestions, submit ownership claims, and complete item pickup through an official campus lost-and-found office. The project also includes an administrative review workflow and email-notification integration support.

## 3. Problem Statement

In a university environment, students frequently lose personal belongings such as bags, calculators, ID cards, gadgets, and books. Traditional lost-and-found systems are often informal, unstructured, and difficult to track. This creates several issues:

- Lost items are not reported in a consistent way.
- Found items are not easily discoverable by the rightful owner.
- False claims are difficult to identify.
- There is often no formal handover process.
- Accountability is weak because user identity is not strictly verified.

Smart Recover addresses these problems with a secure, role-based, university-specific workflow.

## 4. Objectives

The primary objectives of the project are:

- To create a digital lost-and-found platform for campus use.
- To restrict access to verified Bennett University email users.
- To maintain accountability by storing user identity information.
- To allow students to report lost and found items with detailed metadata.
- To automatically suggest possible matches between lost and found reports.
- To provide a claim-verification workflow before returning an item.
- To route approved handovers through the official lost-and-found office.
- To provide an admin interface for oversight and claim approval.
- To support email delivery workflows for user notifications.

## 5. Scope of the Project

The current version of Smart Recover supports:

- User authentication with Bennett University email validation
- Lost item submission
- Found item submission
- Matching suggestions based on simple similarity scoring
- Restricted access to shared found-item discovery
- Claim submission and claim tracking
- Official pickup token workflow after approval
- Admin claim review and suspicious-activity monitoring
- Delete functionality for user-owned lost and found reports
- Frontend navigation with separate page-style views for major user tasks

The system is currently suitable as a strong academic prototype and functional campus web application demo.

## 6. Technology Stack

### Frontend

- HTML5
- CSS3
- Vanilla JavaScript

### Backend

- Python 3
- `http.server` from the Python standard library

### Data Storage

- Local JSON storage through `data.json`
- Temporary fallback storage for Vercel deployment through `/tmp`

### Email Integration

- Gmail SMTP for local use
- Resend API integration for hosted deployment environments where SMTP is restricted

### Deployment Support

- Render
- Vercel

## 7. Project Structure

The core files in the project are:

- [index.html](C:\Users\Mehul\OneDrive\Documents\New%20project\index.html): Frontend markup and templates
- [styles.css](C:\Users\Mehul\OneDrive\Documents\New%20project\styles.css): UI design and responsive styling
- [app.js](C:\Users\Mehul\OneDrive\Documents\New%20project\app.js): Frontend logic, page rendering, navigation, and API interaction
- [app.py](C:\Users\Mehul\OneDrive\Documents\New%20project\app.py): Backend server, API handling, authentication, storage, matching, and notifications
- [data.json](C:\Users\Mehul\OneDrive\Documents\New%20project\data.json): Current project data store
- [api/index.py](C:\Users\Mehul\OneDrive\Documents\New%20project\api\index.py): Vercel serverless entrypoint
- [vercel.json](C:\Users\Mehul\OneDrive\Documents\New%20project\vercel.json): Vercel configuration
- [requirements.txt](C:\Users\Mehul\OneDrive\Documents\New%20project\requirements.txt): Python dependency descriptor
- [favicon.svg](C:\Users\Mehul\OneDrive\Documents\New%20project\favicon.svg): Site favicon
- [assets](C:\Users\Mehul\OneDrive\Documents\New%20project\assets): Home-page illustration assets

## 8. Functional Modules

### 8.1 User Authentication Module

The authentication system validates users based on Bennett University email addresses. It stores:

- Full name
- University email
- University ID
- Password hash

Only the designated admin account, `s24bcau0044@bennett.edu.in`, receives admin privileges.

Relevant backend methods:

- [app.py](C:\Users\Mehul\OneDrive\Documents\New%20project\app.py#L433): `handle_signup`
- [app.py](C:\Users\Mehul\OneDrive\Documents\New%20project\app.py#L455): `handle_login`

### 8.2 Lost Item Submission Module

Users can submit lost item reports containing:

- Item name
- Description
- Lost location
- Date and time
- Optional image

Relevant backend method:

- [app.py](C:\Users\Mehul\OneDrive\Documents\New%20project\app.py#L476): `handle_create_item`

Relevant frontend page:

- [app.js](C:\Users\Mehul\OneDrive\Documents\New%20project\app.js#L254): `renderLostForm`

### 8.3 Found Item Submission Module

Users can submit found item reports with similar fields. These reports may later be claimed by other users if ownership is verified.

Relevant frontend page:

- [app.js](C:\Users\Mehul\OneDrive\Documents\New%20project\app.js#L276): `renderFoundForm`

### 8.4 Restricted Discovery Access Module

To prevent misuse, the shared campus discoveries page is available only after a user has submitted at least one lost-item report. However, users can still manage the found items they themselves submitted.

This rule is enforced both in the frontend and in backend state shaping.

Relevant backend method:

- [app.py](C:\Users\Mehul\OneDrive\Documents\New%20project\app.py#L327): `public_state_for`

### 8.5 Matching Engine

The system compares lost and found reports using:

- item name similarity
- keyword overlap in descriptions
- location similarity

Possible matches are shown to users on a dedicated page.

Relevant frontend page:

- [app.js](C:\Users\Mehul\OneDrive\Documents\New%20project\app.js#L309): `renderHomePage`

### 8.6 Claim and Verification Module

Users can submit claims for found items by providing identifying proof. Admin reviews each claim before approval or rejection.

Relevant backend methods:

- [app.py](C:\Users\Mehul\OneDrive\Documents\New%20project\app.py#L527): `handle_create_claim`
- [app.py](C:\Users\Mehul\OneDrive\Documents\New%20project\app.py#L590): `handle_claim_action`

### 8.7 Official Pickup Workflow

Once a claim is approved:

- the system generates a pickup token
- the founder is instructed to deposit the item at the campus lost-and-found office
- the claimant receives collection instructions
- the claimant confirms collection after pickup

This workflow avoids direct finder-claimant contact and adds institutional control.

### 8.8 Admin Monitoring Module

The admin view includes:

- pending claim review
- suspicious-activity monitoring

Suspicious behavior is identified using simple heuristics such as high claim volume and repeated rejected claims.

### 8.9 Delete Item Module

Users can delete their own:

- lost item reports
- found item reports

When a found item is deleted, related claims are removed to keep data consistent.

Relevant backend method:

- [app.py](C:\Users\Mehul\OneDrive\Documents\New%20project\app.py#L561): `handle_delete_item`

## 9. User Interface Design

The interface is designed as a modern, card-based application with:

- a split-panel login page
- a visual home page with image-based navigation cards
- separate page-style views for each major workflow
- white and cyan visual theme for the main application
- mobile-responsive layouts

The home page acts as a navigation hub, allowing access to:

- Report Lost Item
- Report Found Item
- Campus Discoveries
- Your Lost Items
- Your Discoveries
- Suggested Matches
- Claims and Pickup
- Admin Panel

Relevant frontend renderer:

- [app.js](C:\Users\Mehul\OneDrive\Documents\New%20project\app.js#L563): `renderDashboard`

## 10. System Workflow

### User Workflow

1. User signs up using a Bennett University email.
2. User logs in and reaches the home page.
3. User submits a lost or found item.
4. The system stores the item and checks for possible matches.
5. If the item is found, the user submits a claim with proof.
6. Admin reviews and approves or rejects the claim.
7. If approved, the item is handed over through the official lost-and-found office.
8. The claimant uses a pickup token to collect the item.

### Admin Workflow

1. Admin logs in with the designated admin account.
2. Admin opens the Admin Panel.
3. Admin reviews pending claims.
4. Admin approves or rejects claims.
5. Admin monitors suspicious user behavior.

## 11. API and Backend Behavior

The backend is implemented as a lightweight Python service using request handlers rather than a full web framework. It exposes endpoints for:

- authentication
- state loading
- lost/found item creation
- claim creation
- claim actions
- item deletion
- demo data generation

This approach keeps the system dependency-light and easy to run in a small project environment.

## 12. Email Notification Strategy

The project includes email notification support for:

- lost item submission
- found item submission
- match detection
- claim approval
- claim rejection
- pickup readiness
- collection completion

The code currently supports two strategies:

- SMTP-based sending for local environments
- Resend API integration for hosted environments where SMTP ports are blocked

Relevant backend method:

- [app.py](C:\Users\Mehul\OneDrive\Documents\New%20project\app.py#L205): `send_email_if_configured`

## 13. Deployment Notes

### Local Execution

Run the application using:

```powershell
py app.py
```

Then open:

```text
http://127.0.0.1:8000
```

### Render Deployment

Render can host the Python backend as a web service. However:

- free instances spin down after inactivity
- SMTP is blocked on free instances
- Resend is a better email-delivery option for free hosting

### Vercel Deployment

The project also contains Vercel deployment support through:

- [api/index.py](C:\Users\Mehul\OneDrive\Documents\New%20project\api\index.py)
- [vercel.json](C:\Users\Mehul\OneDrive\Documents\New%20project\vercel.json)

However, because Vercel is serverless, the current JSON storage model is only temporary there and not production-safe.

## 14. Limitations

The current project has several limitations:

- `data.json` is not ideal for production persistence
- no relational database is currently used
- email delivery in hosted environments requires external provider setup
- image storage is inline/base64 rather than cloud-object storage
- sessions and file-based storage are suitable for a prototype, not large-scale production
- advanced search and AI-based matching are not yet implemented

## 15. Future Enhancements

Future versions of Smart Recover can include:

- PostgreSQL or MongoDB integration
- secure production-grade session management
- cloud image storage
- stronger claim-verification workflow
- OCR/AI-based item recognition
- admin analytics dashboard
- real-time notifications
- user profile management
- campus office inventory integration
- QR-code based pickup verification

## 16. Conclusion

Smart Recover is a practical and well-structured university lost-and-found system that combines identity verification, item reporting, automated matching, claim validation, and office-based handover into one platform. The project demonstrates both frontend and backend design, user-role handling, real workflow thinking, and deployment awareness.

As a prototype, it already covers the major functional requirements of a secure university lost-and-found application. With database integration and production-grade hosting improvements, Smart Recover can be extended into a fully deployable campus service.
