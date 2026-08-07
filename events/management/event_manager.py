from django.db.models import Q
from ..models import Event, Status, Project, Task

class EventManager:
    def __init__(self, user):
        self.user = user
        self.user_events = self.get_user_events()
        self.projects_by_event = self.get_projects_by_event()
        self.tasks_by_event = self.get_tasks_by_event()
        self.active_status = self.get_active_status()

    def get_user_events(self):
        if hasattr(self.user, 'profile') and hasattr(self.user.profile, 'role') and self.user.profile.role == 'SU':
            return Event.objects.all().order_by('-updated_at')
        else:
            return Event.objects.filter(
                Q(assigned_to=self.user) | Q(attendees=self.user)
            ).distinct().order_by('-updated_at')

    def get_projects_by_event(self):
        projects = Project.objects.filter(event_id__in=self.user_events.values_list('id', flat=True)).select_related('project_status')

        projects_by_event = {}
        for project in projects:
            if project.event_id not in projects_by_event:
                projects_by_event[project.event_id] = []
            projects_by_event[project.event_id].append(project)
        
        return projects_by_event

    def get_tasks_by_event(self):
        tasks = Task.objects.filter(event_id__in=self.user_events.values_list('id', flat=True)).select_related('task_status')

        tasks_by_event = {}
        for task in tasks:
            if task.event_id not in tasks_by_event:
                tasks_by_event[task.event_id] = []
            tasks_by_event[task.event_id].append(task)
        
        return tasks_by_event

    def get_active_status(self):
        # Attempt to retrieve the 'In Progress' status
        try:
            return Status.objects.get(status_name='In Progress')
        # Handle the exception when the status does not exist
        except Status.DoesNotExist:
            print("The 'in_progress' status does not exist in the database.")
            return None
        # Handle the exception when multiple 'In Progress ' statuses are found
        except Status.MultipleObjectsReturned:
            print("Multiple 'in_progress' statuses found in the database.")
            return None
        # Catch any other unexpected exceptions
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def get_event_data(self, event):
        projects = self.projects_by_event.get(event.id, [])
        tasks = self.tasks_by_event.get(event.id, [])
        projects_in_progress = [project for project in projects if project.project_status.status_name == 'In Progress']
        tasks_in_progress = [task for task in tasks if task.task_status.status_name == 'In Progress']
        return {
            'event': event,
            'count_projects': len(projects),
            'count_tasks': len(tasks),
            'count_projects_in_progress': len(projects_in_progress),
            'count_tasks_in_progress': len(tasks_in_progress),
            'projects': projects,
            'tasks': tasks
        }

    def get_event_by_id(self, event_id):
        try:
            event = Event.objects.get(id=event_id)
            event_data = self.get_event_data(event)
            return event_data
        except Event.DoesNotExist:
            return None

    def get_all_events(self):
        events = []
        active_events = []
        active_status_id = self.active_status.id if self.active_status else None
        for event in self.user_events:
            event_data = self.get_event_data(event)
            events.append(event_data)
            if active_status_id and event.event_status_id == active_status_id:
                active_events.append(event_data)
        
        return events, active_events
