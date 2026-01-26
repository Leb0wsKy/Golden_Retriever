"""
Transitland API client for fetching real transit schedules.

This service fetches real-world schedule data from the Transitland API
to enable realistic conflict generation based on actual timetables.

API Documentation: https://www.transit.land/documentation/rest-api/
"""

import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.core.config import settings


logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class StopTime:
    """A scheduled stop time at a station."""
    trip_id: str
    stop_id: str
    stop_name: str
    arrival_time: datetime
    departure_time: datetime
    stop_sequence: int
    platform: Optional[str] = None
    track: Optional[str] = None
    headsign: Optional[str] = None
    route_id: Optional[str] = None
    route_name: Optional[str] = None
    train_number: Optional[str] = None


@dataclass  
class ScheduledTrip:
    """A scheduled train trip with all its stops."""
    trip_id: str
    route_id: str
    route_name: str
    direction: int
    service_date: date
    stop_times: List[StopTime]
    train_number: Optional[str] = None
    

class ScheduleWindow(BaseModel):
    """A window of schedule data for a station."""
    station_id: str
    station_name: str
    start_time: datetime
    end_time: datetime
    arrivals: List[Dict[str, Any]] = Field(default_factory=list)
    departures: List[Dict[str, Any]] = Field(default_factory=list)
    platform_usage: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)


class HeadwayInfo(BaseModel):
    """Headway information between consecutive trains."""
    leading_trip_id: str
    following_trip_id: str
    route_id: str
    stop_id: str
    headway_seconds: int
    scheduled_headway_seconds: int  # What it should be
    is_violation: bool = False


# =============================================================================
# Transitland API Client
# =============================================================================

