import requests
import json
from datetime import datetime, timezone
from config import MOOGSOFT_API_KEY

INCIDENTS_API_URL = "https://api.moogsoft.ai/v1/incidents"

def epoch_to_moogsoft_format(epoch_time: int) -> str:
    """
    Convert epoch seconds to Moogsoft time format: YYYY-MM-DD HH:MM:SS
    """
    return datetime.fromtimestamp(epoch_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def fetch_incidents_since(start_epoch: int) -> list:
    """
    Fetch all incidents from Moogsoft API starting from start_epoch (filter by created_at).
    Handles pagination until no results are returned.
    """
    incidents = []
    headers = {
        "apikey": MOOGSOFT_API_KEY,
        "Content-Type": "application/json"
    }

    # Properly format dateFrom with string interpolation
    date_from_str = epoch_to_moogsoft_format(start_epoch)

    payload = {
        "filter": {
            "created_at": {
                "filterType": "combined",
                "operator": "AND",
                "condition1": {
                    "dateFrom": "1970-01-01 05:30:00",
                    "dateTo": None,
                    "filterType": "date",
                    "type": "greaterThan"
                },
                "condition2": {
                    "filterType": "combined",
                    "operator": "AND",
                    "condition1": {
                        "filterType": "date",
                        "type": "greaterThanOrEqual",
                        "dateFrom": date_from_str,
                        "dateTo": None
                    }
                }
            }
        },
        "limit": 5000,
        "fields": [
            "created_at",
            "tags",
            "manager"
        ]
    }

    while True:
        response = requests.post(INCIDENTS_API_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        data = response.json()

        results = data.get("data", {}).get("result", [])
        if not results:
            break

        incidents.extend(results)

        search_after = data.get("data", {}).get("search_after")
        if not search_after:
            break

        payload["search_after"] = search_after

    return incidents

def aggregate_incidents(this_month_epoch: int, last_24h_epoch: int) -> dict:
    """
    Aggregate incident data for given time ranges, return detailed statistics as per specs.
    """
    month_incidents = fetch_incidents_since(this_month_epoch)
    day_incidents = fetch_incidents_since(last_24h_epoch)

    def summarize(incidents_list):
        summary = {
            "total_count": 0,
            "sn_inc_created": 0,   # incidents with tags.SNOWInc not blank
            "sn_creation_errors": 0, # tags.SNOWIncidentCreated == "error"
            "priority_upgraded": 0,  # tags.upgraded not blank
            "auto_resolved": 0,      # tags.auto_close not blank
            "not_created_sn": 0,     # tags.SNOWInc is blank

            "per_manager": {},

            # Undiscovered workloads (Dynatrace manager + cmdb_ci blank + Workload not blank)
            "undiscovered_workloads": [],

            # Remaining alerts with cmdb_ci blank & Workload blank
            "cmdb_ci_blank_workload_blank": {
                "count": 0,
                "source_tags": set(),  # tags.source collected if available
                "no_workload_no_source_count": 0
            },

            # Splunk alerts (manager contains "Splunk", cmdb_ci blank, collect tags.Workload)
            "splunk_workloads": []
        }

        for incident in incidents_list:
            summary["total_count"] += 1

            manager = incident.get("manager") or "Unknown"
            tags = incident.get("tags") or {}

            # Helper vars for tag presence and blank check (None or empty string counts as blank)
            def is_blank(val):
                return val is None or (isinstance(val, str) and val.strip() == "")

            sn_inc = tags.get("SNOWInc")
            sn_inc_created_error = tags.get("SNOWIncidentCreated")
            upgraded = tags.get("upgraded")
            auto_close = tags.get("auto_close")
            cmdb_ci = tags.get("cmdb_ci")
            workload = tags.get("Workload")
            source = tags.get("source")

            # Count incidents with ServiceNow ticket created (SNOWInc not blank)
            if not is_blank(sn_inc):
                summary["sn_inc_created"] += 1
            else:
                summary["not_created_sn"] += 1

            # Incident creation errors
            if sn_inc_created_error == "error":
                summary["sn_creation_errors"] += 1

            # Priority auto upgraded
            if not is_blank(upgraded):
                summary["priority_upgraded"] += 1

            # Auto resolved by Moogsoft
            if not is_blank(auto_close):
                summary["auto_resolved"] += 1

            # Per manager aggregates (similar counters)
            mgr_data = summary["per_manager"].setdefault(manager, {
                "total_count": 0,
                "sn_inc_created": 0,
                "sn_creation_errors": 0,
                "priority_upgraded": 0,
                "auto_resolved": 0,
                "not_created_sn": 0,
            })
            mgr_data["total_count"] += 1
            if not is_blank(sn_inc):
                mgr_data["sn_inc_created"] += 1
            else:
                mgr_data["not_created_sn"] += 1
            if sn_inc_created_error == "error":
                mgr_data["sn_creation_errors"] += 1
            if not is_blank(upgraded):
                mgr_data["priority_upgraded"] += 1
            if not is_blank(auto_close):
                mgr_data["auto_resolved"] += 1

            # Undiscovered workloads: manager Dynatrace, cmdb_ci blank, Workload not blank
            if manager == "Dynatrace" and is_blank(cmdb_ci) and not is_blank(workload):
                summary["undiscovered_workloads"].append(workload)

            # Remaining alerts where cmdb_ci is blank and workload blank
            if is_blank(cmdb_ci) and is_blank(workload):
                # Check for source tag
                if not is_blank(source):
                    summary["cmdb_ci_blank_workload_blank"]["source_tags"].add(source)
                else:
                    summary["cmdb_ci_blank_workload_blank"]["no_workload_no_source_count"] += 1
                summary["cmdb_ci_blank_workload_blank"]["count"] += 1

            # Splunk alerts: manager contains "Splunk", cmdb_ci blank, collect workload list
            if "Splunk" in manager and is_blank(cmdb_ci) and not is_blank(workload):
                summary["splunk_workloads"].append(workload)

        # Convert source_tags set to list for JSON serializability
        summary["cmdb_ci_blank_workload_blank"]["source_tags"] = list(summary["cmdb_ci_blank_workload_blank"]["source_tags"])

        return summary

    month_summary = summarize(month_incidents)
    day_summary = summarize(day_incidents)

    result = {
        "this_month": month_summary,
        "last_24h": day_summary
    }

    # Recursive helper to convert all sets in the result dict to lists (for JSON serialization)
    def convert_sets_to_lists(obj):
        if isinstance(obj, dict):
            return {k: convert_sets_to_lists(v) for k, v in obj.items()}
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, list):
            return [convert_sets_to_lists(i) for i in obj]
        else:
            return obj

    return convert_sets_to_lists(result)
