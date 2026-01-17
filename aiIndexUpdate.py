#!/usr/bin/env python3
"""
This script is designed to run in an Azure Runbook, leveraging Automation Account variables for storing and retrieving necessary
information to be used as variables. The script connects to a private GitHub repository that contains backups of HTML files from
a Confluence Wiki. It searches for HTML files modified within the past specified number of days (defined by the `aiUpdate-fileAgeDays`
variable in the Automation Account). The content of these files is then uploaded to an Azure Blob Storage container. Additionally,
the script parses the HTML files to extract their last modified dates, facilitating updates to the Azure AI Search Index based on the
new data.

The following secrets must be stored in an Azure Auotmation Runbook variables for this script to function correctly:

aiUpdate-gitToken
aiUpdate-gitRepo
aiUpdate-gitFolderPath
aiUpdate-fileAgeDays
aiUpdate-azBlobConnectStr
aiUpdate-azBlobContainer
aiUpdate-searchSvcEp
aiUpdate-searchSvcKey
"""
from azure.search.documents.indexes import SearchIndexerClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from github import Github
import automationassets
import time
import sys
import re

# Fetch the updated .html files from GitHub
def fetch_recent_html_files(token, repo_name, folder_paths, days):
	try:
		g = Github(token)
		repo = g.get_repo(repo_name)
		recent_html_files = []
		threshold_date = (datetime.now() - timedelta(days=days)).date()

		for folder_path in folder_paths:
			contents = repo.get_contents(folder_path)
			for content in contents:
				if content.type == 'file' and content.path.endswith('.html'):
					file_content = content.decoded_content.decode('utf-8')
					last_modified_date = extract_last_modified_date(file_content)

					# Check if the file has a last modified date and it is within the threshold date
					if last_modified_date and last_modified_date >= threshold_date:
						recent_html_files.append(content)
		return recent_html_files

	except Exception as e:
		print(f'ERROR : Failed to fetch recent HTML files: {e}')
		sys.exit(1)

# Extract the last modified date from the .html content
def extract_last_modified_date(html_content):
	try:
		soup = BeautifulSoup(html_content, 'html.parser')
		metadata_div = soup.find('div', class_='page-metadata')				
		if metadata_div:
			match = re.search(r'last modified (?:by.*? )?on (\w+ \d{1,2}, \d{4})', metadata_div.get_text())
			if match:
				last_modified_date = datetime.strptime(match.group(1), '%b %d, %Y')
				return last_modified_date.date()
			   
			# If no modified date, try to find the created date
			match_created = re.search(r'Created by.*?on (\w+ \d{1,2}, \d{4})', metadata_div.get_text())
			if match_created:
				created_date = datetime.strptime(match_created.group(1), '%b %d, %Y')
				return created_date.date()    
		return None
	
	except Exception as e:
		print(f"WARNING : Failed to extract last modified date: {e}")
		return None

def fetch_file_content(file):
	data = file.decoded_content.decode('utf-8')
	return data

def update_blob_storage(file_content, connection_string, container_name, blob_name):
	try:
		blob_service_client = BlobServiceClient.from_connection_string(connection_string)
		blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
				
		# Check if the blob already exists and update it
		if blob_client.exists():
			blob_client.upload_blob(file_content, overwrite=True)
			print(f'INFO : Blob {blob_name} updated successfully in container {container_name}.')
		else:
			blob_client.upload_blob(file_content)
			print(f'INFO : Blob {blob_name} created successfully in container {container_name}.')

	except Exception as e:
		print(f'ERROR : Failed to update blob {blob_name}: {e}')
		sys.exit(1)

def run_indexers(search_service_endpoint, search_service_key):
    try:
        search_client = SearchIndexerClient(endpoint=search_service_endpoint, credential=AzureKeyCredential(search_service_key))
        
        # List indexers
        indexers = search_client.get_indexers()

        # Separate chunk indexers from regular indexers
        regular_indexers = [indexer for indexer in indexers if not indexer.name.endswith('-chunk')]
        chunk_indexers = [indexer for indexer in indexers if indexer.name.endswith('-chunk')]

        # Run regular indexers first
        for indexer in regular_indexers:
            time.sleep(10)  # Add a 10-second delay before each indexer kicks off
            search_client.run_indexer(indexer.name)
            print(f'INFO : Regular indexer {indexer.name} kicked off successfully.')

        # Run chunk indexers last
        for indexer in chunk_indexers:
            time.sleep(10)  # Add a 10-second delay before each indexer kicks off
            search_client.run_indexer(indexer.name)
            print(f'INFO : Chunk indexer {indexer.name} kicked off successfully.')

    except Exception as e:
        print(f'ERROR : Failed to run indexers: {e}')
        sys.exit(1)

def main():
	try:
		github_token = automationassets.get_automation_variable("aiUpdate-gitToken")
		github_repo_name = automationassets.get_automation_variable("aiUpdate-gitRepo")
		github_folder_paths = automationassets.get_automation_variable("aiUpdate-gitFolderPath").split(",") #Supports multiple folder paths in the same repo
		days = int(automationassets.get_automation_variable("aiUpdate-fileAgeDays"))
		azure_blob_connection_string = automationassets.get_automation_variable("aiUpdate-azBlobConnectStr")
		azure_blob_container_name = automationassets.get_automation_variable("aiUpdate-azBlobContainer")
		search_service_endpoint = automationassets.get_automation_variable("aiUpdate-searchSvcEp")
		search_service_key = automationassets.get_automation_variable("aiUpdate-searchSvcKey")

	except KeyError as e:
		print(f"ERROR : Missing environment variable: {e}")
		sys.exit(1)
	except ValueError as e:
		print(f"ERROR : Invalid value for environment variable: {e}")
		sys.exit(1)

	# Fetch recent HTML files from GitHub
	recent_html_files = fetch_recent_html_files(github_token, github_repo_name, github_folder_paths, days)

	if not recent_html_files:
		print(f"INFO : No recent HTML files found.")
	
	else:
		for file in recent_html_files:
			# Fetch file content
			file_content = fetch_file_content(file)

			# Use the file name, strip the path
			file_name = file.path.split('/')[-1]

			# Update blob storage
			update_blob_storage(file_content, azure_blob_connection_string, azure_blob_container_name, file_name)
			time.sleep(20)

		# Run indexers
		run_indexers(search_service_endpoint, search_service_key)

	print(f"SUCCESS : Script completed")
	sys.exit(0)

if __name__ == "__main__":
	main()