class TransitlandClient:
    """
    Client for the Transitland REST API.
    
    Fetches real schedule data for UK rail operators to enable
    realistic conflict generation.
    
    Example:
        >>> client = TransitlandClient()
        >>> schedules = await client.get_station_schedule(
        ...     station_id="s-gcpvj-londonstpancras",
        ...     date=date.today(),
        ...     start_hour=8,
        ...     end_hour=10
        ... )
    """
    
    BASE_URL = "https://transit.land/api/v2/rest"
    
    # UK rail operator feed IDs in Transitland
    UK_RAIL_FEEDS = [
        "f-gcpv-nationalrail",  # National Rail (covers most UK operators)
    ]
    
    # Major UK stations with their Transitland IDs
    UK_STATIONS = {
        "London Euston": "s-gcpvj-londoneuston",
        "London Kings Cross": "s-gcpvj-londonkingscross",
        "London St Pancras": "s-gcpvj-londonstpancras",
        "London Paddington": "s-gcpv-londonpaddington",
        "London Waterloo": "s-gcpu-londonwaterloo",
        "London Victoria": "s-gcpu-londonvictoria",
        "London Liverpool Street": "s-gcpw-londonliverpoolstreet",
        "Birmingham New Street": "s-gcqd-birminghamnewstreet",
        "Manchester Piccadilly": "s-gcw2-manchesterpiccadilly",
        "Edinburgh Waverley": "s-gcp6-edinburghwaverley",
        "Glasgow Central": "s-gckx-glasgowcentral",
        "Leeds": "s-gcse-leeds",
        "Liverpool Lime Street": "s-gcmv-liverpoollimestreet",
        "Bristol Temple Meads": "s-gbz-bristoltemplemeads",
        "Newcastle": "s-gcp7-newcastlecentral",
        "York": "s-gcx6-york",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Transitland client.
        
        Args:
            api_key: Transitland API key. If None, reads from settings.
        """
        self.api_key = api_key or getattr(settings, 'TRANSITLAND_API_KEY', None)
        if not self.api_key:
            logger.warning("No Transitland API key configured. Using fallback schedule generation.")
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["apikey"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to the Transitland API."""
        client = await self._get_client()
        
        try:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Transitland API error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request failed: {e}")
            raise
    
    # =========================================================================
    # Schedule Fetching Methods
    # =========================================================================
    
    async def get_station_schedule(
        self,
        station_name: str,
        schedule_date: date,
        start_hour: int = 6,
        end_hour: int = 22,
    ) -> ScheduleWindow:
        """
        Get all scheduled arrivals and departures at a station.
        
        Args:
            station_name: Human-readable station name (e.g., "London Euston")
            schedule_date: Date to fetch schedule for
            start_hour: Start hour (0-23)
            end_hour: End hour (0-23)
        
        Returns:
            ScheduleWindow with all scheduled movements
        """
        station_id = self.UK_STATIONS.get(station_name)
        if not station_id:
            logger.warning(f"Unknown station: {station_name}, using fallback")
            return self._generate_fallback_schedule(
                station_name, schedule_date, start_hour, end_hour
            )
        
        # Construct time window
        start_time = datetime.combine(schedule_date, datetime.min.time().replace(hour=start_hour))
        end_time = datetime.combine(schedule_date, datetime.min.time().replace(hour=end_hour))
        
        # If no API key, use fallback
        if not self.api_key:
            return self._generate_fallback_schedule(
                station_name, schedule_date, start_hour, end_hour
            )
        
        try:
            # Fetch departures from this station
            departures_data = await self._make_request(
                f"/stops/{station_id}/departures",
                params={
                    "service_date": schedule_date.isoformat(),
                    "start_time": f"{start_hour:02d}:00:00",
                    "end_time": f"{end_hour:02d}:00:00",
                    "limit": 500,
                }
            )
            
            # Process the response
            arrivals = []
            departures = []
            platform_usage: Dict[str, List[Dict[str, Any]]] = {}
            
            for stop_time in departures_data.get("stop_times", []):
                movement = self._parse_stop_time(stop_time)
                
                # Add to appropriate list
                if movement.get("is_arrival"):
                    arrivals.append(movement)
                else:
                    departures.append(movement)
                
                # Track platform usage
                platform = movement.get("platform", "unknown")
                if platform not in platform_usage:
                    platform_usage[platform] = []
                platform_usage[platform].append(movement)
            
            return ScheduleWindow(
                station_id=station_id,
                station_name=station_name,
                start_time=start_time,
                end_time=end_time,
                arrivals=arrivals,
                departures=departures,
                platform_usage=platform_usage,
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch schedule for {station_name}: {e}")
            return self._generate_fallback_schedule(
                station_name, schedule_date, start_hour, end_hour
            )
    
    def _parse_stop_time(self, stop_time_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a stop_time from the API response."""
        trip = stop_time_data.get("trip", {})
        route = trip.get("route", {})
        stop = stop_time_data.get("stop", {})
        
        return {
            "trip_id": trip.get("trip_id", ""),
            "route_id": route.get("route_id", ""),
            "route_name": route.get("route_long_name") or route.get("route_short_name", ""),
            "train_number": trip.get("trip_short_name", ""),
            "arrival_time": stop_time_data.get("arrival_time"),
            "departure_time": stop_time_data.get("departure_time"),
            "platform": stop_time_data.get("platform"),
            "track": stop_time_data.get("track"),
            "stop_name": stop.get("stop_name", ""),
            "headsign": trip.get("trip_headsign", ""),
            "is_arrival": stop_time_data.get("arrival_time") is not None,
        }
    
    async def get_route_headways(
        self,
        route_id: str,
        schedule_date: date,
    ) -> List[HeadwayInfo]:
        """
        Calculate headways between consecutive trains on a route.
        
        Args:
            route_id: The route identifier
            schedule_date: Date to analyze
        
        Returns:
            List of HeadwayInfo with actual vs expected headways
        """
        # If no API key, return empty
        if not self.api_key:
            return []
            
        try:
            response = await self._make_request(
                f"/routes/{route_id}/trips",
                params={
                    "service_date": schedule_date.isoformat(),
                    "include_geometry": "false",
                }
            )
            
            # Group trips by direction and stop
            trips_by_stop: Dict[str, List[Dict[str, Any]]] = {}
            
            for trip in response.get("trips", []):
                for stop_time in trip.get("stop_times", []):
                    stop_id = stop_time.get("stop", {}).get("stop_id", "")
                    if stop_id not in trips_by_stop:
                        trips_by_stop[stop_id] = []
                    trips_by_stop[stop_id].append({
                        "trip_id": trip.get("trip_id"),
                        "departure_time": stop_time.get("departure_time"),
                    })
            
            # Calculate headways
            headways = []
            for stop_id, stop_times in trips_by_stop.items():
                # Sort by departure time
                sorted_times = sorted(
                    stop_times,
                    key=lambda x: x["departure_time"] or "99:99:99"
                )
                
                for i in range(1, len(sorted_times)):
                    prev = sorted_times[i - 1]
                    curr = sorted_times[i]
                    
                    # Calculate headway in seconds
                    headway_seconds = self._time_diff_seconds(
                        prev["departure_time"],
                        curr["departure_time"]
                    )
                    
                    # Standard minimum headway for rail (3 minutes = 180 seconds)
                    min_headway = 180
                    
                    headways.append(HeadwayInfo(
                        leading_trip_id=prev["trip_id"],
                        following_trip_id=curr["trip_id"],
                        route_id=route_id,
                        stop_id=stop_id,
                        headway_seconds=headway_seconds,
                        scheduled_headway_seconds=min_headway,
                        is_violation=headway_seconds < min_headway,
                    ))
            
            return headways
            
        except Exception as e:
            logger.error(f"Failed to fetch headways for route {route_id}: {e}")
            return []
    
    def _time_diff_seconds(self, time1: str, time2: str) -> int:
        """Calculate difference in seconds between two time strings (HH:MM:SS)."""
        def parse_time(t: str) -> int:
            parts = t.split(":")
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        
        return parse_time(time2) - parse_time(time1)
    
    # =========================================================================
    # Fallback Methods (when API unavailable)
    # =========================================================================
    
    def _generate_fallback_schedule(
        self,
        station_name: str,
        schedule_date: date,
        start_hour: int,
        end_hour: int,
    ) -> ScheduleWindow:
        """
        Generate a realistic synthetic schedule when API is unavailable.
        
        Uses typical UK rail patterns for frequency and platform usage.
        """
        import random
        rng = random.Random(hash(f"{station_name}{schedule_date}"))
        
        start_time = datetime.combine(schedule_date, datetime.min.time().replace(hour=start_hour))
        end_time = datetime.combine(schedule_date, datetime.min.time().replace(hour=end_hour))
        
        arrivals = []
        departures = []
        platform_usage: Dict[str, List[Dict[str, Any]]] = {}
        
        # Generate trains based on time of day patterns
        current_time = start_time
        train_counter = 1
        
        platforms = ["1", "2", "3", "4", "5", "6", "7", "8"][:rng.randint(4, 8)]
        routes = ["InterCity", "Regional Express", "Suburban", "High Speed"]
        destinations = ["Manchester", "Edinburgh", "Birmingham", "Bristol", "Leeds", "Glasgow", "Newcastle", "Liverpool"]
        
        while current_time < end_time:
            hour = current_time.hour
            
            # Determine frequency based on time of day
            if 7 <= hour <= 9 or 17 <= hour <= 19:  # Peak
                interval_minutes = rng.randint(3, 8)
            elif 10 <= hour <= 16:  # Off-peak
                interval_minutes = rng.randint(10, 20)
            else:  # Early/late
                interval_minutes = rng.randint(20, 40)
            
            # Create train movement
            platform = rng.choice(platforms)
            route = rng.choice(routes)
            train_number = f"{route[:2].upper()}{train_counter:03d}"
            
            arrival_dt = current_time
            departure_dt = current_time + timedelta(minutes=rng.randint(2, 5))
            
            movement = {
                "trip_id": f"trip-{train_number}",
                "route_name": route,
                "train_number": train_number,
                "arrival_time": arrival_dt.strftime("%H:%M:%S"),
                "departure_time": departure_dt.strftime("%H:%M:%S"),
                "platform": platform,
                "stop_name": station_name,
                "headsign": rng.choice(destinations),
            }
            
            arrivals.append(movement)
            departures.append(movement)
            
            if platform not in platform_usage:
                platform_usage[platform] = []
            platform_usage[platform].append(movement)
            
            current_time += timedelta(minutes=interval_minutes)
            train_counter += 1
        
        return ScheduleWindow(
            station_id=f"fallback-{station_name.lower().replace(' ', '-')}",
            station_name=station_name,
            start_time=start_time,
            end_time=end_time,
            arrivals=arrivals,
            departures=departures,
            platform_usage=platform_usage,
        )


# =============================================================================
# Factory Function
# =============================================================================

_client_instance: Optional[TransitlandClient] = None


def get_transitland_client() -> TransitlandClient:
    """Get or create the Transitland client singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = TransitlandClient()
    return _client_instance


def clear_client_cache() -> None:
    """Clear the client singleton (useful for testing)."""
    global _client_instance
    _client_instance = None
