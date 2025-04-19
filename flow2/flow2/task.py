"""
Asynchronous task task_queue to create efficient automated workflows.

**Features**:

- subclass a Task to implement your own constructor and run code
- or use CallbackTask to create a task from a bare callback, sync or async
- parallel or serial task groups to nest tasks
- logging and colored output
- uses :py:class:`cli2.queue.Queue` so you can control the number or workers,
  which is cpucount*2 by default, and spawn new tasks on the fly

Example:

.. code-block:: python

    import flow2

    async def your_callback1(task_queue, context):
        return 'something'

    queue = flow2.TaskQueue(
        'Your workflow',
        flow2.ParallelTaskGroup(
            'Parallel task',
            flow2.CallbackTask('Task 1', your_callback1),
            flow2.CallbackTask('Task 2', your_callback2),
        ),
        flow2.SerialTaskGroup(
            'Parallel task',
            YourTask('Task 3', your, args),
            flow2.CallbackTask('Task 4', your_callback4),
        ),
    )

    result = await queue.run()

Result is a dict of the return value of each task, where the keys are
snake_cased conversion of the names, ie. 'Task 4' becomes 'task_4' in the
result dict.

The result dict is provisioned by the tasks as they run, and is passed to the
next running tasks. As such, in the above example, you are sure that
your_callback4 will have the 'task_3' key in the context when called.
"""


from cli2.queue import Queue
from cli2.asyncio import async_resolve
from cli2.theme import t
from cli2.log import log


class Task:
    """
    Base task class, don't use it directly.

    .. py:attribute:: name

        Task name in human readable format.

    .. py:attribute:: key

        lower_snake_cased conversion of the name
    """

    def __init__(self, name, description=None, output=None):
        """
        Instanciate a task.

        :param name: Name of the task
        """
        self.name = name
        self.description = description
        self.output = output

    @property
    def key(self):
        return self.output or self.name.lower().replace(' ', '_')

    async def run(self, task_queue, context):
        """
        You should override this in your own Task subclasses.

        :raises: NotImplementedError
        """
        raise NotImplementedError(
            'Cannot run bare task, inherit from task and define run'
            ' or use CallbackTask'
        )

    async def start(self, task_queue, context):
        """
        Called when the task begins,  does printing and logging.

        :param task_queue: :py:class:`TaskQueue` object
        :param context: Context dict
        """
        log.debug('task begin', name=self.name)
        if task_queue.printer:
            task_queue.printer(t.yellow.bold('STARTING') + ' ' + self.name)

    async def exception(self, exception, task_queue, context, reraise=True):
        """
        Called when the task raises an exception.

        :param execption: Raised exception
        :param reraise: Wether to re-raise the exception or to swallow it
        :param task_queue: :py:class:`TaskQueue` object
        :param context: Context dict
        """
        if task_queue.printer:
            task_queue.printer(t.red.bold('FAILED') + ' ' + self.name)
        context[self.key] = exception
        if reraise:
            raise

    async def success(self, result, task_queue, context):
        """
        Called when the task ends successfully,  does printing and logging.

        :param result: Result of the task run method
        :param task_queue: :py:class:`TaskQueue` object
        :param context: Context dict
        """
        log.info('task success', name=self.name)
        if task_queue.printer:
            task_queue.printer(t.green.bold('SUCCESS') + ' ' + self.name)

    async def process(self, task_queue, context):
        """
        Actual function to add to the :py:class:`cli2.queue.Queue`.

        Orchestrate the call to the :py:meth:`run` method.

        :param task_queue: :py:class:`TaskQueue` object
        :param context: Context dict
        """
        await self.start(task_queue, context)

        try:
            result = await self.run(task_queue, context)
        except Exception as exc:
            await self.exception(exc, task_queue, context)
            return

        if result:
            log.info(self.name, result=result)
            context[self.key] = result

        await self.success(result, task_queue, context)

        return result


class CallbackTask(Task):
    """
    Task decorating a callback

    .. py:attribute:: callback

        Sync or async task callback, result will be processed by
        :py:func:`cli2.asyncio.async_resolve`.
    """
    def __init__(self, name, callback, **kwargs):
        if not callable(callback):
            raise TypeError(f'{callback} must be callable')
        self.callback = callback
        super().__init__(name, **kwargs)

    async def run(self, task_queue, context):
        return await async_resolve(self.callback(task_queue, context))


class TaskGroup(Task):
    """
    Base TaskGroup, don't use this directly.

    Instead, use :py:class:`ParallelTaskGroup` or :py:class:`SerialTaskGroup`.

    .. py:attribute:: tasks

        Task objects
    """
    def __init__(self, name, *tasks, **kwargs):
        self.tasks = tasks
        super().__init__(name, **kwargs)


class ParallelTaskGroup(TaskGroup):
    """
    Run tasks in parallel without caring about success or failures.
    """
    async def run(self, task_queue, context):
        for task in self.tasks:
            await task_queue.queue.put(task.process(task_queue, context))


class SerialTaskGroup(TaskGroup):
    """
    Run tasks one after another, stop and fail if one fails.
    """
    async def run(self, task_queue, context):
        for task in self.tasks:
            await task.process(task_queue, context)


class TaskQueue:
    """
    Actual task executor.

    .. py:attribute:: name

        Name of the task executor

    .. py:attribute:: tasks

        Task objects

    .. py:attribute:: queue

        :py:class:`cli2.queue.Queue` object.

    .. py:attribute:: printer

        print() builtin function by default, if None, will not be called. Set
        printer=None for silent mode (logging will still be enabled).
    """
    def __init__(self, name, *tasks, queue=None, printer=print):
        self.name = name
        self.tasks = tasks
        self.queue = queue or Queue()
        self.printer = printer

    async def run(self, context=None):
        """
        Run the task queue with a given context dict if any.

        :param context: Context dict that will be passed to every task.
        :return: Context dict
        """
        context = context or dict()
        await self.queue.run(*[
            task.process(self, context)
            for task in self.tasks
        ])
        return context
