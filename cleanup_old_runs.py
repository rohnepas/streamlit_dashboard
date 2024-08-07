import requests
import os

def get_workflow_id(repo, token, workflow_name):
    url = f"https://api.github.com/repos/{repo}/actions/workflows"
    headers = {'Authorization': f'token {token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    workflows = response.json()['workflows']
    for workflow in workflows:
        if workflow['name'] == workflow_name:
            return workflow['id']
    raise ValueError(f"Workflow {workflow_name} not found")

def get_workflow_runs(repo, token, workflow_id):
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/runs"
    headers = {'Authorization': f'token {token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['workflow_runs']

def delete_run(repo, token, run_id):
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    headers = {'Authorization': f'token {token}'}
    response = requests.delete(url, headers=headers)
    response.raise_for_status()

def main():
    repo = os.getenv('GITHUB_REPOSITORY')
    token = os.getenv('PERSONAL_ACCESS_TOKEN')  # Use the new secret name
    workflow_name = "Run scheduler script"
    keep_runs = 3

    workflow_id = get_workflow_id(repo, token, workflow_name)
    runs = get_workflow_runs(repo, token, workflow_id)
    for run in runs[keep_runs:]:
        delete_run(repo, token, run['id'])

if __name__ == "__main__":
    main()
