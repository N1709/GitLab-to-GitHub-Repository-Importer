#!/usr/bin/env python3

import os
import sys
import xml.etree.ElementTree as ET
import subprocess
import requests
from urllib.parse import urlparse
import time

class GitLabToGitHub:
    def __init__(self, github_token, gitlab_base_url="https://gitlab.com", organization=None):
        self.github_token = github_token
        self.gitlab_base_url = gitlab_base_url.rstrip('/')
        self.github_api = "https://api.github.com"
        self.organization = organization
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def parse_manifest(self, manifest_path):
        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()
            
            remotes = {}
            for remote in root.findall('remote'):
                name = remote.get('name')
                fetch = remote.get('fetch')
                remotes[name] = fetch
            
            projects = []
            for project in root.findall('project'):
                proj_info = {
                    'path': project.get('path'),
                    'name': project.get('name'),
                    'remote': project.get('remote', 'origin'),
                    'revision': project.get('revision', 'main')
                }
                
                if proj_info['remote'] in remotes:
                    base_url = remotes[proj_info['remote']]
                    if not base_url.startswith('http'):
                        base_url = self.gitlab_base_url
                    proj_info['gitlab_url'] = f"{base_url}/{proj_info['name']}.git"
                else:
                    proj_info['gitlab_url'] = f"{self.gitlab_base_url}/{proj_info['name']}.git"
                
                projects.append(proj_info)
            
            return projects
        except Exception as e:
            print(f"Error parsing manifest: {e}")
            return []
    
    def create_github_repo(self, repo_name, description="", private=False):
        if self.organization:
            url = f"{self.github_api}/orgs/{self.organization}/repos"
        else:
            url = f"{self.github_api}/user/repos"
        
        data = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": False
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 422:
            owner = self.organization if self.organization else "<username>"
            print(f"WARNING: Repository '{repo_name}' already exists")
            return {"full_name": f"{owner}/{repo_name}"}
        else:
            print(f"ERROR: Failed to create repo: {response.status_code} - {response.text}")
            return None
    
    def get_github_username(self):
        url = f"{self.github_api}/user"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()['login']
        return None
    
    def get_user_organizations(self):
        url = f"{self.github_api}/user/orgs"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return [org['login'] for org in response.json()]
        return []
    
    def import_repository(self, gitlab_url, github_repo_name, branch="main"):
        print(f"\nImporting: {gitlab_url}")
        print(f"   Target GitHub: {github_repo_name}")
        
        if self.organization:
            owner = self.organization
            print(f"   Target: Organization '{owner}'")
        else:
            owner = self.get_github_username()
            if not owner:
                print("ERROR: Failed to get GitHub username")
                return False
            print(f"   Target: User '{owner}'")
        
        repo_info = self.create_github_repo(github_repo_name)
        if not repo_info:
            return False
        
        github_url = f"https://{self.github_token}@github.com/{owner}/{github_repo_name}.git"
        
        temp_dir = f"/tmp/gitlab_import_{github_repo_name}"
        
        try:
            if os.path.exists(temp_dir):
                subprocess.run(["rm", "-rf", temp_dir], check=True)
            
            print(f"   Cloning from GitLab...")
            result = subprocess.run(
                ["git", "clone", "--mirror", gitlab_url, temp_dir],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"   ERROR: Clone failed: {result.stderr}")
                return False
            
            print(f"   Pushing to GitHub...")
            os.chdir(temp_dir)
            
            result = subprocess.run(
                ["git", "push", "--mirror", github_url],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"   ERROR: Push failed: {result.stderr}")
                return False
            
            print(f"   SUCCESS: Repository imported")
            
            os.chdir("/")
            subprocess.run(["rm", "-rf", temp_dir], check=True)
            
            return True
            
        except Exception as e:
            print(f"   ERROR: {e}")
            try:
                os.chdir("/")
                subprocess.run(["rm", "-rf", temp_dir], check=True)
            except:
                pass
            return False
    
    def extract_repo_name(self, project_name):
        parts = project_name.split('/')
        return parts[-1] if parts else project_name
    
    def process_manifest(self, manifest_path, prefix="", custom_names=None):
        print("GitLab to GitHub Importer")
        print("=" * 60)
        
        projects = self.parse_manifest(manifest_path)
        
        if not projects:
            print("ERROR: No projects found in manifest")
            return
        
        print(f"\nFound {len(projects)} projects to import")
        
        if self.organization:
            print(f"Target: Organization '{self.organization}'")
        else:
            username = self.get_github_username()
            print(f"Target: User '{username}'")
        
        print()
        
        print("Projects to be imported:")
        for i, proj in enumerate(projects, 1):
            repo_name = custom_names.get(proj['name'], self.extract_repo_name(proj['name'])) if custom_names else self.extract_repo_name(proj['name'])
            if prefix:
                repo_name = f"{prefix}{repo_name}"
            print(f"  {i}. {proj['name']} -> {repo_name}")
        
        print("\n" + "=" * 60)
        confirm = input("\nContinue with import? (y/n): ")
        
        if confirm.lower() != 'y':
            print("Import cancelled")
            return
        
        success_count = 0
        failed_count = 0
        
        for i, proj in enumerate(projects, 1):
            print(f"\n[{i}/{len(projects)}]")
            
            repo_name = custom_names.get(proj['name'], self.extract_repo_name(proj['name'])) if custom_names else self.extract_repo_name(proj['name'])
            if prefix:
                repo_name = f"{prefix}{repo_name}"
            
            if self.import_repository(proj['gitlab_url'], repo_name, proj['revision']):
                success_count += 1
            else:
                failed_count += 1
            
            if i < len(projects):
                time.sleep(2)
        
        print("\n" + "=" * 60)
        print("Import Summary:")
        print(f"   Successful: {success_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Total: {len(projects)}")
        print("=" * 60)


