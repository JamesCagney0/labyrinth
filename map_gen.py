"""
LABYRINTH — Map generator
"""
from __future__ import annotations
import logging
from typing import Dict, Set, TYPE_CHECKING

logger = logging.getLogger(__name__)

from constants import GameConstants
if TYPE_CHECKING:
    from player import Player
    from room import Room

class MapGenerator:
    """Generate ASCII visual map of explored rooms"""
    
    @staticmethod
    def generate_visual_map(floors: Dict[int, Dict[str, 'Room']], 
                           current_floor: int, 
                           current_room: str,
                           visited_rooms: Set[str]) -> str:
        """Generate expanded compass-style ASCII map for current floor"""
        floor_rooms = floors[current_floor]
        visited_floor = [r for r in visited_rooms if r in floor_rooms]
        
        if not visited_floor:
            return "No rooms explored on this floor yet!"
        
        current = floor_rooms[current_room]
        
        lines = []
        lines.append("╔" + "═" * 78 + "╗")
        lines.append(f"║ FLOOR {current_floor} COMPASS MAP - EXPANDED VIEW{' ' * (78 - len(f' FLOOR {current_floor} COMPASS MAP - EXPANDED VIEW'))}║")
        lines.append("╠" + "═" * 78 + "╣")
        
        # Get rooms in each direction from current room (with depth)
        def get_room_chain(direction, max_depth=2):
            """Get chain of rooms in a direction"""
            chain = []
            current_id = current_room
            
            for depth in range(max_depth):
                if current_id not in floor_rooms:
                    break
                    
                room = floor_rooms[current_id]
                if direction not in room.exits:
                    break
                
                target_id = room.exits[direction]
                if target_id not in floor_rooms:
                    break
                
                target_room = floor_rooms[target_id]
                is_visited = target_id in visited_rooms
                
                name = target_room.name[:18] if is_visited else "Unexplored"
                markers = []
                
                if is_visited:
                    if target_room.enemies:
                        markers.append("⚔")
                    if target_room.items:
                        markers.append("◆")
                else:
                    markers.append("?")
                
                chain.append({
                    'name': name,
                    'markers': " ".join(markers),
                    'visited': is_visited,
                    'depth': depth + 1
                })
                
                current_id = target_id
            
            return chain
        
        # Get room chains in all directions
        north_chain = get_room_chain('north')
        south_chain = get_room_chain('south')
        east_chain = get_room_chain('east')
        west_chain = get_room_chain('west')
        
        # Get special exits
        def get_special_info(direction):
            if direction in current.exits:
                target_id = current.exits[direction]
                target_room = floor_rooms.get(target_id)
                if target_room:
                    is_visited = target_id in visited_rooms
                    name = target_room.name[:18] if is_visited else "Unexplored"
                    markers = []
                    if is_visited:
                        if target_room.enemies:
                            markers.append("⚔")
                        if target_room.items:
                            markers.append("◆")
                    else:
                        markers.append("?")
                    return name, " ".join(markers), is_visited
            return None, None, False
        
        up_info = get_special_info('up')
        down_info = get_special_info('down')
        # secret_info intentionally not fetched — secret exits are hidden from the map
        
        # Build expanded compass display
        lines.append("║" + " " * 78 + "║")
        
        # NORTH CHAIN (show up to 3 rooms)
        if north_chain:
            lines.append("║" + " " * 33 + "[NORTH]" + " " * 38 + "║")
            for i, room_info in enumerate(reversed(north_chain)):
                depth_marker = "↑" * room_info['depth']
                room_line = f"║{' ' * 18}{depth_marker} {room_info['name']:<18}"
                if room_info['markers']:
                    room_line += f" {room_info['markers']:>4}"
                room_line += " " * (78 - len(room_line) + 1) + "║"
                lines.append(room_line)
            lines.append("║" + " " * 35 + "│" + " " * 42 + "║")
        
        # WEST-CENTER-EAST ROW
        west_display = ""
        east_display = ""
        
        # WEST CHAIN
        if west_chain:
            west_rooms = []
            for room_info in reversed(west_chain):
                depth_marker = "←" * room_info['depth']
                room_str = f"{room_info['name'][:12]:<12}"
                if room_info['markers']:
                    room_str += f" {room_info['markers']}"
                west_rooms.append(f"{room_str} {depth_marker}")
            west_display = " ".join(west_rooms)
        
        # CENTER (Current Room)
        current_name = current.name[:16]
        current_markers = []
        if current.enemies:
            current_markers.append("⚔")
        if current.items:
            current_markers.append("◆")
        marker_str = " ".join(current_markers) if current_markers else ""
        
        center_display = f"[ ►{current_name:<16}]"
        if marker_str:
            center_display += f" {marker_str}"
        
        # EAST CHAIN
        if east_chain:
            east_rooms = []
            for room_info in east_chain:
                depth_marker = "→" * room_info['depth']
                room_str = f"{room_info['name'][:12]:<12}"
                if room_info['markers']:
                    room_str += f" {room_info['markers']}"
                east_rooms.append(f"{depth_marker} {room_str}")
            east_display = " ".join(east_rooms)
        
        # Build center line
        center_line = "║"
        
        if west_display:
            center_line += f" {west_display}"
        else:
            center_line += " " * 2
        
        center_line += f" {center_display} "
        
        if east_display:
            center_line += f"{east_display}"
        
        # Pad to width
        padding = 78 - len(center_line) + 1
        if padding > 0:
            center_line += " " * padding
        center_line += "║"
        lines.append(center_line)
        
        # Direction labels
        label_line = "║"
        if west_chain:
            label_line += f"{' ' * 5}[WEST]"
        else:
            label_line += " " * 11
        
        label_line += " " * 30
        
        if east_chain:
            label_line += f"[EAST]"
        
        padding = 78 - len(label_line) + 1
        if padding > 0:
            label_line += " " * padding
        label_line += "║"
        lines.append(label_line)
        
        # SOUTH CHAIN
        if south_chain:
            lines.append("║" + " " * 35 + "│" + " " * 42 + "║")
            for room_info in south_chain:
                depth_marker = "↓" * room_info['depth']
                room_line = f"║{' ' * 18}{depth_marker} {room_info['name']:<18}"
                if room_info['markers']:
                    room_line += f" {room_info['markers']:>4}"
                room_line += " " * (78 - len(room_line) + 1) + "║"
                lines.append(room_line)
            lines.append("║" + " " * 33 + "[SOUTH]" + " " * 38 + "║")
        
        lines.append("║" + " " * 78 + "║")
        
        # Special exits at bottom
        special_dirs = []
        if up_info[0]:
            special_dirs.append(f"↑UP: {up_info[0][:20]} {up_info[1] or ''}")
        if down_info[0]:
            special_dirs.append(f"↓DOWN: {down_info[0][:20]} {down_info[1] or ''}")
        
        if special_dirs:
            lines.append("║ Special Exits:" + " " * 63 + "║")
            for spec in special_dirs:
                line = f"║   {spec}"
                padding = 78 - len(line) + 1
                line += " " * padding + "║"
                lines.append(line)
            lines.append("║" + " " * 78 + "║")
        
        # Floor overview of ALL rooms
        lines.append("╠" + "═" * 78 + "╣")
        lines.append("║ FLOOR OVERVIEW - All Rooms:" + " " * 49 + "║")
        lines.append("║" + " " * 78 + "║")
        
        # List all rooms with status
        all_rooms = []
        for room_id, room in floor_rooms.items():
            is_current = (room_id == current_room)
            is_visited = room_id in visited_rooms
            
            marker = "►" if is_current else ("○" if is_visited else "·")

            room_type = ""
            if 'boss' in room_id:
                room_type = "⚔BOSS"
            elif 'stairs' in room_id:
                room_type = "⬇STAIRS"
            elif room_id == 'start' or 'start' in room_id:
                room_type = "⬆START"
            elif 'secret' in room_id:
                room_type = ""

            # Hide name and type of undiscovered rooms — no spoilers
            display_name = room.name[:20] if is_visited else "???"
            display_type = room_type if is_visited else ""

            all_rooms.append({
                'marker': marker,
                'name': display_name,
                'type': display_type,
                'visited': is_visited,
                'sort_type': room_type  # keep original for sorting
            })
        
        # Sort: Start, Regular, Boss, Stairs, Secret
        def sort_key(r):
            if 'START' in r['sort_type']:
                return (0, r['name'])
            elif 'BOSS' in r['sort_type']:
                return (2, r['name'])
            elif 'STAIRS' in r['sort_type']:
                return (3, r['name'])
            elif 'SECRET' in r['sort_type']:
                return (4, r['name'])
            else:
                return (1, r['name'])
        
        all_rooms.sort(key=sort_key)
        
        # Display in two columns
        for i in range(0, len(all_rooms), 2):
            room1 = all_rooms[i]
            line = f"║ {room1['marker']} {room1['name']:<20}"
            if room1['type']:
                line += f" [{room1['type']}]"
            
            if i + 1 < len(all_rooms):
                room2 = all_rooms[i + 1]
                # Pad first column
                current_len = len(line) - 1  # Subtract the ║
                padding_needed = 40 - current_len
                if padding_needed > 0:
                    line += " " * padding_needed
                line += f"{room2['marker']} {room2['name']:<20}"
                if room2['type']:
                    line += f" [{room2['type']}]"
            
            # Final padding
            padding = 78 - len(line) + 1
            if padding > 0:
                line += " " * padding
            line += "║"
            lines.append(line)
        
        lines.append("║" + " " * 78 + "║")
        lines.append("╠" + "═" * 78 + "╣")
        
        # Stats and legend
        stats_line = f"║ Progress: {len(visited_floor)}/{len(floor_rooms)} rooms  |  Current Floor: {current_floor}"
        padding = 78 - len(stats_line) + 1
        lines.append(stats_line + " " * padding + "║")
        lines.append("║ ► = You  ○ = Visited  · = Undiscovered  ⚔ = Enemies  ◆ = Items            ║")
        lines.append("║ Depth arrows: → (1 room away)  →→ (2 rooms away)  →→→ (3 rooms away)         ║")
        lines.append("╚" + "═" * 78 + "╝")
        
        return '\n'.join(lines)

