"""Parser for tasks.md files following Spec-Kit format."""

import re
from pathlib import Path
from typing import Optional

from .models import Task, StoryGroup, Phase, TasksDocument


# Regex patterns for parsing
TITLE_PATTERN = re.compile(r'^# Tasks: (.+)$')
METADATA_INPUT_PATTERN = re.compile(r'^\*\*Input\*\*: (.+)$')
METADATA_BRANCH_PATTERN = re.compile(r'^\*\*Branch\*\*: `?(.+?)`?$')
PHASE_PATTERN = re.compile(r'^## Phase (\d+): (.+)$')
GROUP_PATTERN = re.compile(r'^### (.+?)(?:\s*\((US\d+)\))?$')
TASK_PATTERN = re.compile(
    r'^- \[([ Xx])\] (T\d{3,4})\s*(\[P\])?\s*(\[US\d+\])?\s*(.+)$'
)
PURPOSE_PATTERN = re.compile(r'^\*\*Purpose\*\*:?\s*(.+)$')
GOAL_PATTERN = re.compile(r'^\*\*Goal\*\*:?\s*(.+)$')
CHECKPOINT_PATTERN = re.compile(r'^\*\*Checkpoint\*\*:?\s*(.+)$')
INDEPENDENT_TEST_PATTERN = re.compile(r'^\*\*Independent Test\*\*:?\s*(.+)$')

# Extract priority from phase heading like "Priority: P1" or "(P1)"
PRIORITY_PATTERN = re.compile(r'(?:Priority:\s*)?(P\d)')
# Extract user story like "User Story 1" or "US1"
USER_STORY_PATTERN = re.compile(r'(?:User Story\s+(\d+)|(US\d+))')
# Check for MVP marker
MVP_MARKER = '🎯'

# File path pattern - matches things like "src/file.py" or "tests/test_file.py"
FILE_PATH_PATTERN = re.compile(r'\b[\w-]+(?:/[\w/.-]+)+\.\w+')


def extract_file_paths(text: str) -> list[str]:
    """Extract file paths from description text."""
    return FILE_PATH_PATTERN.findall(text)


def parse_phase_heading(heading: str, phase_number: int) -> tuple[str, Optional[str], Optional[str], bool]:
    """
    Parse phase heading to extract:
    - Title (cleaned)
    - Priority (e.g., "P1")
    - User Story (e.g., "US1")
    - Is MVP flag
    
    Example: "Phase 3: User Story 1 - Generate Connectors (Priority: P1) 🎯 MVP"
    Returns: ("User Story 1 - Generate Connectors", "P1", "US1", True)
    """
    title = heading.strip()
    priority = None
    user_story = None
    is_mvp = MVP_MARKER in heading
    
    # Extract priority
    if match := PRIORITY_PATTERN.search(heading):
        priority = match.group(1)
        # Clean it from title
        title = PRIORITY_PATTERN.sub('', title)
    
    # Extract user story
    if match := USER_STORY_PATTERN.search(heading):
        if match.group(1):  # "User Story 1" format
            user_story = f"US{match.group(1)}"
        else:  # "US1" format
            user_story = match.group(2)
    
    # Clean up title
    title = title.replace(MVP_MARKER, '').replace('MVP', '')
    title = title.replace('(Priority:', '').replace(')', '')
    title = title.strip()
    
    # Remove "Phase N: " prefix if present
    title = re.sub(r'^Phase \d+:\s*', '', title)
    
    return title, priority, user_story, is_mvp


