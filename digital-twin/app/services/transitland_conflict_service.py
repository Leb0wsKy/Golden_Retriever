"""
Transitland Conflict Auto-Generator Service.

This service automatically fetches real schedule data from Transitland
and generates realistic conflicts based on actual train schedules.

Features:
- Periodic schedule fetching from configured UK stations
- Automatic conflict detection (platform conflicts, headway violations, etc.)
- Storage in Qdrant for historical analysis
- Configurable generation frequency and parameters

Example:
    >>> from app.services.transitland_conflict_service import TransitlandConflictService
    >>> 
    >>> service = TransitlandConflictService()
    >>> await service.generate_and_store_conflicts(
    ...     stations=["London Euston", "Manchester Piccadilly"],
    ...     count=20
    ... )
"""

import logging
import asyncio
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.core.config import settings
from app.core.constants import ConflictType
from app.services.transitland_client import TransitlandClient, get_transitland_client
from app.services.schedule_conflict_generator import (
    HybridConflictGenerator,
    get_hybrid_generator,
)
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.qdrant_service import QdrantService, get_qdrant_service
from app.models.conflict import GeneratedConflict

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for automatic conflict generation."""
    
    # Generation parameters
    conflicts_per_run: int = 10
    schedule_ratio: float = 0.8  # 80% from real schedules, 20% synthetic
    
    # Station selection
    stations: Optional[List[str]] = None  # None = use all configured stations
    max_stations_per_run: int = 5
    
    # Conflict type preferences
    preferred_types: Optional[List[ConflictType]] = None  # None = all types
    
    # Storage options
    auto_store_in_qdrant: bool = True
    generate_embeddings: bool = True
    
    # Scheduling
    schedule_date: Optional[date] = None  # None = today
    
    @classmethod
    def default(cls) -> "GenerationConfig":
        """Create default configuration."""
        return cls()


@dataclass
class GenerationResult:
    """Result of a conflict generation run."""
    
    success: bool
    conflicts_generated: int
    conflicts_stored: int
    embeddings_created: int
    stations_processed: List[str]
    schedule_based_count: int
    synthetic_count: int
    errors: List[str]
    generation_time_seconds: float
    timestamp: datetime


class TransitlandConflictService:
    """
    Service for automatic Transitland-based conflict generation.
    
    This service bridges the gap between Transitland schedule data
    and the Digital Twin conflict resolution system.
    
    Attributes:
        config: Generation configuration.
        transitland_client: Client for Transitland API.
        schedule_generator: Generator for schedule-based conflicts.
        embedding_service: Service for creating embeddings.
        qdrant_service: Service for Qdrant storage.
    """
    
    def __init__(
        self,
        config: Optional[GenerationConfig] = None,
        transitland_client: Optional[TransitlandClient] = None,
        schedule_generator: Optional[HybridConflictGenerator] = None,
        embedding_service: Optional[EmbeddingService] = None,
        qdrant_service: Optional[QdrantService] = None,
    ):
        """
        Initialize the service.
        
        Args:
            config: Generation configuration (uses default if None).
            transitland_client: Transitland API client (creates new if None).
            schedule_generator: Hybrid conflict generator (creates new if None).
            embedding_service: Embedding service (creates new if None).
            qdrant_service: Qdrant service (creates new if None).
        """
        self.config = config or GenerationConfig.default()
        self._transitland_client = transitland_client
        self._schedule_generator = schedule_generator
        self._embedding_service = embedding_service
        self._qdrant_service = qdrant_service
        
        # Statistics
        self.total_runs = 0
        self.total_conflicts_generated = 0
        self.total_conflicts_stored = 0
        self.last_run_time: Optional[datetime] = None
        self.last_run_result: Optional[GenerationResult] = None
    
    @property
    def transitland_client(self) -> TransitlandClient:
        """Get or create Transitland client."""
        if self._transitland_client is None:
            self._transitland_client = get_transitland_client()
        return self._transitland_client
    
    @property
    def schedule_generator(self) -> HybridConflictGenerator:
        """Get or create hybrid conflict generator."""
        if self._schedule_generator is None:
            self._schedule_generator = get_hybrid_generator()
        return self._schedule_generator
    
    @property
    def embedding_service(self) -> EmbeddingService:
        """Get or create embedding service."""
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    @property
    def qdrant_service(self) -> QdrantService:
        """Get or create Qdrant service."""
        if self._qdrant_service is None:
            self._qdrant_service = get_qdrant_service()
        return self._qdrant_service
    
    def _select_stations(self) -> List[str]:
        """
        Select stations for conflict generation.
        
        Returns:
            List of station names to process.
        """
        if self.config.stations:
            # Use configured stations
            return self.config.stations[:self.config.max_stations_per_run]
        else:
            # Use all available UK stations from TransitlandClient
            all_stations = list(TransitlandClient.UK_STATIONS.keys())
            return all_stations[:self.config.max_stations_per_run]
    
    async def generate_and_store_conflicts(
        self,
        stations: Optional[List[str]] = None,
        count: Optional[int] = None,
        schedule_date: Optional[date] = None,
    ) -> GenerationResult:
        """
        Generate conflicts from Transitland schedules and store in Qdrant.
        
        This is the main method for automated conflict generation.
        
        Args:
            stations: Stations to process (uses config if None).
            count: Number of conflicts to generate (uses config if None).
            schedule_date: Date for schedule data (uses today if None).
        
        Returns:
            GenerationResult with statistics and any errors.
        
        Example:
            >>> result = await service.generate_and_store_conflicts(
            ...     stations=["London Euston", "Manchester Piccadilly"],
            ...     count=20
            ... )
            >>> print(f"Generated {result.conflicts_generated} conflicts")
        """
        import time
        start_time = time.time()
        errors = []
        
        # Use provided params or fall back to config
        target_stations = stations or self._select_stations()
        target_count = count or self.config.conflicts_per_run
        target_date = schedule_date or self.config.schedule_date or date.today()
        
        logger.info(
            f"Starting Transitland conflict generation: "
            f"{target_count} conflicts from {len(target_stations)} stations on {target_date}"
        )
        
        conflicts: List[GeneratedConflict] = []
        schedule_based_count = 0
        synthetic_count = 0
        stored_count = 0
        embeddings_count = 0
        
        try:
            # Generate conflicts using hybrid approach (schedule + synthetic)
            logger.info(f"Generating {target_count} conflicts using hybrid generator...")
            all_conflicts = await self.schedule_generator.generate(
                count=target_count,
                stations=target_stations,
                schedule_date=target_date,
            )
            conflicts.extend(all_conflicts)
            # Estimate schedule vs synthetic based on configured ratio
            schedule_based_count = int(len(all_conflicts) * self.config.schedule_ratio)
            synthetic_count = len(all_conflicts) - schedule_based_count
            logger.info(f"✅ Generated {len(all_conflicts)} conflicts (est. {schedule_based_count} real, {synthetic_count} synthetic)")
            
            # Store in Qdrant if configured
            if self.config.auto_store_in_qdrant and conflicts:
                try:
                    logger.info(f"Storing {len(conflicts)} conflicts in Qdrant...")
                    
                    # Ensure collections exist
                    self.qdrant_service.ensure_collections()
                    
                    for conflict in conflicts:
                        try:
                            # Generate embedding
                            conflict_text = self._build_conflict_text(conflict)
                            embedding = await asyncio.to_thread(
                                self.embedding_service.embed,
                                conflict_text
                            )
                            embeddings_count += 1
                            
                            # Store in Qdrant
                            await asyncio.to_thread(
                                self.qdrant_service.upsert_conflict,
                                conflict,
                                embedding,
                                conflict.id
                            )
                            stored_count += 1
                            
                        except Exception as e:
                            error_msg = f"Failed to store conflict {conflict.id}: {str(e)}"
                            logger.warning(error_msg)
                            errors.append(error_msg)
                    
                    logger.info(f"✅ Stored {stored_count}/{len(conflicts)} conflicts in Qdrant")
                    
                except Exception as e:
                    error_msg = f"Qdrant storage failed: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Update statistics
            self.total_runs += 1
            self.total_conflicts_generated += len(conflicts)
            self.total_conflicts_stored += stored_count
            self.last_run_time = datetime.utcnow()
            
            elapsed = time.time() - start_time
            
            result = GenerationResult(
                success=len(conflicts) > 0,
                conflicts_generated=len(conflicts),
                conflicts_stored=stored_count,
                embeddings_created=embeddings_count,
                stations_processed=target_stations,
                schedule_based_count=schedule_based_count,
                synthetic_count=synthetic_count,
                errors=errors,
                generation_time_seconds=elapsed,
                timestamp=datetime.utcnow(),
            )
            
            self.last_run_result = result
            
            logger.info(
                f"✅ Conflict generation complete: "
                f"{len(conflicts)} conflicts ({schedule_based_count} real, {synthetic_count} synthetic) "
                f"in {elapsed:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Conflict generation failed: {e}", exc_info=True)
            errors.append(f"Critical error: {str(e)}")
            
            elapsed = time.time() - start_time
            
            result = GenerationResult(
                success=False,
                conflicts_generated=len(conflicts),
                conflicts_stored=stored_count,
                embeddings_created=embeddings_count,
                stations_processed=target_stations,
                schedule_based_count=schedule_based_count,
                synthetic_count=synthetic_count,
                errors=errors,
                generation_time_seconds=elapsed,
                timestamp=datetime.utcnow(),
            )
            
            self.last_run_result = result
            return result
    
    def _build_conflict_text(self, conflict: GeneratedConflict) -> str:
        """
        Build text representation for embedding.
        
        Args:
            conflict: The conflict to convert to text.
        
        Returns:
            Text description suitable for embedding.
        """
        text_parts = [
            f"{conflict.conflict_type} at {conflict.station}",
            f"during {conflict.time_of_day}",
            f"Severity: {conflict.severity}",
            f"Affected trains: {', '.join(conflict.affected_trains)}",
            f"Initial delay: {conflict.delay_before} minutes",
            conflict.description,
        ]
        
        if conflict.platform:
            text_parts.append(f"Platform: {conflict.platform}")
        
        if conflict.track_section:
            text_parts.append(f"Track: {conflict.track_section}")
        
        return ". ".join(text_parts)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get service statistics.
        
        Returns:
            Dictionary with generation statistics.
        """
        return {
            "total_runs": self.total_runs,
            "total_conflicts_generated": self.total_conflicts_generated,
            "total_conflicts_stored": self.total_conflicts_stored,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "last_run_result": {
                "success": self.last_run_result.success,
                "conflicts_generated": self.last_run_result.conflicts_generated,
                "conflicts_stored": self.last_run_result.conflicts_stored,
                "schedule_based": self.last_run_result.schedule_based_count,
                "synthetic": self.last_run_result.synthetic_count,
                "errors": self.last_run_result.errors,
                "generation_time_seconds": self.last_run_result.generation_time_seconds,
            } if self.last_run_result else None,
            "config": {
                "conflicts_per_run": self.config.conflicts_per_run,
                "schedule_ratio": self.config.schedule_ratio,
                "auto_store_in_qdrant": self.config.auto_store_in_qdrant,
                "stations": self.config.stations or "all",
            }
        }


# =============================================================================
# Singleton instance
# =============================================================================

_service_instance: Optional[TransitlandConflictService] = None


def get_transitland_conflict_service() -> TransitlandConflictService:
    """
    Get singleton instance of TransitlandConflictService.
    
    Returns:
        Shared TransitlandConflictService instance.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = TransitlandConflictService()
    return _service_instance


def reset_transitland_conflict_service() -> None:
    """Reset the singleton instance (useful for testing)."""
    global _service_instance
    _service_instance = None
