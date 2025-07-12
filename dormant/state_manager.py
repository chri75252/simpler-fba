"""
State Management for Amazon FBA Agent System v3.
Handles multi-phase processing state, resume capabilities, and workflow coordination.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from config import settings, PriceRangeConfig, ProcessingLimitsConfig

# Setup logging
log = logging.getLogger(__name__)


class ProcessingPhase(Enum):
    """Processing phases for multi-price-range workflow."""
    PHASE_1_LOW_PRICE = "phase_1_low_price"      # £0.1 - £10.0
    PHASE_2_MEDIUM_PRICE = "phase_2_medium_price"  # £10.0 - £20.0
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CategoryProgress:
    """Progress tracking for a single category."""
    category_url: str
    category_name: str = ""
    current_page: int = 1
    products_processed: int = 0
    products_found: int = 0
    last_processed_product_index: int = -1
    processing_start_time: Optional[str] = None
    processing_end_time: Optional[str] = None
    phase: ProcessingPhase = ProcessingPhase.PHASE_1_LOW_PRICE
    is_completed: bool = False
    error_count: int = 0
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['phase'] = self.phase.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CategoryProgress':
        """Create from dictionary (JSON deserialization)."""
        if 'phase' in data:
            data['phase'] = ProcessingPhase(data['phase'])
        return cls(**data)


@dataclass
class PhaseTransitionPoint:
    """Tracks where Phase 1 ended and Phase 2 should begin."""
    category_url: str
    page_number: int
    product_index: int
    timestamp: str
    products_above_threshold: List[float]  # Recent product prices that triggered transition
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PhaseTransitionPoint':
        """Create from dictionary (JSON deserialization)."""
        return cls(**data)


@dataclass
class ProcessingState:
    """Complete processing state for the FBA agent system."""
    supplier_url: str
    supplier_name: str
    session_id: str
    current_phase: ProcessingPhase
    
    # Processing configuration
    processing_limits: Dict[str, int]
    price_ranges: Dict[str, float]
    
    # Category tracking
    categories_progress: Dict[str, CategoryProgress]
    
    # Phase transition tracking
    phase_transition_points: Dict[str, PhaseTransitionPoint]
    price_monitoring_window: List[float]  # Recent product prices for phase transition detection
    
    current_category_url: Optional[str] = None
    
    # Overall progress
    total_products_processed: int = 0
    total_categories_processed: int = 0
    session_start_time: str = ""
    last_update_time: str = ""
    
    # Resume capabilities
    can_resume: bool = True
    resume_from_category: Optional[str] = None
    resume_from_page: int = 1
    resume_from_product_index: int = 0
    
    # Error tracking
    global_error_count: int = 0
    last_global_error: Optional[str] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        current_time = datetime.now().isoformat()
        if not self.session_start_time:
            self.session_start_time = current_time
        if not self.last_update_time:
            self.last_update_time = current_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['current_phase'] = self.current_phase.value
        
        # Convert category progress
        data['categories_progress'] = {
            url: progress.to_dict() 
            for url, progress in self.categories_progress.items()
        }
        
        # Convert phase transition points
        data['phase_transition_points'] = {
            url: point.to_dict()
            for url, point in self.phase_transition_points.items()
        }
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingState':
        """Create from dictionary (JSON deserialization)."""
        # Convert phase
        if 'current_phase' in data:
            data['current_phase'] = ProcessingPhase(data['current_phase'])
        
        # Convert category progress
        if 'categories_progress' in data:
            data['categories_progress'] = {
                url: CategoryProgress.from_dict(progress_data)
                for url, progress_data in data['categories_progress'].items()
            }
        
        # Convert phase transition points
        if 'phase_transition_points' in data:
            data['phase_transition_points'] = {
                url: PhaseTransitionPoint.from_dict(point_data)
                for url, point_data in data['phase_transition_points'].items()
            }
        
        return cls(**data)


class StateManager:
    """
    Manages processing state for the FBA agent system.
    
    Features:
    - Multi-phase processing (Phase 1: £0.1-£10.0, Phase 2: £10.0-£20.0)
    - Resume capabilities with exact position tracking
    - Category-level progress tracking
    - Price monitoring for automatic phase transitions
    - Error tracking and recovery
    - Atomic state updates with backup/restore
    """
    
    def __init__(self, 
                 supplier_url: str,
                 supplier_name: str,
                 session_id: Optional[str] = None,
                 price_config: Optional[PriceRangeConfig] = None,
                 limits_config: Optional[ProcessingLimitsConfig] = None):
        """Initialize state manager."""
        self.supplier_url = supplier_url
        self.supplier_name = supplier_name
        self.session_id = session_id or self._generate_session_id()
        
        self.price_config = price_config or settings.price_ranges
        self.limits_config = limits_config or settings.processing_limits
        
        # File paths
        self.state_file = self._get_state_file_path()
        self.backup_dir = self._get_backup_dir_path()
        
        # Current state
        self._state: Optional[ProcessingState] = None
        
        # Ensure directories exist
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        log.info(f"StateManager initialized for {supplier_name} (session: {self.session_id})")
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.supplier_name}_{timestamp}"
    
    def _get_state_file_path(self) -> Path:
        """Get the state file path."""
        base_dir = Path(settings.cache.base_output_dir)
        filename = f"{self.supplier_name}_processing_state.json"
        return base_dir / filename
    
    def _get_backup_dir_path(self) -> Path:
        """Get the backup directory path."""
        return Path(settings.cache.emergency_backup_dir) / "state_backups"
    
    def _create_backup(self) -> str:
        """Create a backup of the current state file."""
        if not self.state_file.exists():
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{self.supplier_name}_state_backup_{timestamp}.json"
        backup_path = self.backup_dir / backup_filename
        
        try:
            # Copy current state to backup
            with open(self.state_file, 'r') as src, open(backup_path, 'w') as dst:
                dst.write(src.read())
            
            log.debug(f"State backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            log.error(f"Failed to create state backup: {e}")
            return ""
    
    def load_state(self) -> ProcessingState:
        """Load processing state from disk or create new state."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                
                self._state = ProcessingState.from_dict(data)
                log.info(f"Loaded existing state: {self._state.current_phase.value}, "
                        f"{self._state.total_products_processed} products processed")
                
            else:
                # Create new state
                self._state = ProcessingState(
                    supplier_url=self.supplier_url,
                    supplier_name=self.supplier_name,
                    session_id=self.session_id,
                    current_phase=ProcessingPhase.PHASE_1_LOW_PRICE,
                    processing_limits={
                        "max_products_per_category": self.limits_config.max_products_per_category,
                        "max_analyzed_products": self.limits_config.max_analyzed_products,
                        "max_products_per_cycle": self.limits_config.max_products_per_cycle
                    },
                    price_ranges={
                        "phase1_min": self.price_config.phase1_min_price,
                        "phase1_max": self.price_config.phase1_max_price,
                        "phase2_min": self.price_config.phase2_min_price,
                        "phase2_max": self.price_config.phase2_max_price
                    },
                    categories_progress={},
                    phase_transition_points={},
                    price_monitoring_window=[]
                )
                log.info("Created new processing state")
                
        except Exception as e:
            log.error(f"Failed to load state: {e}")
            # Create fallback state
            self._state = ProcessingState(
                supplier_url=self.supplier_url,
                supplier_name=self.supplier_name,
                session_id=self.session_id,
                current_phase=ProcessingPhase.PHASE_1_LOW_PRICE,
                processing_limits={},
                price_ranges={},
                categories_progress={},
                phase_transition_points={},
                price_monitoring_window=[]
            )
        
        return self._state
    
    def save_state(self) -> bool:
        """Save current state to disk with backup."""
        if self._state is None:
            log.warning("No state to save")
            return False
        
        try:
            # Create backup before saving
            self._create_backup()
            
            # Update timestamp
            self._state.last_update_time = datetime.now().isoformat()
            
            # Save state atomically
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self._state.to_dict(), f, indent=2)
            
            # Atomic rename
            temp_file.replace(self.state_file)
            
            log.debug(f"State saved successfully: {self.state_file}")
            return True
            
        except Exception as e:
            log.error(f"Failed to save state: {e}")
            return False
    
    def get_current_state(self) -> Optional[ProcessingState]:
        """Get the current processing state."""
        return self._state
    
    def is_unlimited_processing(self) -> bool:
        """Check if system is configured for unlimited processing."""
        return self.limits_config.is_unlimited_processing()
    
    def get_current_phase(self) -> ProcessingPhase:
        """Get current processing phase."""
        return self._state.current_phase if self._state else ProcessingPhase.PHASE_1_LOW_PRICE
    
    def get_current_price_range(self) -> Tuple[float, float]:
        """Get current price range based on phase."""
        phase = self.get_current_phase()
        
        if phase == ProcessingPhase.PHASE_1_LOW_PRICE:
            return self.price_config.phase1_min_price, self.price_config.phase1_max_price
        elif phase == ProcessingPhase.PHASE_2_MEDIUM_PRICE:
            return self.price_config.phase2_min_price, self.price_config.phase2_max_price
        else:
            return self.price_config.phase1_min_price, self.price_config.phase2_max_price
    
    def add_price_to_monitoring(self, price: float) -> bool:
        """Add a product price to the monitoring window for phase transition detection."""
        if self._state is None:
            return False
        
        # Add price to monitoring window
        self._state.price_monitoring_window.append(price)
        
        # Keep only the last N prices as configured
        window_size = self.price_config.price_monitoring_window
        if len(self._state.price_monitoring_window) > window_size:
            self._state.price_monitoring_window = self._state.price_monitoring_window[-window_size:]
        
        # Check for phase transition
        return self._check_phase_transition()
    
    def _check_phase_transition(self) -> bool:
        """Check if phase transition should occur based on price monitoring."""
        if (self._state is None or 
            self._state.current_phase != ProcessingPhase.PHASE_1_LOW_PRICE or
            len(self._state.price_monitoring_window) < self.price_config.price_monitoring_window):
            return False
        
        # Count products above phase 1 threshold
        threshold_price = self.price_config.phase1_max_price
        prices_above_threshold = [
            p for p in self._state.price_monitoring_window 
            if p > threshold_price
        ]
        
        transition_threshold = self.price_config.phase_transition_threshold
        
        if len(prices_above_threshold) >= transition_threshold:
            log.info(f"Phase 1 → Phase 2 transition triggered: "
                    f"{len(prices_above_threshold)}/{len(self._state.price_monitoring_window)} "
                    f"products above £{threshold_price}")
            
            # Store transition point
            self._store_phase_transition_point(prices_above_threshold)
            
            # Transition to Phase 2
            self._state.current_phase = ProcessingPhase.PHASE_2_MEDIUM_PRICE
            self._state.price_monitoring_window = []  # Reset monitoring window
            
            return True
        
        return False
    
    def _store_phase_transition_point(self, prices_above_threshold: List[float]):
        """Store the exact point where phase transition occurred."""
        if self._state is None or self._state.current_category_url is None:
            return
        
        current_category = self._state.categories_progress.get(self._state.current_category_url)
        if current_category is None:
            return
        
        transition_point = PhaseTransitionPoint(
            category_url=self._state.current_category_url,
            page_number=current_category.current_page,
            product_index=current_category.last_processed_product_index,
            timestamp=datetime.now().isoformat(),
            products_above_threshold=prices_above_threshold
        )
        
        self._state.phase_transition_points[self._state.current_category_url] = transition_point
        
        log.info(f"Phase transition point stored for {self._state.current_category_url}: "
                f"page {transition_point.page_number}, product {transition_point.product_index}")
    
    def start_category_processing(self, category_url: str, category_name: str = "") -> CategoryProgress:
        """Start processing a new category or resume existing one."""
        if self._state is None:
            raise RuntimeError("State not loaded")
        
        self._state.current_category_url = category_url
        
        if category_url not in self._state.categories_progress:
            # New category
            progress = CategoryProgress(
                category_url=category_url,
                category_name=category_name,
                phase=self._state.current_phase,
                processing_start_time=datetime.now().isoformat()
            )
            self._state.categories_progress[category_url] = progress
            log.info(f"Started new category: {category_name or category_url}")
        else:
            # Existing category
            progress = self._state.categories_progress[category_url]
            progress.phase = self._state.current_phase  # Update to current phase
            log.info(f"Resumed category: {category_name or category_url} "
                    f"(page {progress.current_page}, {progress.products_processed} products)")
        
        return self._state.categories_progress[category_url]
    
    def update_category_progress(self, 
                                category_url: str,
                                current_page: int = None,
                                products_processed: int = None,
                                products_found: int = None,
                                last_product_index: int = None,
                                error: str = None) -> bool:
        """Update progress for a specific category."""
        if (self._state is None or 
            category_url not in self._state.categories_progress):
            return False
        
        progress = self._state.categories_progress[category_url]
        
        if current_page is not None:
            progress.current_page = current_page
        if products_processed is not None:
            progress.products_processed = products_processed
            self._state.total_products_processed += (products_processed - progress.products_processed)
        if products_found is not None:
            progress.products_found = products_found
        if last_product_index is not None:
            progress.last_processed_product_index = last_product_index
        
        if error:
            progress.error_count += 1
            progress.last_error = error
            self._state.global_error_count += 1
            self._state.last_global_error = error
        
        return True
    
    def complete_category(self, category_url: str) -> bool:
        """Mark a category as completed."""
        if (self._state is None or 
            category_url not in self._state.categories_progress):
            return False
        
        progress = self._state.categories_progress[category_url]
        progress.is_completed = True
        progress.processing_end_time = datetime.now().isoformat()
        
        self._state.total_categories_processed += 1
        
        log.info(f"Category completed: {category_url} "
                f"({progress.products_processed} products processed)")
        
        return True
    
    def get_resume_point(self) -> Tuple[Optional[str], int, int]:
        """Get the exact point where processing should resume."""
        if self._state is None:
            return None, 1, 0
        
        # If we have a current category, resume from there
        if (self._state.current_category_url and 
            self._state.current_category_url in self._state.categories_progress):
            
            progress = self._state.categories_progress[self._state.current_category_url]
            return (self._state.current_category_url, 
                   progress.current_page, 
                   progress.last_processed_product_index + 1)
        
        # Find the last incomplete category
        for url, progress in self._state.categories_progress.items():
            if not progress.is_completed:
                return url, progress.current_page, progress.last_processed_product_index + 1
        
        # No resume point found
        return None, 1, 0
    
    def should_continue_processing(self) -> bool:
        """Check if processing should continue based on limits and phase."""
        if self._state is None:
            return False
        
        # If unlimited processing is enabled, always continue
        if self.is_unlimited_processing():
            return self._state.current_phase not in [ProcessingPhase.COMPLETED, ProcessingPhase.FAILED]
        
        # Check specific limits
        limits = self._state.processing_limits
        
        if (limits.get("max_analyzed_products", 0) > 0 and 
            self._state.total_products_processed >= limits["max_analyzed_products"]):
            log.info(f"Max analyzed products limit reached: {self._state.total_products_processed}")
            return False
        
        if (limits.get("max_products_per_cycle", 0) > 0 and
            self._state.total_products_processed >= limits["max_products_per_cycle"]):
            log.info(f"Max products per cycle limit reached: {self._state.total_products_processed}")
            return False
        
        return self._state.current_phase not in [ProcessingPhase.COMPLETED, ProcessingPhase.FAILED]
    
    def mark_completed(self, reason: str = "Processing completed successfully") -> bool:
        """Mark the entire processing session as completed."""
        if self._state is None:
            return False
        
        self._state.current_phase = ProcessingPhase.COMPLETED
        log.info(f"Processing session completed: {reason}")
        
        return self.save_state()
    
    def mark_failed(self, reason: str = "Processing failed") -> bool:
        """Mark the entire processing session as failed."""
        if self._state is None:
            return False
        
        self._state.current_phase = ProcessingPhase.FAILED
        self._state.last_global_error = reason
        
        log.error(f"Processing session failed: {reason}")
        
        return self.save_state()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        if self._state is None:
            return {}
        
        completed_categories = sum(1 for p in self._state.categories_progress.values() if p.is_completed)
        total_categories = len(self._state.categories_progress)
        
        # Calculate processing time
        start_time = datetime.fromisoformat(self._state.session_start_time)
        current_time = datetime.now()
        processing_duration = current_time - start_time
        
        return {
            "session_id": self._state.session_id,
            "current_phase": self._state.current_phase.value,
            "total_products_processed": self._state.total_products_processed,
            "total_categories": total_categories,
            "completed_categories": completed_categories,
            "categories_in_progress": total_categories - completed_categories,
            "processing_duration_seconds": processing_duration.total_seconds(),
            "processing_duration_hours": processing_duration.total_seconds() / 3600,
            "global_error_count": self._state.global_error_count,
            "current_price_range": self.get_current_price_range(),
            "unlimited_processing": self.is_unlimited_processing(),
            "can_resume": self._state.can_resume
        }