def parse_tasks_md(content: str) -> TasksDocument:
    """
    Parse a tasks.md file and return a TasksDocument structure.
    
    Args:
        content: String content of the tasks.md file
        
    Returns:
        TasksDocument with parsed structure
    """
    lines = content.split('\n')
    
    # Initialize document
    doc = TasksDocument(title="Untitled")
    
    # State tracking
    current_phase: Optional[Phase] = None
    current_group: Optional[StoryGroup] = None
    phase_number = 0
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines and format description lines
        if not line_stripped or line_stripped.startswith('##') and 'Format:' in line_stripped:
            continue
        
        # Parse title
        if match := TITLE_PATTERN.match(line_stripped):
            doc.title = match.group(1).strip()
            continue
        
        # Parse metadata
        if match := METADATA_INPUT_PATTERN.match(line_stripped):
            doc.input_path = match.group(1).strip()
            continue
        
        if match := METADATA_BRANCH_PATTERN.match(line_stripped):
            doc.branch = match.group(1).strip()
            continue
        
        # Parse phase heading
        if match := PHASE_PATTERN.match(line_stripped):
            # Save current group to current phase before saving phase
            if current_group and current_phase:
                current_phase.groups.append(current_group)
            # Save previous phase
            if current_phase:
                doc.phases.append(current_phase)
            
            phase_number = int(match.group(1))
            phase_heading = match.group(2)
            
            title, priority, user_story, is_mvp = parse_phase_heading(phase_heading, phase_number)
            
            current_phase = Phase(
                number=phase_number,
                title=title,
                priority=priority,
                user_story=user_story,
                is_mvp=is_mvp
            )
            current_group = None
            continue
        
        # Parse story group heading (### headings within phases, not ####)
        if line_stripped.startswith('### ') and not line_stripped.startswith('#### ') and current_phase:
            if match := GROUP_PATTERN.match(line_stripped):
                # Save previous group if exists
                if current_group:
                    current_phase.groups.append(current_group)
                
                title = match.group(1).strip()
                user_story = match.group(2) if match.group(2) else None
                
                current_group = StoryGroup(title=title, user_story=user_story)
            continue
        
        # Parse phase metadata
        if current_phase and not current_group:
            if match := PURPOSE_PATTERN.match(line_stripped):
                current_phase.purpose = match.group(1).strip()
                continue
            if match := GOAL_PATTERN.match(line_stripped):
                current_phase.goal = match.group(1).strip()
                continue
            if match := CHECKPOINT_PATTERN.match(line_stripped):
                current_phase.checkpoint = match.group(1).strip()
                continue
            if match := INDEPENDENT_TEST_PATTERN.match(line_stripped):
                current_phase.independent_test = match.group(1).strip()
                continue
        
        # Parse task line
        if match := TASK_PATTERN.match(line_stripped):
            if not current_phase:
                continue  # Skip tasks not in a phase
            
            is_completed = match.group(1).upper() == 'X'
            task_id = match.group(2)
            is_parallel = match.group(3) is not None
            user_story_raw = match.group(4)
            description = match.group(5).strip()
            
            # Remove leading colon if present (e.g., "T001: description" -> "description")
            if description.startswith(':'):
                description = description[1:].strip()
            
            # Extract user story from [US1] format
            user_story = None
            if user_story_raw:
                user_story = user_story_raw.strip('[]')
            
            # Extract file paths
            file_paths = extract_file_paths(description)
            
            task = Task(
                id=task_id,
                description=description,
                is_completed=is_completed,
                is_parallel=is_parallel,
                user_story=user_story,
                file_paths=file_paths,
                phase_number=phase_number,
                group_title=current_group.title if current_group else None,
                raw_line=line_stripped
            )
            
            if current_group:
                current_group.tasks.append(task)
            else:
                current_phase.direct_tasks.append(task)
    
    # Add final phase and group
    if current_group and current_phase:
        current_phase.groups.append(current_group)
    if current_phase:
        doc.phases.append(current_phase)
    
    return doc


def parse_tasks_file(file_path: Path) -> TasksDocument:
    """
    Parse a tasks.md file from disk.
    
    Args:
        file_path: Path to the tasks.md file
        
    Returns:
        TasksDocument with parsed structure
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return parse_tasks_md(content)
