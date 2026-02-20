"""Data models for tasks.md parsing."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    """Represents a single task from tasks.md."""
    
    id: str  # e.g., "T001"
    description: str
    is_completed: bool
    is_parallel: bool
    user_story: Optional[str]  # e.g., "US1"
    file_paths: list[str]
    phase_number: int
    group_title: Optional[str] = None
    raw_line: str = ""  # Original line for reference


@dataclass
class StoryGroup:
    """Represents a story group (### heading) within a phase."""
    
    title: str
    user_story: Optional[str]  # e.g., "US1"
    tasks: list[Task] = field(default_factory=list)


@dataclass
class Phase:
    """Represents a phase (## heading) in tasks.md."""
    
    number: int
    title: str
    purpose: Optional[str] = None
    goal: Optional[str] = None
    checkpoint: Optional[str] = None
    independent_test: Optional[str] = None
    priority: Optional[str] = None  # e.g., "P1"
    user_story: Optional[str] = None  # e.g., "US1"
    is_mvp: bool = False
    groups: list[StoryGroup] = field(default_factory=list)
    direct_tasks: list[Task] = field(default_factory=list)
    
    @property
    def all_tasks(self) -> list[Task]:
        """Get all tasks in this phase (from groups and direct)."""
        tasks = list(self.direct_tasks)
        for group in self.groups:
            tasks.extend(group.tasks)
        return tasks


@dataclass
class TasksDocument:
    """Represents the entire tasks.md document."""
    
    title: str
    input_path: Optional[str] = None
    branch: Optional[str] = None
    phases: list[Phase] = field(default_factory=list)
    
    @property
    def all_tasks(self) -> list[Task]:
        """Get all tasks across all phases."""
        tasks = []
        for phase in self.phases:
            tasks.extend(phase.all_tasks)
        return tasks
    
    @property
    def task_count(self) -> int:
        """Total number of tasks."""
        return len(self.all_tasks)
    
    @property
    def completed_count(self) -> int:
        """Number of completed tasks."""
        return sum(1 for task in self.all_tasks if task.is_completed)


@dataclass
class DependencyGraph:
    """Represents task dependencies."""
    
    # Maps task ID to list of task IDs it depends on (blocking tasks)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    
    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a dependency: task_id depends on depends_on."""
        if task_id not in self.dependencies:
            self.dependencies[task_id] = []
        if depends_on not in self.dependencies[task_id]:
            self.dependencies[task_id].append(depends_on)
    
    def get_blockers(self, task_id: str) -> list[str]:
        """Get list of task IDs that block this task."""
        return self.dependencies.get(task_id, [])
    
    def has_dependencies(self, task_id: str) -> bool:
        """Check if a task has any dependencies."""
        return task_id in self.dependencies and len(self.dependencies[task_id]) > 0
