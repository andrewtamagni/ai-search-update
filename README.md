# ai-search-update

This script is designed to run in an Azure Runbook, leveraging Azure Automation Account variables for storing and retrieving necessary information. The script connects to a private GitHub repository that contains backups of HTML files from a Confluence Wiki. It searches for HTML files modified within the past specified number of days (defined by the `aiUpdate-fileAgeDays` variable in the Automation Account). The content of these files is then uploaded to an Azure Blob Storage container. Additionally, the script parses the HTML files to extract their last modified dates, facilitating updates to the Azure AI Search Index based on the new data.

## Prerequisites
Python 3.8

## Local Setup for Testing Instructions
1. Install packages in requirements.txt:
   ```bash
   pip install --requirement requirements.txt
   ```

## Azure Setup Instructions
1. Create an Azure Automation Account.
2. Add the required variables to the Automation Account under **Assets > Variables**:
   - `aiUpdate-gitToken`
   - `aiUpdate-gitRepo`
   - `aiUpdate-gitFolderPath`
   - `aiUpdate-fileAgeDays`
   - `aiUpdate-azBlobConnectStr`
   - `aiUpdate-azBlobContainer`
   - `aiUpdate-searchSvcEp`
   - `aiUpdate-searchSvcKey`
3. Assign the Automation Account's Managed Identity the **Contributor** role over the Resource Group containing the A.I. resources.
4. Download all required Python packages from the packages directory and upload them into the Runbook environment. Note: The `cryptography` package requires a Python 3.10 environment, while other packages should run in Python 3.8.
5. Create a Python 3.8 Runbook in the Automation Account.
6. Upload and save the script into the Runbook.
7. Test the Runbook to ensure variables are correctly accessed and the script functions as expected.
8. Publish the Runbook.
9. Configure a schedule to automatically run the Runbook.

## Setup Monitoring and Email Alert in Azure
1. Create or use an existing Log Analytics Workspace to publish the Automation Account logs.
2. In the Azure Automation Account settings under **Monitor**, select **Diagnostic Settings**.
3. Send all logs to the Log Analytics Workspace.
4. In the Log Analytics Workspace, create an alert rule to fire off an email action with the query below to check back an hour for failures:
   ```kql
   AzureDiagnostics 
   | where ResourceProvider == "MICROSOFT.AUTOMATION" 
   and Category == "JobLogs" 
   and (ResultType == "Failed" or ResultType == "Suspended") 
   | where TimeGenerated >= ago(24h)
   ```

---

## Third-Party Dependencies

This project uses the following third-party open-source libraries:

- **Azure SDKs** (MIT License) - Azure Identity, Key Vault, Search, and Storage Blob libraries
- **BeautifulSoup4** (MIT License) - HTML/XML parsing library
- **PyGithub** (LGPL-3.0 License) - GitHub API client library
- **requests** (Apache-2.0 License) - HTTP library for Python
- **cryptography** (Apache-2.0 License / BSD-3-Clause License) - Cryptographic library
- **PyJWT** (MIT License) - JSON Web Token implementation
- **PyNaCl** (Apache-2.0 License) - Python binding to the Networking and Cryptography library

All dependencies are listed in `requirements.txt`. Please refer to each library's license for specific terms and conditions. **Note:** Some dependencies may have different license terms - please review individual package licenses for compliance.