def select_target():
    print("\n" + "=" * 60)
    print("Select Import Target")
    print("=" * 60)
    print("\n1. Personal Account (User)")
    print("2. Organization")
    print()
    
    while True:
        choice = input("Select option (1 or 2): ").strip()
        
        if choice == "1":
            return None
        elif choice == "2":
            org_name = input("\nEnter organization name: ").strip()
            if org_name:
                return org_name
            else:
                print("ERROR: Organization name cannot be empty")
        else:
            print("ERROR: Invalid option. Please select 1 or 2.")


def main():
    print("""
============================================================
       GitLab to GitHub Repository Importer
       Support Import repositories via manifest.xml
============================================================
    """)
    
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not github_token:
        print("WARNING: GITHUB_TOKEN environment variable not set")
        github_token = input("Enter your GitHub Personal Access Token: ").strip()
    
    if not github_token:
        print("ERROR: GitHub token is required!")
        sys.exit(1)
    
    manifest_path = input("Enter path to manifest.xml (default: ./manifest.xml): ").strip()
    if not manifest_path:
        manifest_path = "./manifest.xml"
    
    if not os.path.exists(manifest_path):
        print(f"ERROR: Manifest file not found: {manifest_path}")
        sys.exit(1)
    
    organization = select_target()
    
    prefix = input("\nEnter prefix for GitHub repo names (optional, e.g., 'pixel-'): ").strip()
    
    gitlab_url = input("Enter GitLab base URL (default: https://gitlab.com): ").strip()
    if not gitlab_url:
        gitlab_url = "https://gitlab.com"
    
    importer = GitLabToGitHub(github_token, gitlab_url, organization)
    
    if organization:
        print(f"\nVerifying access to organization '{organization}'...")
        orgs = importer.get_user_organizations()
        if organization not in orgs:
            print(f"WARNING: You may not have access to organization '{organization}'")
            print(f"   Available organizations: {', '.join(orgs) if orgs else 'None'}")
            confirm = input("\n   Continue anyway? (y/n): ")
            if confirm.lower() != 'y':
                print("Import cancelled")
                sys.exit(0)
    
    importer.process_manifest(manifest_path, prefix)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nImport cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
