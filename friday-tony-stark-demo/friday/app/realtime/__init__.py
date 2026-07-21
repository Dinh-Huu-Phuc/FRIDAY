__all__ = ["SystemSocketBroadcaster", "SystemSocketManager", "create_system_socket_router"]


def __getattr__(name: str):
    if name == "create_system_socket_router":
        from .system_socket import create_system_socket_router

        return create_system_socket_router
    if name == "SystemSocketBroadcaster":
        from .system_socket_broadcaster import SystemSocketBroadcaster

        return SystemSocketBroadcaster
    if name == "SystemSocketManager":
        from .system_socket_manager import SystemSocketManager

        return SystemSocketManager
    raise AttributeError(name)
