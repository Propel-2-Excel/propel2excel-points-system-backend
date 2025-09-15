"""
Enhanced Availability Matching Algorithm for Propel2Excel Resume Review Sessions

This module provides sophisticated algorithms to match student and professional
availability for optimal scheduling.

Features:
- Natural language time parsing
- Time zone handling
- Fuzzy matching for flexibility
- Scoring algorithm for best matches
- Multiple matching strategies

Usage:
    from availability_matcher import AvailabilityMatcher
    
    matcher = AvailabilityMatcher()
    matches = matcher.find_matches(student_availability, professional_availability)
"""

import re
import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class MatchStrategy(Enum):
    EXACT = "exact"           # Exact time/day matches only
    FLEXIBLE = "flexible"     # Allow partial matches
    FUZZY = "fuzzy"          # Use fuzzy matching algorithms

@dataclass
class TimeSlot:
    """Represents a time slot with day, start, end, and metadata"""
    day: str                  # Day of week (monday, tuesday, etc.)
    start_time: Optional[time] = None  # Start time (HH:MM)
    end_time: Optional[time] = None    # End time (HH:MM)
    period: Optional[str] = None       # Period (morning, afternoon, evening)
    timezone: str = "UTC"              # Time zone
    raw_text: str = ""                 # Original text for reference
    confidence: float = 1.0            # Parsing confidence (0-1)

@dataclass
class Match:
    """Represents a match between student and professional availability"""
    student_slot: TimeSlot
    professional_slot: TimeSlot
    overlap_minutes: int               # Minutes of overlap
    match_score: float                 # Match quality score (0-1)
    match_type: str                    # Type of match (exact, partial, fuzzy)
    suggested_time: Optional[datetime] = None  # Suggested meeting time

