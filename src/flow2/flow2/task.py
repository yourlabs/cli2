"""
Asynchronous task executor.

**Features**:

- subclass a Task to implement your own constructor and run code
- or use CallbackTask to create a task from a bare callback, sync or async
- parallel or serial task groups to nest tasks
- logging and colored output

Example:

.. code-block:: python

    import flow2

    async def your_callback1(context):
        return 'something'

    task = flow2.SerialTaskGroup(
        'Your workflow',
        flow2.ParallelTaskGroup(
            'Parallel task',
            flow2.CallbackTask('Task 1', your_callback1),
            flow2.CallbackTask('Task 2', your_callback2),
        ),
        flow2.ParallelTaskGroup(
            'Parallel task',
            YourTask('Task 3', your, args),
            flow2.CallbackTask('Task 4', your_callback4),
        ),
    )

    result = await task.run()

Result is a dict of the return value of each task, where the keys are
snake_cased conversion of the names, ie. 'Task 4' becomes 'task_4' in the
result dict.

The result dict is provisioned by the tasks as they run, and is passed to the
next running tasks. As such, in the above example, you are sure that
your_callback4 will have the 'task_3' key in the context when called.
"""


import asyncio
import cli2


class Task:
    """
    Base task class, don't use it directly.

    .. py:attribute:: name

        Task name in human readable format.

    .. py:attribute:: key

        lower_snake_cased conversion of the name
    """
    def __init__(self, name, description=None, register=None, output=True):
        """
        Instanciate a task.

        :param name: Name of the task
        """
        self.name = name
        self.description = description
        self.register = register
        self.output = output

    @property
    def key(self):
        return self.register or self.name.lower().replace(' ', '_')

    async def run(self, context):
        """
        You should override this in your own Task subclasses.

        :raises: NotImplementedError
        """
        raise NotImplementedError(
            'Cannot run bare task, inherit from task and define run'
            ' or use CallbackTask'
        )

    async def start(self, context):
        """
        Called when the task begins,  does printing and logging.

        :param context: context dict
        """
        cli2.log.debug('task begin', name=self.name)
        print(cli2.t.yellow.bold('STARTING') + ' ' + self.name)

    async def exception(self, exception, context, raises=True):
        """
        Called when the task raises an exception.

        :param execption: Raised exception
        :param context: context dict
        :param raises: wether to raise exception or not
        """
        context[self.key] = exception
        print(cli2.t.red.bold('FAILED') + ' ' + self.name)
        if raises:
            raise exception
        else:
            cli2.log.exception(exception)

    async def success(self, result, context):
        """
        Called when the task ends successfully,  does printing and logging.

        :param result: Result of the task run method
        :param context: context dict
        """
        cli2.log.info(
            'task success',
            name=self.name,
            result=result,
            context=context,
        )
        print(cli2.t.green.bold('SUCCESS') + ' ' + self.name)
        if result:
            context[self.key] = result
            if self.output:
                self.output_result(result)

    def output_result(self, result):
        cli2.print(result)

    async def process(self, context=None, raises=True):
        """
        Orchestrate the call to the :py:meth:`run` method.

        :param context: context dict
        :param raises: Wether to raise exceptions or not
        """
        context = context if context is not None else dict()

        await self.start(context)

        try:
            result = await self.run(context)
        except Exception as exc:
            await self.exception(exc, context, raises)
        else:
            await self.success(result, context)

        return context


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

    async def run(self, context):
        return await cli2.async_resolve(self.callback(context))


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
    async def run(self, context):
        await asyncio.gather(*[
            task.process(context, raises=False)
            for task in self.tasks
        ])


class SerialTaskGroup(TaskGroup):
    """
    Run tasks one after another, stop and fail if one fails.
    """
    async def run(self, context):
        for task in self.tasks:
            try:
                await task.process(context)
            except:   # noqa
                break
