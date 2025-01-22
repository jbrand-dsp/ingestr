"""
Preliminary implementation of Google Ads pipeline.
"""

from typing import Iterator, List, Optional
from datetime import datetime

import dlt
from dlt.common.exceptions import MissingDependencyException
from dlt.common.typing import TDataItem
from dlt.sources import DltResource
from googleapiclient.discovery import Resource  # type: ignore

from .helpers.data_processing import to_dict

from .predicates import date_predicate

try:
    from google.ads.googleads.client import GoogleAdsClient  # type: ignore
except ImportError:
    raise MissingDependencyException("Requests-OAuthlib", ["google-ads"])


@dlt.source(max_table_nesting=2)
def google_ads(
    client: GoogleAdsClient,
    customer_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[DltResource]:
    return [
        asset_report_daily(client=client, customer_id=customer_id, start_date=start_date, end_date=end_date),
        ad_report_daily(client=client, customer_id=customer_id, start_date=start_date, end_date=end_date),
    ]

@dlt.resource
def asset_report_daily(
    client: Resource,
    customer_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Iterator[TDataItem]:

    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT 
            metrics.clicks, 
            metrics.conversions, 
            metrics.conversions_value, 
            metrics.cost_micros, 
            metrics.impressions, 
            campaign.id, 
            campaign.name, 
            customer.id, 
            ad_group.id, 
            ad_group.name, 
            asset.id,
            segments.date
        FROM 
            ad_group_ad_asset_view 
        WHERE 
            {date_predicate("segments.date", start_date, end_date)}
    """
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            yield  {
                "clicks": row.metrics.clicks,
                "conversions": row.metrics.conversions,
                "conversions_value": row.metrics.conversions_value,
                "cost_micros": row.metrics.cost_micros,
                "impressions": row.metrics.impressions,
                "campaign_id": row.campaign.id,
                "campaign_name": row.campaign.name,
                "customer_id": row.customer.id,
                "ad_group_id": row.ad_group.id,
                "ad_group_name": row.ad_group.name,
                "asset_id": row.asset.id,
                "date": row.segments.date
            }

@dlt.resource
def ad_report_daily(
    client: Resource,
    customer_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Iterator[TDataItem]:

    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value,
            metrics.impressions,
            metrics.cost_micros,
            metrics.video_quartile_p25_rate,
            metrics.video_quartile_p50_rate,
            metrics.video_quartile_p75_rate,
            metrics.video_quartile_p100_rate,
            customer.id,
            campaign.id,
            campaign.name,
            ad_group.id,
            ad_group.name,
            ad_group.status,
            ad_group_ad.ad.id,
            segments.date
        FROM
            ad_group_ad
        WHERE
            {date_predicate("segments.date", start_date, end_date)}
    """
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            yield  {
                "clicks": row.metrics.clicks,
                "conversions": row.metrics.conversions,
                "conversions_value": row.metrics.conversions_value,
                "impressions": row.metrics.impressions,
                "cost_micros": row.metrics.cost_micros,
                "video_quartile_p25_rate": row.metrics.video_quartile_p25_rate,
                "video_quartile_p50_rate": row.metrics.video_quartile_p50_rate,
                "video_quartile_p75_rate": row.metrics.video_quartile_p75_rate,
                "video_quartile_p100_rate": row.metrics.video_quartile_p100_rate,
                "customer_id": row.customer.id,
                "campaign_id": row.campaign.id,
                "campaign_name": row.campaign.name,
                "ad_group_id": row.ad_group.id,
                "ad_group_name": row.ad_group.name,
                "ad_group_status": row.ad_group.status,
                "ad_group_ad_ad_id": row.ad_group_ad.ad.id,
                "date": row.segments.date
            }