# Convenience functions
def create_state_manager(supplier_url: str, supplier_name: str, session_id: str = None) -> StateManager:
    """Create a new state manager instance."""
    return StateManager(supplier_url, supplier_name, session_id)


if __name__ == "__main__":
    # Test the state manager
    print("📊 Testing State Manager")
    print("=" * 30)
    
    # Create test state manager
    manager = StateManager(
        supplier_url="https://www.clearance-king.co.uk",
        supplier_name="clearance-king.co.uk",
        session_id="test_session"
    )
    
    # Test state loading/saving
    state = manager.load_state()
    print(f"✅ State loaded: {state.current_phase.value}")
    
    # Test category processing
    category_url = "/test-category.html"
    progress = manager.start_category_processing(category_url, "Test Category")
    print(f"✅ Category started: {progress.category_url}")
    
    # Test price monitoring and phase transition
    print(f"Current phase: {manager.get_current_phase().value}")
    print(f"Current price range: £{manager.get_current_price_range()[0]} - £{manager.get_current_price_range()[1]}")
    
    # Add some prices to trigger phase transition
    prices = [5.0, 7.0, 12.0, 15.0, 18.0]  # Mix of low and high prices
    for price in prices:
        transitioned = manager.add_price_to_monitoring(price)
        if transitioned:
            print(f"🔄 Phase transition triggered at price £{price}")
            break
    
    print(f"Final phase: {manager.get_current_phase().value}")
    print(f"Final price range: £{manager.get_current_price_range()[0]} - £{manager.get_current_price_range()[1]}")
    
    # Test statistics
    stats = manager.get_statistics()
    print(f"📈 Statistics: {stats}")
    
    # Test save
    saved = manager.save_state()
    print(f"✅ State saved: {saved}")
    
    print("\n🎯 State Manager test completed successfully!")