class AvailabilityMatcher:
    """Advanced availability matching system"""
    
    # Day name mappings and variations
    DAY_PATTERNS = {
        'monday': ['monday', 'mon', 'm'],
        'tuesday': ['tuesday', 'tue', 'tues', 't'],
        'wednesday': ['wednesday', 'wed', 'w'],
        'thursday': ['thursday', 'thu', 'thur', 'th'],
        'friday': ['friday', 'fri', 'f'],
        'saturday': ['saturday', 'sat', 's'],
        'sunday': ['sunday', 'sun', 'su']
    }
    
    # Time period mappings
    TIME_PERIODS = {
        'morning': (time(6, 0), time(12, 0)),
        'afternoon': (time(12, 0), time(18, 0)),
        'evening': (time(18, 0), time(22, 0)),
        'night': (time(22, 0), time(6, 0))
    }
    
    # Common time patterns
    TIME_PATTERNS = [
        r'(\d{1,2}):(\d{2})\s*(am|pm)',                    # 2:30 PM
        r'(\d{1,2})\s*(am|pm)',                            # 2 PM
        r'(\d{1,2}):(\d{2})',                              # 14:30
        r'(\d{1,2})-(\d{1,2})\s*(am|pm)',                  # 2-3 PM
        r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})',           # 2:30-3:30
    ]
    
    def __init__(self, strategy: MatchStrategy = MatchStrategy.FLEXIBLE):
        """
        Initialize availability matcher
        
        Args:
            strategy: Matching strategy to use
        """
        self.strategy = strategy
    
    def parse_availability(self, availability_text: str) -> List[TimeSlot]:
        """
        Parse natural language availability into structured TimeSlot objects
        
        Args:
            availability_text: Raw availability text
            
        Returns:
            List of parsed TimeSlot objects
        """
        if not availability_text:
            return []
        
        # Split by common delimiters
        segments = re.split(r'[,;]|\sand\s|\sor\s', availability_text.lower())
        slots = []
        
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
                
            slot = self._parse_single_segment(segment)
            if slot:
                slots.append(slot)
        
        return slots
    
    def _parse_single_segment(self, segment: str) -> Optional[TimeSlot]:
        """Parse a single availability segment"""
        segment = segment.strip().lower()
        
        # Extract day
        day = self._extract_day(segment)
        
        # Extract time information
        start_time, end_time = self._extract_times(segment)
        
        # Extract period
        period = self._extract_period(segment)
        
        # If we have a period but no specific times, use period defaults
        if period and not start_time and not end_time:
            if period in self.TIME_PERIODS:
                start_time, end_time = self.TIME_PERIODS[period]
        
        # Calculate confidence based on how much we parsed
        confidence = self._calculate_confidence(segment, day, start_time, end_time, period)
        
        if day or start_time or period:
            return TimeSlot(
                day=day or "any",
                start_time=start_time,
                end_time=end_time,
                period=period,
                raw_text=segment,
                confidence=confidence
            )
        
        return None
    
    def _extract_day(self, text: str) -> Optional[str]:
        """Extract day of week from text"""
        for day, patterns in self.DAY_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    return day
        return None
    
    def _extract_times(self, text: str) -> Tuple[Optional[time], Optional[time]]:
        """Extract start and end times from text"""
        for pattern in self.TIME_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return self._parse_time_match(match)
        return None, None
    
    def _parse_time_match(self, match) -> Tuple[Optional[time], Optional[time]]:
        """Parse time from regex match"""
        groups = match.groups()
        
        if len(groups) >= 3 and groups[2] in ['am', 'pm']:
            # Handle AM/PM format
            hour = int(groups[0])
            minute = int(groups[1]) if groups[1] else 0
            
            if groups[2] == 'pm' and hour != 12:
                hour += 12
            elif groups[2] == 'am' and hour == 12:
                hour = 0
                
            return time(hour, minute), None
        
        elif len(groups) >= 2:
            # Handle 24-hour format or range
            try:
                hour1 = int(groups[0])
                minute1 = int(groups[1]) if groups[1] else 0
                start_time = time(hour1, minute1)
                
                if len(groups) >= 4:
                    # Time range
                    hour2 = int(groups[2])
                    minute2 = int(groups[3]) if groups[3] else 0
                    end_time = time(hour2, minute2)
                    return start_time, end_time
                
                return start_time, None
            except ValueError:
                return None, None
        
        return None, None
    
    def _extract_period(self, text: str) -> Optional[str]:
        """Extract time period from text"""
        for period in self.TIME_PERIODS.keys():
            if period in text:
                return period
        return None
    
    def _calculate_confidence(self, text: str, day: str, start_time: time, 
                            end_time: time, period: str) -> float:
        """Calculate parsing confidence score"""
        score = 0.0
        
        # Day recognition
        if day:
            score += 0.3
        
        # Time recognition
        if start_time:
            score += 0.4
        if end_time:
            score += 0.2
        
        # Period recognition
        if period:
            score += 0.1
        
        # Text length and complexity (longer, more specific text = higher confidence)
        if len(text) > 10:
            score += 0.1
        
        return min(score, 1.0)
    
    def find_matches(self, student_availability: List[str], 
                    professional_availability: List[str]) -> List[Match]:
        """
        Find matches between student and professional availability
        
        Args:
            student_availability: List of student availability strings
            professional_availability: List of professional availability strings
            
        Returns:
            List of Match objects sorted by match score
        """
        # Parse availability
        student_slots = []
        for avail in student_availability:
            student_slots.extend(self.parse_availability(avail))
        
        professional_slots = []
        for avail in professional_availability:
            professional_slots.extend(self.parse_availability(avail))
        
        # Find matches
        matches = []
        for student_slot in student_slots:
            for professional_slot in professional_slots:
                match = self._compare_slots(student_slot, professional_slot)
                if match:
                    matches.append(match)
        
        # Sort by match score (highest first)
        matches.sort(key=lambda m: m.match_score, reverse=True)
        
        return matches
    
    def _compare_slots(self, student_slot: TimeSlot, professional_slot: TimeSlot) -> Optional[Match]:
        """Compare two time slots for compatibility"""
        
        # Day compatibility
        day_match = self._check_day_compatibility(student_slot.day, professional_slot.day)
        if not day_match:
            return None
        
        # Time compatibility
        time_match, overlap_minutes = self._check_time_compatibility(student_slot, professional_slot)
        if not time_match:
            return None
        
        # Calculate match score
        score = self._calculate_match_score(student_slot, professional_slot, overlap_minutes)
        
        # Determine match type
        match_type = self._determine_match_type(student_slot, professional_slot)
        
        return Match(
            student_slot=student_slot,
            professional_slot=professional_slot,
            overlap_minutes=overlap_minutes,
            match_score=score,
            match_type=match_type
        )
    
    def _check_day_compatibility(self, student_day: str, professional_day: str) -> bool:
        """Check if days are compatible"""
        if student_day == "any" or professional_day == "any":
            return True
        
        if student_day == professional_day:
            return True
        
        # Allow fuzzy matching for similar day abbreviations
        if self.strategy == MatchStrategy.FUZZY:
            student_patterns = self.DAY_PATTERNS.get(student_day, [])
            professional_patterns = self.DAY_PATTERNS.get(professional_day, [])
            
            return bool(set(student_patterns) & set(professional_patterns))
        
        return False
    
    def _check_time_compatibility(self, student_slot: TimeSlot, 
                                professional_slot: TimeSlot) -> Tuple[bool, int]:
        """Check time compatibility and calculate overlap"""
        
        # If both have specific times, check overlap
        if (student_slot.start_time and student_slot.end_time and 
            professional_slot.start_time and professional_slot.end_time):
            
            return self._calculate_time_overlap(
                student_slot.start_time, student_slot.end_time,
                professional_slot.start_time, professional_slot.end_time
            )
        
        # If one has period and other has time, check compatibility
        if student_slot.period and professional_slot.start_time:
            period_start, period_end = self.TIME_PERIODS.get(student_slot.period, (None, None))
            if period_start and period_end:
                return self._time_in_period(professional_slot.start_time, period_start, period_end), 30
        
        if professional_slot.period and student_slot.start_time:
            period_start, period_end = self.TIME_PERIODS.get(professional_slot.period, (None, None))
            if period_start and period_end:
                return self._time_in_period(student_slot.start_time, period_start, period_end), 30
        
        # If both have periods, check if they match
        if student_slot.period and professional_slot.period:
            return student_slot.period == professional_slot.period, 60
        
        # If neither has specific time info, consider it a match
        if (not student_slot.start_time and not student_slot.period and
            not professional_slot.start_time and not professional_slot.period):
            return True, 30
        
        return False, 0
    
    def _calculate_time_overlap(self, start1: time, end1: time, 
                              start2: time, end2: time) -> Tuple[bool, int]:
        """Calculate overlap between two time ranges"""
        
        # Convert times to minutes since midnight for easier calculation
        start1_min = start1.hour * 60 + start1.minute
        end1_min = end1.hour * 60 + end1.minute
        start2_min = start2.hour * 60 + start2.minute
        end2_min = end2.hour * 60 + end2.minute
        
        # Handle overnight periods (end time before start time)
        if end1_min <= start1_min:
            end1_min += 24 * 60
        if end2_min <= start2_min:
            end2_min += 24 * 60
        
        # Find overlap
        overlap_start = max(start1_min, start2_min)
        overlap_end = min(end1_min, end2_min)
        
        if overlap_end > overlap_start:
            overlap_minutes = overlap_end - overlap_start
            return True, overlap_minutes
        
        return False, 0
    
    def _time_in_period(self, check_time: time, period_start: time, period_end: time) -> bool:
        """Check if a time falls within a period"""
        check_min = check_time.hour * 60 + check_time.minute
        start_min = period_start.hour * 60 + period_start.minute
        end_min = period_end.hour * 60 + period_end.minute
        
        # Handle overnight periods
        if end_min <= start_min:
            return check_min >= start_min or check_min <= end_min
        
        return start_min <= check_min <= end_min
    
    def _calculate_match_score(self, student_slot: TimeSlot, professional_slot: TimeSlot, 
                             overlap_minutes: int) -> float:
        """Calculate overall match score"""
        score = 0.0
        
        # Base score from overlap duration
        if overlap_minutes > 0:
            score += min(overlap_minutes / 60.0, 1.0) * 0.4  # Max 0.4 for time overlap
        
        # Bonus for exact day match
        if student_slot.day == professional_slot.day:
            score += 0.2
        elif student_slot.day == "any" or professional_slot.day == "any":
            score += 0.1
        
        # Bonus for specific time matches
        if (student_slot.start_time and professional_slot.start_time):
            score += 0.2
        
        # Confidence factor
        confidence_factor = (student_slot.confidence + professional_slot.confidence) / 2
        score *= confidence_factor
        
        # Bonus for longer overlaps
        if overlap_minutes >= 30:
            score += 0.1
        if overlap_minutes >= 60:
            score += 0.1
        
        return min(score, 1.0)
    
    def _determine_match_type(self, student_slot: TimeSlot, professional_slot: TimeSlot) -> str:
        """Determine the type of match"""
        
        # Exact match: same day and overlapping specific times
        if (student_slot.day == professional_slot.day and
            student_slot.start_time and professional_slot.start_time):
            return "exact"
        
        # Partial match: some specificity but not complete
        if (student_slot.day == professional_slot.day or
            (student_slot.period and professional_slot.period)):
            return "partial"
        
        return "fuzzy"
    
    def suggest_meeting_times(self, matches: List[Match], 
                            num_suggestions: int = 3) -> List[Dict[str, Any]]:
        """
        Suggest specific meeting times based on matches
        
        Args:
            matches: List of Match objects
            num_suggestions: Number of suggestions to return
            
        Returns:
            List of suggested meeting time dictionaries
        """
        suggestions = []
        
        for match in matches[:num_suggestions]:
            suggestion = self._create_time_suggestion(match)
            if suggestion:
                suggestions.append(suggestion)
        
        return suggestions
    
    def _create_time_suggestion(self, match: Match) -> Optional[Dict[str, Any]]:
        """Create a specific time suggestion from a match"""
        
        # Use the overlap time if both have specific times
        if (match.student_slot.start_time and match.professional_slot.start_time):
            # Find overlap start time
            student_start = match.student_slot.start_time
            professional_start = match.professional_slot.start_time
            
            # Use the later start time
            suggested_time = max(student_start, professional_start)
            
            return {
                'day': match.student_slot.day or match.professional_slot.day,
                'time': suggested_time.strftime('%I:%M %p'),
                'duration': min(match.overlap_minutes, 30),
                'match_score': match.match_score,
                'match_type': match.match_type,
                'description': f"{match.student_slot.raw_text} ↔ {match.professional_slot.raw_text}"
            }
        
        # Use period-based suggestion
        elif match.student_slot.period or match.professional_slot.period:
            period = match.student_slot.period or match.professional_slot.period
            
            # Default times for periods
            period_times = {
                'morning': '10:00 AM',
                'afternoon': '2:00 PM',
                'evening': '7:00 PM'
            }
            
            return {
                'day': match.student_slot.day or match.professional_slot.day,
                'time': period_times.get(period, '2:00 PM'),
                'duration': 30,
                'match_score': match.match_score,
                'match_type': match.match_type,
                'description': f"{match.student_slot.raw_text} ↔ {match.professional_slot.raw_text}"
            }
        
        return None

