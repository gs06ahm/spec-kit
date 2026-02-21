"""Build dependency graph from tasks.md structure."""

from typing import Optional

from .models import TasksDocument, DependencyGraph, Task


def build_dependency_graph(document: TasksDocument) -> DependencyGraph:
    """
    Build a dependency graph from the parsed tasks document.
    
    Dependency rules (from Spec-Kit conventions):
    1. Within a phase:
       - Sequential tasks: each depends on the previous non-parallel task
       - Parallel tasks [P]: all depend on the last sequential "anchor" task
       - Parallel tasks do NOT block each other
    
    2. Across phases:
       - The first task of Phase N depends on the last task of Phase N-1
    
    Args:
        document: Parsed TasksDocument
        
    Returns:
        DependencyGraph with all dependencies mapped
    """
    graph = DependencyGraph()
    
    # Track last task across phases for phase boundaries
    last_task_of_previous_phase: Optional[str] = None
    
    for phase in document.phases:
        all_tasks = phase.all_tasks
        
        if not all_tasks:
            continue
        
        # Add cross-phase dependency
        if last_task_of_previous_phase:
            first_task = all_tasks[0]
            graph.add_dependency(first_task.id, last_task_of_previous_phase)
        
        # Track dependencies within this phase
        last_sequential_task: Optional[Task] = None
        parallel_group_anchor: Optional[Task] = None
        
        for task in all_tasks:
            if not task.is_parallel:
                # Sequential task
                if last_sequential_task:
                    # Sequential task depends on previous sequential task
                    graph.add_dependency(task.id, last_sequential_task.id)
                
                # Update trackers
                last_sequential_task = task
                parallel_group_anchor = task
            else:
                # Parallel task
                if parallel_group_anchor:
                    # Parallel task depends on the anchor (last sequential task)
                    graph.add_dependency(task.id, parallel_group_anchor.id)
                # Do NOT update last_sequential_task - parallel tasks don't block
        
        # Remember last task for next phase boundary
        if last_sequential_task:
            last_task_of_previous_phase = last_sequential_task.id
        elif all_tasks:
            # If phase has only parallel tasks, use the last one
            last_task_of_previous_phase = all_tasks[-1].id
    
    return graph
