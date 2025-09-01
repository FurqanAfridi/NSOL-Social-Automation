# NSOL Social Media Automation Task

## Objective
This n8n workflow automates the daily creation of social media content. It generates 5 post ideas using Google's Gemini AI, stores them in a Google Sheet for review, generates images for approved posts, and prepares them for publishing.

## Prerequisites for the Evaluator
To execute this workflow, you will need:
1.  **A running n8n instance.** The easiest way is to use the local desktop app: [Download n8n Desktop](https://n8n.io/get-started/)
2.  **A Google Cloud Project** with billing enabled (Gemini API requires it).
3.  **A Google Sheet** to serve as the database. You can create a blank one; the workflow will use it.

## Part 1: Google Cloud & API Setup

### Step 1: Create a Google Cloud Project & Enable APIs
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project (e.g., `n8n-nsol-task`).
3.  Enable the following APIs for your project:
    *   **Google Sheets API**
    *   **Google Drive API**
    *   **Generative Language API** (this provides access to Gemini)

### Step 2: Create OAuth 2.0 Credentials (for Sheets & Drive)
1.  In your Google Cloud Console, navigate to **APIs & Services > Credentials**.
2.  Click **Create Credentials** and select **OAuth client ID**.
3.  Set the **Application type** to **Desktop application**.
4.  Give it a name (e.g., `n8n Desktop Client`) and click **Create**.
5.  **Important:** Note down your **Client ID** and **Client Secret**. You will need them in Part 3.

### Step 3: Create an API Key (for Gemini)
1.  In the same **Credentials** section, click **Create Credentials** and select **API key**.
2.  Restrict this key to only the **Generative Language API** for security.
3.  Note down this **API Key**.

### Step 4: Prepare Your Google Sheet
1.  Create a new Google Sheet.
2.  Note its **Sheet ID** from the URL: `https://docs.google.com/spreadsheets/d/[THIS_IS_THE_SHEET_ID]/edit...`
3.  Share this Google Sheet with the **client email** found in your Google Cloud Console under **IAM & Admin > Service Accounts**. This grants your n8n application write access to the sheet.

## Part 2: Import the Workflow into n8n

1.  **Open your n8n desktop application.**
2.  Go to the **Workflows** tab.
3.  Click the **Import** button and upload the provided `workflow.json` file.

## Part 3: Configure Credentials in n8n

The imported workflow has nodes missing credentials. You need to create them.

### 1. Google Sheets & Drive Credential
*   In n8n, go to **Credentials > New Credential**.
*   Search for and select **Google Sheets OAuth2 API**.
*   **Name:** `My Google Auth`
*   **Client ID:** *[Paste the Client ID from Step 2.5]*
*   **Client Secret:** *[Paste the Client Secret from Step 2.5]*
*   Click **Save**. A pop-up will appear to complete the OAuth flow with Google. Authenticate with the account you used to create the Cloud project.
*   **Repeat this process** to create a credential for **Google Drive OAuth2 API**, using the same Client ID and Secret.

### 2. Google Gemini Credential
*   In n8n, go to **Credentials > New Credential**.
*   Search for and select **Google Gemini(PaLM) API**.
*   **Name:** `My Gemini Key`
*   **API Key:** *[Paste the API Key from Step 3]*
*   Click **Save**.

### 3. Connect Credentials to the Workflow
*   Go back to your imported workflow.
*   Click on the node named **"Save to Ideas & Drafts"**.
*   In its parameters, under **Credentials**, select your `My Google Auth` credential.
*   **Repeat this** for the **"Update Image Link"**, **"Check Approval Status"**, and **"Upload images to drive"** nodes.
*   Click on the **"Message a model"** and **"Generate an image"** nodes and select your `My Gemini Key` credential.

## Part 4: Configure the Workflow

One final step is needed to tell the workflow which Google Sheet to use.

1.  In the workflow, click on the **"Save to Ideas & Drafts"** node.
2.  In its parameters, you will see **Document ID**. Click on the field and change the mode from *List* to *Expression*.
3.  In the expression editor that appears, paste the following, replacing `YOUR_SHEET_ID_HERE` with the actual ID of your Google Sheet from Step 4.2:
    ```
   ={{ "YOUR_SHEET_ID_HERE" }}
    ```
    *Example: `={{ "1abc123def456ghi" }}`*
4.  Click **Execute Node** to test. This should add a new row to your Google Sheet.
5.  **Repeat Step 3** for the **"Update Image Link"** and **"Check Approval Status"** nodes.

## Execution & Validation

1.  **Activate the workflow** by flipping the toggle switch at the top right of the editor.
2.  To test immediately without waiting for 9 AM, click the **Execute Workflow** button.
3.  **Check for Success:**
    *   Look at the **"Save to Ideas & Drafts"** node. It should have a green checkmark.
    *   Check your Google Sheet. The **"Ideas & Drafts"** tab should now have 5 new rows of post ideas with the status "Waiting for Review".
    *   Manually change the status of one post to **"Approved"** in the sheet.
    *   Execute the workflow again. You should see the **"Generate an image"** node activate, and the **"Update Image Link"** node should add a Google Drive link to the approved post in the sheet.

## Summary of Deliverables
- [ ] **Google Cloud Project** with Sheets, Drive, and Gemini APIs enabled.
- [ ] **OAuth Client ID & Secret** and an **API Key** created.
- [ ] **Workflow** imported into n8n.
- [ ] **Credentials** created and connected in n8n.
- [ ] **Google Sheet ID** configured in the workflow nodes.
- [ ] **Workflow executed successfully**, generating ideas and an image for an approved post.

This demonstrates a fully functional automation pipeline for social media content creation.
