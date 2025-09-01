# NSOL Social Media Automation

This n8n workflow automates the daily generation of social media content ideas, stores them for review in Google Sheets, and generates images for approved posts.

## Prerequisites

Before you begin, ensure you have the following:
1.  **n8n Installed:** Either locally via npm (`npm install n8n -g`) or via Docker.
2.  **A Google Cloud Project** with the Google Sheets API, Google Drive API, and Generative Language API enabled.
3.  **Access** to the "NSOL CONTENT STRATEGY" Google Sheet.

## Setup Instructions

### 1. Get the Code
Clone this repository to your machine:
```bash
git clone <your-github-repository-url>
cd nsol-social-automation