# Utility functions for easy integration
def find_availability_matches(student_availability: List[str], 
                            professional_availability: List[str],
                            strategy: MatchStrategy = MatchStrategy.FLEXIBLE) -> List[Dict[str, Any]]:
    """
    Simple function to find availability matches
    
    Args:
        student_availability: List of student availability strings
        professional_availability: List of professional availability strings
        strategy: Matching strategy
        
    Returns:
        List of match dictionaries with scores and suggestions
    """
    matcher = AvailabilityMatcher(strategy)
    matches = matcher.find_matches(student_availability, professional_availability)
    
    results = []
    for match in matches:
        results.append({
            'student_availability': match.student_slot.raw_text,
            'professional_availability': match.professional_slot.raw_text,
            'overlap_minutes': match.overlap_minutes,
            'match_score': match.match_score,
            'match_type': match.match_type,
            'day': match.student_slot.day or match.professional_slot.day,
            'period': match.student_slot.period or match.professional_slot.period
        })
    
    return results

def get_time_suggestions(student_availability: List[str], 
                        professional_availability: List[str],
                        num_suggestions: int = 3) -> List[Dict[str, Any]]:
    """
    Get specific time suggestions for scheduling
    
    Args:
        student_availability: List of student availability strings
        professional_availability: List of professional availability strings
        num_suggestions: Number of suggestions to return
        
    Returns:
        List of time suggestion dictionaries
    """
    matcher = AvailabilityMatcher(MatchStrategy.FLEXIBLE)
    matches = matcher.find_matches(student_availability, professional_availability)
    return matcher.suggest_meeting_times(matches, num_suggestions)

# Example usage and testing
if __name__ == "__main__":
    # Test the matcher
    student_avail = [
        "Monday afternoon",
        "Wednesday 2-3 PM",
        "Friday morning"
    ]
    
    professional_avail = [
        "Monday 1-4 PM",
        "Wednesday afternoon",
        "Thursday 10 AM - 2 PM"
    ]
    
    print("=== Testing Availability Matcher ===")
    
    matches = find_availability_matches(student_avail, professional_avail)
    
    print(f"\nFound {len(matches)} matches:")
    for i, match in enumerate(matches, 1):
        print(f"\n{i}. Match Score: {match['match_score']:.2f}")
        print(f"   Student: {match['student_availability']}")
        print(f"   Professional: {match['professional_availability']}")
        print(f"   Overlap: {match['overlap_minutes']} minutes")
        print(f"   Type: {match['match_type']}")
    
    print("\n=== Time Suggestions ===")
    suggestions = get_time_suggestions(student_avail, professional_avail)
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}. {suggestion['day']} at {suggestion['time']}")
        print(f"   Duration: {suggestion['duration']} minutes")
        print(f"   Score: {suggestion['match_score']:.2f}")
        print(f"   Based on: {suggestion['description']}")
