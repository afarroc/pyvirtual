# urls.py
from django.urls import path
from . import views
from .views import (
    RoomListViewSet, RoomDetailViewSet, RoomSearchViewSet,
    MessageListCreateAPIView, JoinRoomView, LeaveRoomView,
    room_view, navigate_room, create_room_connection, edit_room_connection,
    delete_room_connection, RoomCRUDViewSet, EntranceExitCRUDViewSet,
    PortalCRUDViewSet, RoomConnectionCRUDViewSet, object_action_panel,
    create_room_object, object_hotbar_types, room_object_list, box_detail,
    box_action
)

app_name = 'rooms'


urlpatterns = [
    # Main views
    path('', views.lobby, name='lobby'),
    path('register-presence/', views.register_presence, name='register_presence'),
    path('search/', views.room_search, name='room_search'),

    # Rooms
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/crud/', views.room_crud_view, name='room_crud'),
    path('rooms/create/', views.create_room, name='room_create'),
    path('rooms/create-complete/', views.create_room_complete, name='room_create_complete'),
    path('rooms/<int:pk>/', views.room_detail, name='room_detail'),
    path('rooms/<int:pk>/delete/', views.room_delete, name='room_delete'),
    path('rooms/<int:pk>/3d/', views.room_3d_view, name='room_3d'),
    path('rooms/<int:pk>/3d-interactive/', views.room_3d_interactive_view, name='room_3d_interactive'),
    path('rooms/<int:pk>/comments/', views.room_comments, name='room_comments'),
    path('rooms/<int:pk>/evaluations/', views.room_evaluations, name='room_evaluations'),

    # Portals
    path('portals/', views.portal_list, name='portal_list'),
    path('portals/create/', views.create_portal, name='portal_create'),
    path('portals/<int:pk>/', views.portal_detail, name='portal_detail'),

    # Entrance/Exits
    path('entrance-exits/', views.entrance_exit_list, name='entrance_exit_list'),
    path('entrance-exits/create/', views.create_entrance_exit, name='entrance_exit_create'),
    path('entrance-exits/<int:pk>/', views.entrance_exit_detail, name='entrance_exit_detail'),
    path('entrance-exits/<int:pk>/edit/', views.edit_entrance_exit, name='edit_entrance_exit'),
    path('entrance-exits/<int:pk>/delete/', views.delete_entrance_exit, name='delete_entrance_exit'),
    
    # Room Connections
    path('rooms/<int:room_id>/connections/create/', create_room_connection, name='create_room_connection'),
    path('rooms/<int:room_id>/connections/<int:connection_id>/edit/', edit_room_connection, name='edit_room_connection'),
    path('rooms/<int:room_id>/connections/<int:connection_id>/delete/', delete_room_connection, name='delete_room_connection'),

    # API Routes
    path('api/rooms/', RoomListViewSet.as_view({'get': 'list'}), name='room-list-api'),
    path('api/rooms/<int:pk>/', RoomDetailViewSet.as_view({'get': 'retrieve'}), name='room-detail-api'),
    path('api/rooms/search/', RoomSearchViewSet.as_view({'get': 'list'}), name='room-search-api'),

    # CRUD API Routes - Full REST API for Rooms
    path('api/crud/rooms/', RoomCRUDViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='room-crud-list'),
    path('api/crud/rooms/<int:pk>/', RoomCRUDViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='room-crud-detail'),

    # CRUD API Routes - Full REST API for EntranceExit (Doors)
    path('api/crud/doors/', EntranceExitCRUDViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='entrance-exit-crud-list'),
    path('api/crud/doors/<int:pk>/', EntranceExitCRUDViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='entrance-exit-crud-detail'),

    # CRUD API Routes - Full REST API for Portal
    path('api/crud/portals/', PortalCRUDViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='portal-crud-list'),
    path('api/crud/portals/<int:pk>/', PortalCRUDViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='portal-crud-detail'),

    # CRUD API Routes - Full REST API for RoomConnection
    path('api/crud/connections/', RoomConnectionCRUDViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='connection-crud-list'),
    path('api/crud/connections/<int:pk>/', RoomConnectionCRUDViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='connection-crud-detail'),
    path('api/rooms/<int:room_id>/messages/', MessageListCreateAPIView.as_view(), name='room-messages-api'),
    path('api/rooms/<int:room_id>/join/', JoinRoomView.as_view(), name='join-room-api'),
    path('api/rooms/<int:room_id>/leave/', LeaveRoomView.as_view(), name='leave-room-api'),
    
    # Transition System API Routes
    path('api/transitions/available/', views.get_available_transitions, name='available-transitions-api'),
    path('api/entrance/<int:entrance_id>/use/', views.use_entrance_exit, name='use-entrance-api'),
    path('api/entrance/<int:entrance_id>/info/', views.get_entrance_info, name='entrance-info-api'),
    path('api/teleport/<int:room_id>/', views.teleport_to_room, name='teleport-to-room-api'),
    path('api/navigation/history/', views.get_navigation_history, name='navigation-history-api'),
    path('api/user/current-room/', views.get_user_current_room, name='user-current-room-api'),

    # 3D Environment API Routes
    path('api/3d/rooms/<int:room_id>/data/', views.get_room_3d_data, name='room-3d-data-api'),
    path('api/3d/transition/', views.room_transition, name='room-transition-api'),
    path('api/3d/player/position/', views.update_player_position, name='update-player-position-api'),
    path('api/3d/player/status/', views.get_player_status, name='player-status-api'),

    # Basic 3D Environment
    path('3d-basic/', views.basic_3d_environment, name='basic_3d_environment'),

    # Navigation Test Zone
    path('navigation-test-zone/', views.create_navigation_test_zone, name='create_navigation_test_zone'),

   # ... otras URLs existentes ...
     path('room/', room_view, name='current_room'),
     path('room/<int:room_id>/', room_view, name='room_view'),
     path('navigate/<str:direction>/', navigate_room, name='navigate_room'),
     
      # Object Action Panel
      path('<int:room_id>/objects/panel/', object_action_panel, name='object_action_panel'),
      path('<int:room_id>/objects/create/', create_room_object, name='create_room_object'),
      path('api/objects/hotbar-types/', object_hotbar_types, name='object-hotbar-types'),

      # Room objects and boxes
      path('<int:room_id>/objects/', room_object_list, name='room_object_list'),
      path('boxes/<int:box_id>/', box_detail, name='box_detail'),
      path('boxes/<int:box_id>/action/', box_action, name='box_action'),
  ]

