from datetime import datetime, time
from typing import Optional
from ..models.models import Shop, WorkingHours, WorkingDay

def parse_time(time_str: str) -> time:
    """Convert a string in format 'HH:MM' to time object"""
    try:
        hours, minutes = map(int, time_str.strip().split(':'))
        return time(hour=hours, minute=minutes)
    except (ValueError, AttributeError):
        raise ValueError("Invalid time format. Expected 'HH:MM'")

def parse_legacy_working_hours(legacy_hours: dict) -> WorkingHours:
    """Convert the old working hours format to the new WorkingHours model"""
    working_hours = WorkingHours()
    
    day_mapping = {
        'Lunes-viernes': ['lunes', 'martes', 'miércoles', 'jueves', 'viernes'],
        'Lunes-sábado': ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'],
        'Sábado': ['sábado'],
        'Domingo': ['domingo']
    }
    
    for schedule, hours in legacy_hours.items():
        try:
            # Parse schedule like "07:30 - 18:00"
            open_time_str, close_time_str = hours.split('-')
            open_time = parse_time(open_time_str)
            close_time = parse_time(close_time_str)
            
            # Create WorkingDay instance
            working_day = WorkingDay(
                open_time=open_time,
                close_time=close_time,
                is_open=True
            )
            
            # Apply to all relevant days
            if schedule in day_mapping:
                for day in day_mapping[schedule]:
                    setattr(working_hours, day, working_day)
                    
        except (ValueError, AttributeError) as e:
            print(f"Error parsing working hours for {schedule}: {e}")
            continue
            
    return working_hours

def is_shop_open(shop: Shop) -> bool:
    """Check if a shop is currently open based on its working hours"""
    if not shop.working_hours:
        return False
        
    now = datetime.now()
    current_day = now.strftime('%A').lower()
    current_time = now.time()
    
    # Get the working hours for the current day
    day_schedule: Optional[WorkingDay] = getattr(shop.working_hours, current_day)
    
    if not day_schedule or not day_schedule.is_open:
        return False
        
    return day_schedule.open_time <= current_time <= day_schedule.close_time

def format_time(t: time) -> str:
    """Format a time object to 'HH:MM' string"""
    return t.strftime('%H:%M')

def format_working_hours(working_hours: Optional[WorkingHours]) -> Optional[dict]:
    """Format WorkingHours model to a human-readable dictionary"""
    if not working_hours:
        return None
        
    formatted = {}
    days = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
    
    for day in days:
        schedule = getattr(working_hours, day)
        if schedule and schedule.is_open:
            formatted[day] = f"{format_time(schedule.open_time)} - {format_time(schedule.close_time)}"
            
    return formatted 