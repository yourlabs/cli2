import cli2
from code2 import db


class ProjectDB:
    def __init__(self, project):
        self.project = project
        cli2.cfg.defaults.update(dict(
            CODE2_DB=f'sqlite+aiosqlite:///{project.path}/.code2/db.sqlite3',
        ))
        self._engine = None
        self._session = None
        self._session_factory = None

    def engine(self):
        if not self._engine:
            self._engine = db.create_async_engine(cli2.cfg["CODE2_DB"], echo=False)
        return self._engine

    async def session_factory(self):
        if not self._session_factory:
            async with self.engine().begin() as conn:
                await conn.run_sync(lambda connection: db.Base.metadata.create_all(connection, checkfirst=True))

            self._session_factory = db.async_sessionmaker(
                self.engine(),
                class_=db.AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory

    async def session(self):
        if not self._session:
            self._session = await self.session_make()
        return self._session

    async def session_make(self):
        return (await self.session_factory())()

    async def session_open(self):
        if not self._session:
            self._session = await self.session_factory()
        return self._session

    async def session_close(self):
        if self._session is not None:
            await self.engine().dispose()
