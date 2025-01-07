import os
import dlt
import tempfile
import csv
import gzip
from copy import deepcopy
from typing import Optional
from datetime import datetime

import requests

from dlt.common.typing import TDataItem
from dlt.sources import DltResource
from typing import List, Iterable, Sequence
from .client import AppStoreConnectClient
from .models import AnalyticsReportInstancesResponse

@dlt.source
def app_store(
    key_id: str,
    key_path: str,
    issuer_id: str,
    app_ids: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Sequence[DltResource]:
    key = None
    with open(key_path) as f: key = f.read()
    client = AppStoreConnectClient(
        key.encode(),
        key_id,
        issuer_id
    )

    return [
        app_downloads_detailed(client, app_ids, start_date, end_date),
        app_store_discovery_and_engagement_detailed(client, app_ids, start_date, end_date),
        app_sessions_detailed(client, app_ids, start_date, end_date),
        app_store_installation_and_deletion_detailed(client, app_ids, start_date, end_date),
        app_store_purchases_detailed(client, app_ids, start_date, end_date)
    ]

def filter_instances_by_date(
        instances: AnalyticsReportInstancesResponse,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
) -> AnalyticsReportInstancesResponse:
    instances = deepcopy(instances)
    if start_date is not None:
        instances.data = list(filter(lambda x: datetime.fromisoformat(x.attributes.processingDate) >= start_date, instances.data))
    if end_date is not None:
        instances.data = list(filter(lambda x: datetime.fromisoformat(x.attributes.processingDate) <= end_date, instances.data))

    return instances

def get_analytics_report(
        client: AppStoreConnectClient,
        app_id: str,
        report_name: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
) -> Iterable[TDataItem]:
    report_requests = client.list_analytics_report_requests(app_id)
    ongoing_requests = list(filter(lambda x: x.attributes.accessType == "ONGOING" , report_requests.data))

    # todo: validate report is not stopped due to inactivity
    if len(ongoing_requests) == 0:
        raise Exception("No ONGOING report requests found")

    reports = client.list_analytics_reports(ongoing_requests[0].id, report_name)
    if len(reports.data) == 0:
        raise Exception(f"No such report found: {report_name}")

    for report in reports.data:
        instances = client.list_report_instances(report.id)

        instances = filter_instances_by_date(instances, start_date, end_date)

        if len(instances.data) == 0:
            raise Exception("No report instances found for the given date range")

        for instance in instances.data:
            segments = client.list_report_segments(instance.id)
            with tempfile.TemporaryDirectory() as temp_dir:
                files = []
                for segment in segments.data:
                    payload = requests.get(segment.attributes.url, stream=True)
                    payload.raise_for_status()

                    csv_path = os.path.join(temp_dir, f"{segment.attributes.checksum}.csv")
                    with open(csv_path, "wb") as f:
                        for chunk in payload.iter_content(chunk_size=8192):
                            f.write(chunk)
                    files.append(csv_path)
                for file in files:
                    with gzip.open(file, "rt") as f:
                        reader = csv.DictReader(f, delimiter="\t")
                        for row in reader:
                            yield {"processing_date": instance.attributes.processingDate, **row}

PRIMARY_KEY_APP_DOWNLOADS_DETAILED = [
    "app_apple_identifier",
    "app_name",
    "app_version",
    "campaign",
    "date",
    "device",
    "download_type",
    "page_title",
    "page_type",
    "platform_version",
    "pre_order",
    "processing_date",
    "source_info",
    "source_type",
    "territory",
]

COLUMN_HINTS_APP_DOWNLOADS_DETAILED = {
    "date": {
        "data_type": "date",
    },
    "app_apple_identifier": {
        "data_type": "bigint",
    },
    "counts": {
        "data_type": "bigint",
    },
    "processing_date": {
        "data_type": "date",
    }
}


@dlt.resource(
    name="app-downloads-detailed", 
    primary_key=PRIMARY_KEY_APP_DOWNLOADS_DETAILED,
    columns=COLUMN_HINTS_APP_DOWNLOADS_DETAILED,
)
def app_downloads_detailed(
    client: AppStoreConnectClient,
    app_ids: List[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime]
) -> Iterable[TDataItem]:

    for app_id in app_ids:
        yield from get_analytics_report(client, app_id, "App Downloads Detailed", start_date, end_date)

PRIMARY_KEY_APP_STORE_DISCOVERY_AND_ENGAGEMENT_DETAILED = [
    "app_apple_identifier",
    "app_name",
    "campaign",
    "date",
    "device",
    "engagement_type",
    "event",
    "page_title",
    "page_type",
    "platform_version",
    "processing_date",
    "source_info",
    "source_type",
    "territory",
]

COLUMN_HINTS_APPS_STORE_DISCOVERY_AND_ENGAGEMENT_DETAILED = {
    "date": {
        "data_type": "date",
    },
    "app_apple_identifier": {
        "data_type": "bigint",
    },
    "counts": {
        "data_type": "bigint",
    },
    "unique_counts": {
        "data_type": "bigint",
    },
    "processing_date": {
        "data_type": "date",
    }
}

@dlt.resource(
    name="app-store-discovery-and-engagement-detailed",
    primary_key=PRIMARY_KEY_APP_STORE_DISCOVERY_AND_ENGAGEMENT_DETAILED,
    columns=COLUMN_HINTS_APPS_STORE_DISCOVERY_AND_ENGAGEMENT_DETAILED,
)
def app_store_discovery_and_engagement_detailed(
    client: AppStoreConnectClient,
    app_ids: List[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime]
) -> Iterable[TDataItem]:
    for app_id in app_ids:
        yield from get_analytics_report(client, app_id, "App Store Discovery and Engagement Detailed", start_date, end_date)

PRIMARY_KEY_APP_SESSIONS_DETAILED = [
    "processing_date",
    "date",
    "app_name",
    "app_apple_identifier",
    "app_version",
    "device",
    "platform_version",
    "source_type",
    "source_info",
    "campaign",
    "page_type",
    "page_title",
    "app_download_date",
    "territory",
]

COLUMN_HINTS_APP_SESSIONS_DETAILED = {
    "date": {
        "data_type": "date",
    },
    "app_apple_identifier": {
        "data_type": "bigint",
    },
    "sessions": {
        "data_type": "bigint",
    },
    "total_session_duration": {
        "data_type": "bigint",
    },
    "unique_devices": {
        "data_type": "bigint",
    },
    "processing_date": {
        "data_type": "date",
    }
}
@dlt.resource(
    name="app-sessions-detailed",
    primary_key=PRIMARY_KEY_APP_SESSIONS_DETAILED,
    columns=COLUMN_HINTS_APP_SESSIONS_DETAILED
)
def app_sessions_detailed(
    client: AppStoreConnectClient,
    app_ids: List[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime]
) -> Iterable[TDataItem]:
    for app_id in app_ids:
        yield from get_analytics_report(client, app_id, "App Sessions Detailed", start_date, end_date)

PRIMARY_KEY_APP_STORE_INSTALLATION_AND_DELETION_DETAILED = [
    "app_apple_identifier",
    "app_download_date",
    "app_name",
    "app_version",
    "campaign",
    "counts",
    "date",
    "device",
    "download_type",
    "event",
    "page_title",
    "page_type",
    "platform_version",
    "processing_date",
    "source_info",
    "source_type",
    "territory",
    "unique_devices",
]

COLUMN_HINTS_APP_STORE_INSTALLATION_AND_DELETION_DETAILED = {
    "date": {
        "data_type": "date",
    },
    "app_apple_identifier": {
        "data_type": "bigint",
    },
    "counts": {
        "data_type": "bigint",
    },
    "unique_devices": {
        "data_type": "bigint",
    },
    "app_download_date": {
        "data_type": "date",
    },
    "processing_date": {
        "data_type": "date",
    }
}

@dlt.resource(
    name="app-store-installation-and-deletion-detailed",
    primary_key=PRIMARY_KEY_APP_STORE_INSTALLATION_AND_DELETION_DETAILED,
    columns=COLUMN_HINTS_APP_STORE_INSTALLATION_AND_DELETION_DETAILED
)
def app_store_installation_and_deletion_detailed(
    client: AppStoreConnectClient,
    app_ids: List[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime]
) -> Iterable[TDataItem]:
    for app_id in app_ids:
        yield from get_analytics_report(client, app_id, "App Store Installation and Deletion Detailed", start_date, end_date)

PRIMARY_KEY_APP_STORE_PURCHASES_DETAILED = [
    "app_apple_identifier",
    "app_download_date",
    "app_name",
    "campaign",
    "content_apple_identifier",
    "content_name",
    "date",
    "device",
    "page_title",
    "page_type",
    "payment_method",
    "platform_version",
    "pre_order",
    "processing_date",
    "purchase_type",
    "source_info",
    "source_type",
    "territory",
]
COLUMN_HINTS_APP_STORE_PURCHASES_DETAILED = {
    "date": {
        "data_type": "date",
    },
    "app_apple_identifier": {
        "data_type": "bigint",
    },
    "app_download_date": {
        "data_type": "date",
    },
    "content_apple_identifier": {
        "data_type": "bigint",
    },
    "purchases": {
        "data_type": "bigint",
    },
    "proceeds_in_usd": {
        "data_type": "float",
    },
    "sales_in_usd": {
        "data_type": "float",
    },
    "paying_users": {
        "data_type": "bigint",
    },
    "processing_date": {
        "data_type": "date",
    }
}

@dlt.resource(
    name="app-store-purchases-detailed",
    primary_key=PRIMARY_KEY_APP_STORE_PURCHASES_DETAILED,
    columns=COLUMN_HINTS_APP_STORE_PURCHASES_DETAILED
)
def app_store_purchases_detailed(
    client: AppStoreConnectClient,
    app_ids: List[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime]
) -> Iterable[TDataItem]:
    for app_id in app_ids:
        yield from get_analytics_report(client, app_id, "App Store Purchases Detailed", start_date, end_date)