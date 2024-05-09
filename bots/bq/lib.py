from google.cloud import bigquery
import json
import pprint
from dotenv import load_dotenv

load_dotenv()

client = bigquery.Client.from_service_account_json(os.getenv("SERVICE_ACCOUNT_JSON"))


def can_run(query: str) -> bool:
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    query_job = client.query(
        query,
        job_config=job_config,
    )
    print("This query will process {} bytes.".format(query_job.total_bytes_processed))
    if query_job.total_bytes_processed > 2000000000:
        return False
    else:
        return True
def query(query: str):
    if can_run(query):
        pass
    else:
        raise Exception
    query_job = client.query(query)
    for row in query_job:
        records = [dict(row) for row in query_job]
        json_obj = json.dumps(str(records))
        return records
def list_datasets():
    datasets = list(client.list_datasets())  # Make an API request.
    project = client.project
    if datasets:
        print("Datasets in project {}:".format(project))
        for dataset in datasets:
            print("\t{}".format(dataset.dataset_id))
    else:
        print("{} project does not contain any datasets.".format(project))
