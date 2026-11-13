import argparse
from databricks.sdk import WorkspaceClient

parser = argparse.ArgumentParser()
parser.add_argument("--app-name", required=True)
args = parser.parse_args()

w = WorkspaceClient()   # picks up the job's run-as identity automatically
print(f"Stopping app: {args.app_name}")
w.apps.stop(args.app_name)
print("Stop requested.")