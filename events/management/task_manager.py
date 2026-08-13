from django.db.models import Q
from ..models import Task, TaskStatus
import logging

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self, user):
        logger.debug(f"TaskManager.__init__: Inicializando TaskManager para usuario {user.username} (ID: {user.id})")
        self.user = user
        logger.debug("TaskManager.__init__: Llamando a get_user_tasks()")
        self.user_tasks = self.get_user_tasks()
        logger.debug(f"TaskManager.__init__: Total de tareas del usuario: {self.user_tasks.count() if self.user_tasks else 0}")
        logger.debug("TaskManager.__init__: Llamando a get_active_status()")
        self.active_status = self.get_active_status()
        logger.debug(f"TaskManager.__init__: Estado activo obtenido: {self.active_status}")
        logger.debug("TaskManager.__init__: Inicialización completada")

    def get_user_tasks(self):
        logger.debug(f"get_user_tasks: Verificando rol del usuario {self.user.username}")
        if (
            hasattr(self.user, 'cv') and 
            hasattr(self.user.cv, 'role') and 
            self.user.cv.role == 'SU'
        ):
            logger.info(f"User {self.user.username} has role 'SU'. Fetching all tasks.")
            logger.debug("get_user_tasks: Obteniendo TODAS las tareas (rol SU)")
            tasks = Task.objects.all().order_by('-updated_at').select_related('task_status', 'project', 'event')
            logger.debug(f"get_user_tasks: Total de tareas obtenidas (rol SU): {tasks.count()}")
            return tasks
        else:
            logger.info(f"User {self.user.username} does not have role 'SU'. Fetching assigned tasks.")
            logger.debug("get_user_tasks: Obteniendo tareas asignadas (rol no SU)")
            tasks = Task.objects.filter(
                Q(assigned_to=self.user) | 
                Q(project__assigned_to=self.user) | 
                Q(event__assigned_to=self.user)
            ).distinct().order_by('-updated_at').select_related('task_status', 'project', 'event')
            logger.debug(f"get_user_tasks: Total de tareas obtenidas (rol no SU): {tasks.count()}")
            return tasks

    def get_active_status(self):
        logger.debug("get_active_status: Iniciando búsqueda de estado 'In Progress'")
        try:
            logger.debug("get_active_status: Intentando obtener TaskStatus con status_name='In Progress'")
            status = TaskStatus.objects.get(status_name='In Progress')
            logger.info(f"get_active_status: Estado 'In Progress' encontrado (ID: {status.id})")
            return status
        except TaskStatus.DoesNotExist:
            logger.error("get_active_status: El estado 'in_progress' no existe en la base de datos")
            print("The 'in_progress' status does not exist in the database.")
            return None
        except TaskStatus.MultipleObjectsReturned:
            logger.error("get_active_status: Se encontraron múltiples estados 'in_progress' en la base de datos")
            print("Multiple 'in_progress' statuses found in the database.")
            return None
        except Exception as e:
            logger.exception(f"get_active_status: Error inesperado al obtener estado activo: {e}")
            print(f"An error occurred: {e}")
            return None

    def get_task_data(self, task_id):
        logger.debug(f"get_task_data: Obteniendo datos para task_id={task_id}")
        task = self.user_tasks.filter(id=task_id).first()
        
        if task:
            logger.debug(f"get_task_data: Tarea encontrada - ID: {task.id}, Título: {task.title}")
            logger.debug(f"get_task_data: Proyecto asociado: {task.project}")
            logger.debug(f"get_task_data: Evento asociado: {task.event}")
            logger.debug(f"get_task_data: Estado de la tarea: {task.task_status}")
        else:
            logger.warning(f"get_task_data: No se encontró tarea con ID={task_id} o usuario no tiene acceso")

        return {
            'task': task,
            'project': task.project,
            'event': task.event,
            'status': task.task_status
        }

    def get_all_tasks(self):
        logger.debug("get_all_tasks: Iniciando obtención de todas las tareas")
        tasks = []
        active_tasks = []
        
        logger.debug(f"get_all_tasks: Procesando {self.user_tasks.count()} tareas del usuario")
        for index, task in enumerate(self.user_tasks, 1):
            logger.debug(f"get_all_tasks: Procesando tarea {index}/{self.user_tasks.count()} - ID: {task.id}")
            task_data = self.get_task_data(task.id)
            tasks.append(task_data)
            
            if self.active_status and task.task_status_id == self.active_status.id:
                logger.debug(f"get_all_tasks: Tarea ID {task.id} marcada como activa")
                active_tasks.append(task_data)
            else:
                logger.debug(f"get_all_tasks: Tarea ID {task.id} NO es activa (task_status_id={task.task_status_id}, active_status.id={self.active_status.id if self.active_status else 'None'})")
        
        logger.info(f"get_all_tasks: Total tareas: {len(tasks)}, Tareas activas: {len(active_tasks)}")
        return tasks, active_tasks

    def get_active_tasks(self):
        logger.debug("get_active_tasks: Iniciando obtención de tareas activas")
        if not self.active_status:
            logger.warning("get_active_tasks: No hay estado activo definido, retornando lista vacía")
            return []
        
        active_tasks = []
        for task in self.user_tasks:
            if task.task_status_id == self.active_status.id:
                logger.debug(f"get_active_tasks: Tarea ID {task.id} es activa")
                active_tasks.append(task)
        
        logger.info(f"get_active_tasks: Encontradas {len(active_tasks)} tareas activas")
        return active_tasks

    def create_task(self, title, description=None, important=False, project=None, event=None,
                    task_status=None, assigned_to=None, ticket_price=0.07):
        """
        Crear una nueva tarea usando el TaskManager con procedimientos correctos
        """
        from ..models import Task, TaskStatus, TaskState
        from django.utils import timezone
        from django.db import transaction, IntegrityError

        logger.info(f"create_task: Iniciando creación de tarea - Título: '{title}'")
        logger.debug(f"create_task: Parámetros - important={important}, project={project}, event={event}, ticket_price={ticket_price}")

        # Obtener el estado por defecto si no se especifica
        if task_status is None:
            logger.debug("create_task: task_status no proporcionado, buscando estado 'To Do'")
            try:
                task_status = TaskStatus.objects.get(status_name='To Do')
                logger.debug(f"create_task: Estado 'To Do' encontrado (ID: {task_status.id})")
            except TaskStatus.DoesNotExist:
                logger.warning("create_task: Estado 'To Do' no encontrado, usando primer estado disponible")
                task_status = TaskStatus.objects.first()
                if not task_status:
                    logger.error("create_task: No hay estados de tarea disponibles en la base de datos")
                    raise ValueError("No hay estados de tarea disponibles")
                logger.debug(f"create_task: Usando primer estado disponible (ID: {task_status.id}, Nombre: {task_status.status_name})")

        # Usar el usuario del manager si no se especifica assigned_to
        if assigned_to is None:
            assigned_to = self.user
            logger.debug(f"create_task: assigned_to no proporcionado, usando usuario actual (ID: {self.user.id})")
        else:
            logger.debug(f"create_task: Usando assigned_to proporcionado (ID: {assigned_to.id})")

        # No crear Event automáticamente. El campo event es opcional.
        # Si se desea asociar un Event, debe pasarse explícitamente.
        if event:
            logger.debug(f"create_task: Usando evento proporcionado (ID: {event.id})")
        else:
            logger.debug("create_task: Sin evento asociado")

        # Crear la tarea
        logger.debug("create_task: Creando objeto Task en base de datos")
        try:
            task = Task.objects.create(
                title=title,
                description=description or '',
                important=important,
                project=project,
                event=event,
                task_status=task_status,
                assigned_to=assigned_to,
                host=self.user,  # El host es siempre el usuario del manager
                ticket_price=ticket_price
            )
            logger.debug(f"create_task: Tarea creada exitosamente (ID: {task.id})")
        except Exception as e:
            logger.exception(f"create_task: Error al crear la tarea: {e}")
            raise

        # Crear el estado inicial de la tarea
        logger.debug("create_task: Creando estado inicial de la tarea (TaskState)")
        try:
            TaskState.objects.create(
                task=task,
                status=task_status,
                start_time=timezone.now()
            )
            logger.debug("create_task: TaskState creado exitosamente")
        except Exception as e:
            logger.exception(f"create_task: Error al crear TaskState: {e}")
            # No hacemos raise aquí para no perder la tarea creada, solo registramos el error

        logger.info(f"Task '{title}' created successfully by TaskManager for user {self.user.username} (Task ID: {task.id})")
        logger.debug("create_task: Proceso de creación de tarea completado")
        return task