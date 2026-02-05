# GitLab to GitHub Repository Importer

A Python script to import repositories from GitLab to GitHub using manifest.xml file.

## Features

- Import multiple repositories from GitLab to GitHub
- Support for manifest.xml parsing
- Import to personal account or organization
- Optional prefix for repository names
- Custom GitLab base URL support
- Automatic repository creation on GitHub
- Mirror clone (all branches and tags)

## Requirements

- Python 3.6+
- Git
- requests library

## Installation

```bash
pip install requests
```

## Usage

### Basic Usage

```bash
python gitlab_to_github_importer.py
```

### Environment Variables

Set GitHub token as environment variable:

```bash
export GITHUB_TOKEN="your_github_token_here"
```

### Interactive Mode

The script will prompt you for:

1. GitHub Personal Access Token (if not set in environment)
2. Path to manifest.xml file
3. Target (Personal Account or Organization)
4. Optional prefix for repository names
5. GitLab base URL (default: https://gitlab.com)

### Example manifest.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<manifest>
  <remote name="origin" fetch="https://gitlab.com" />
  
  <project path="project1" name="group/project1" remote="origin" revision="main" />
  <project path="project2" name="group/project2" remote="origin" revision="master" />
</manifest>
```

## GitHub Token Permissions

Your GitHub Personal Access Token needs the following scopes:

- `repo` (full control of private repositories)
- `admin:org` (if importing to organization)

## How It Works

1. Parses manifest.xml to extract repository information
2. Creates repositories on GitHub (personal or organization)
3. Clones repositories from GitLab using --mirror flag
4. Pushes all branches and tags to GitHub
5. Cleans up temporary files

## Example Session

```
============================================================
       GitLab to GitHub Repository Importer
       Support Import repositories via manifest.xml
============================================================

Enter path to manifest.xml (default: ./manifest.xml): 
Select Import Target
1. Personal Account (User)
2. Organization
Select option (1 or 2): 1
Enter prefix for GitHub repo names (optional, e.g., 'pixel-'): 
Enter GitLab base URL (default: https://gitlab.com): 

Found 5 projects to import
Target: User 'username'

Projects to be imported:
  1. group/project1 -> project1
  2. group/project2 -> project2

Continue with import? (y/n): y
```

## Error Handling

The script handles:

- Missing manifest files
- Repository creation failures
- Clone failures
- Push failures
- Network errors
- Rate limiting (2 second delay between imports)

## Notes

- Existing repositories on GitHub will be skipped with a warning
- All branches and tags are imported
- Repository history is preserved
- Large repositories may take time to import

## License

MIT
