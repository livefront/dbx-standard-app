import argparse
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import BadRequest
from databricks.sdk.service.apps import ComputeState

parser = argparse.ArgumentParser()
parser.add_argument("--app-name", required=True)
args = parser.parse_args()

w = WorkspaceClient()  # picks up the job's run-as identity automatically

app = w.apps.get(args.app_name)
state = app.compute_status.state if app.compute_status else None
print(f"App {args.app_name} compute state: {state}")

if state != ComputeState.ACTIVE:
    print("App is not ACTIVE (already stopped/stopping/starting); nothing to do.")
else:
    print(f"Stopping app: {args.app_name}")
    try:
        w.apps.stop(args.app_name)
        print("Stop requested.")
    except BadRequest as e:
        # Race: it stopped between the check and the call
        if "STOPPED" in str(e):
            print("App already stopped; nothing to do.")
        else:
            raise