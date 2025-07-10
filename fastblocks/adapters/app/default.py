import typing as t
from base64 import b64encode
from contextlib import asynccontextmanager, suppress
from time import perf_counter

from fastblocks.applications import FastBlocks

# Direct ACB imports - ACB is always available
from acb.adapters import get_adapter, import_adapter
from acb.config import Config
from acb.depends import depends
from ._base import AppBase, AppBaseSettings

# Import real ACB config to ensure we get the actual config
try:
    from acb.config import Config as RealConfig
    from acb.depends import depends as real_depends
except ImportError:
    RealConfig = Config
    real_depends = depends

main_start = perf_counter()

try:
    Cache, Storage = import_adapter()
except Exception:
    Cache = Storage = None


class AppSettings(AppBaseSettings):
    url: str = "http://localhost:8000"
    token_id: str | None = "_fb_"

    @depends.inject
    def __init__(self, config: t.Any = depends(), **data: t.Any) -> None:
        super().__init__(**data)
        self.url = self.url if not config.deployed else f"https://{self.domain}"
        token_prefix = self.token_id or "_fb_"
        self.token_id = "".join(
            [token_prefix, b64encode(self.name.encode()).decode().rstrip("=")]
        )


class FastBlocksApp(FastBlocks):
    """The actual FastBlocks application"""
    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(lifespan=self.lifespan, **kwargs)
    
    async def init(self) -> None:
        """Initialize the FastBlocks application"""
        # Simplified init for the wrapper
        pass
    
    async def post_startup(self) -> None:
        """Display app banner and startup information after startup"""
        try:
            from aioconsole import aprint
            from pyfiglet import Figlet
            from acb.depends import depends
            
            # Get app config
            config = depends.get("config")
            app_name = getattr(config.app, 'name', 'FastBlocks')
            app_title = getattr(config.app, 'title', 'Welcome to FastBlocks')
            app_domain = getattr(config.app, 'domain', 'localhost')
            
            # Calculate startup time 
            startup_time = getattr(self, '_startup_time', None)
            if startup_time is None or startup_time <= 0:
                # Fallback startup time calculation
                import time
                init_start = getattr(self, '_init_start_time', None)
                if init_start:
                    startup_time = time.time() - init_start
                else:
                    startup_time = 0.001  # Default fallback
            
            # Display figlet banner using original format (width=90, justify="center")
            fig = Figlet(font="slant", width=90, justify="center")
            banner = fig.renderText(app_name.upper())
            await aprint(f"\n\n{banner}\n")
            
            # Color codes
            GREEN = '\033[92m'
            BLUE = '\033[94m'
            YELLOW = '\033[93m'
            CYAN = '\033[96m'
            RESET = '\033[0m'
            BOLD = '\033[1m'
            
            # Get debug state info
            debug_enabled = []
            if hasattr(config, 'debug'):
                for key, value in vars(config.debug).items():
                    if value and key != 'production':
                        debug_enabled.append(key)
            debug_state = f"Debug: {', '.join(debug_enabled) if debug_enabled else 'disabled'}"
            
            # Center the info text with colors using the same width as figlet (90)
            info_lines = [
                f"{CYAN}{BOLD}{app_title}{RESET}",
                f"{BLUE}Domain: {app_domain}{RESET}",
                f"{YELLOW}Debug: {', '.join(debug_enabled) if debug_enabled else 'disabled'}{RESET}",
                f"{YELLOW}══════════════════════════════════════════════════{RESET}",
                f"{GREEN}🚀 FastBlocks Application Ready{RESET}",
                f"{YELLOW}⚡ Startup time: {startup_time*1000:.2f}ms{RESET}",
                f"{CYAN}🌐 Server running on http://127.0.0.1:8000{RESET}",
                f"{YELLOW}══════════════════════════════════════════════════{RESET}"
            ]
            
            for line in info_lines:
                # Calculate line width without ANSI codes
                line_clean = line.replace(GREEN, '').replace(BLUE, '').replace(YELLOW, '').replace(CYAN, '').replace(RESET, '').replace(BOLD, '')
                line_width = len(line_clean)
                # Use the same centering logic as figlet (width=90)
                padding = max(0, (90 - line_width) // 2)
                centered_line = ' ' * padding + line
                print(centered_line)
            print()
            
        except Exception as e:
            # Fallback to simple text banner if pyfiglet fails
            try:
                from acb.depends import depends
                config = depends.get("config")
                app_name = getattr(config.app, 'name', 'FastBlocks')
                startup_time = getattr(self, '_startup_time', None)
                if startup_time is None or startup_time <= 0:
                    startup_time = 0.001
                print(f"\n  ══════════════════════════════════════════════════")
                print(f"  🚀 {app_name.upper()} Application Ready")
                print(f"  ⚡ Startup time: {startup_time*1000:.2f}ms")
                print(f"  🌐 Server running on http://127.0.0.1:8000") 
                print(f"  ══════════════════════════════════════════════════")
                print()
            except Exception:
                print(f"\n  🚀 FastBlocks Application Ready")
                print()
    
    @asynccontextmanager
    async def lifespan(self, app: "FastBlocks") -> t.AsyncIterator[None]:
        """Lifespan context manager for FastBlocks application startup and shutdown."""
        try:
            # Startup sequence - simplified for wrapper
            if hasattr(self, 'logger'):
                self.logger.info("FastBlocks application starting up")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error during startup: {e}")
            raise e
        yield
        # Shutdown sequence
        if hasattr(self, 'logger'):
            self.logger.info("FastBlocks application shutting down")


class App(AppBase):
    """ACB adapter that wraps the FastBlocks application"""
    # ACB adapter fields  
    router: t.Any = None
    middleware_manager: t.Any = None
    templates: t.Any = None
    models: t.Any = None
    exception_handlers: t.Any = None
    middleware_stack: t.Any = None
    user_middleware: t.Any = None
    fastblocks_app: t.Any = None
    
    
    def __init__(self, **kwargs: t.Any) -> None:
        # Initialize AdapterBase
        super().__init__(**kwargs)
        
        # Create the actual FastBlocks application
        self.fastblocks_app = FastBlocksApp()
        
        # Initialize ACB adapter fields
        self.router = None
        self.middleware_manager = None
        self.templates = None
        self.models = None
        self.exception_handlers = {}
        self.middleware_stack = None
        self.user_middleware = []
        self.state = None
    
    @property
    def logger(self):
        """Ensure logger is available by providing a fallback."""
        if hasattr(super(), 'logger'):
            try:
                return super().logger
            except Exception:
                pass
        # Fallback to getting logger from dependencies
        try:
            Logger = depends.get("logger")
            return Logger
        except Exception:
            # Ultimate fallback to standard logging
            import logging
            return logging.getLogger(self.__class__.__name__)

    async def init(self) -> None:
        # Track startup time
        import time
        self._init_start_time = time.time()
        
        # Initialize the FastBlocks application
        await self.fastblocks_app.init()
        
        # Set the required ACB adapter fields
        try:
            self.templates = depends.get("templates")
        except Exception:
            self.templates = None
            
        try:
            self.models = depends.get("models")
        except Exception:
            self.models = None
            
        try:
            routes_adapter = depends.get("routes")
            self.router = routes_adapter
            # Also add routes to the FastBlocks app
            self.fastblocks_app.routes.extend(routes_adapter.routes)
        except Exception:
            self.router = None
            
        # Set additional required fields from the FastBlocks app
        self.middleware_manager = None
        self.exception_handlers = self.fastblocks_app.exception_handlers
        self.middleware_stack = self.fastblocks_app.middleware_stack  
        self.user_middleware = self.fastblocks_app.user_middleware
        self.state = self.fastblocks_app.state
        
        # Calculate startup time
        import time
        self._startup_time = time.time() - self._init_start_time
        
        # Pass startup time to the FastBlocks app
        self.fastblocks_app._startup_time = self._startup_time
        self.fastblocks_app._init_start_time = self._init_start_time
        
        # Call post_startup to display banner and startup info
        await self.post_startup()

    def __call__(self, scope, receive, send):
        """Make the adapter callable like a Starlette app"""
        return self.fastblocks_app(scope, receive, send)
    
    def __getattr__(self, name):
        """Delegate attribute access to the FastBlocks app"""
        return getattr(self.fastblocks_app, name)

    async def post_startup(self) -> None:
        # Delegate to the FastBlocks app
        await self.fastblocks_app.post_startup()

    def _setup_admin_adapter(self, app: FastBlocks) -> None:
        if not get_adapter("admin"):
            return
        sql = depends.get()
        auth = depends.get()
        admin = depends.get()
        admin.__init__(
            app,
            engine=sql.engine,
            title=self.config.admin.title,
            debug=getattr(self.config.debug, "admin", False),
            base_url=self.config.admin.url,
            logo_url=self.config.admin.logo_url,
            authentication_backend=auth,
        )
        self.router.routes.insert(0, self.router.routes.pop())

    async def _startup_sequence(self, app: FastBlocks) -> None:
        self._setup_admin_adapter(app)
        await self.post_startup()
        main_start_time = perf_counter() - main_start
        self.logger.warning(f"App started in {main_start_time} s")

    async def _shutdown_logger(self) -> None:
        import asyncio

        completer = None
        if hasattr(self.logger, "complete"):
            completer = getattr(self.logger, "complete")()
        elif hasattr(self.logger, "stop"):
            completer = getattr(self.logger, "stop")()
        if completer:
            await asyncio.wait_for(completer, timeout=1.0)

    def _cancel_remaining_tasks(self) -> None:
        import asyncio

        loop = asyncio.get_event_loop()
        tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
        if tasks:
            self.logger.debug(f"Cancelling {len(tasks)} remaining tasks")
            for task in tasks:
                task.cancel()

    @asynccontextmanager
    async def lifespan(self, app: FastBlocks) -> t.AsyncIterator[None]:
        try:
            await self._startup_sequence(app)
        except Exception as e:
            self.logger.error(f"Error during startup: {e}")
            raise e
        yield
        self.logger.critical("Application shut down")
        try:
            await self._shutdown_logger()
        except TimeoutError:
            self.logger.warning("Logger completion timed out, forcing shutdown")
        except Exception as e:
            self.logger.error(f"Logger completion failed: {e}")
        finally:
            with suppress(Exception):
                self._cancel_remaining_tasks()


with suppress(Exception):
    depends.set(App)
