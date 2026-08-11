#!/usr/bin/env python
"""Verificación post-migración Room → Cell en Management360."""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from rooms.models import Cell, CellConnection, PlayerProfile, Message, Comment, Evaluation
from chat.models import UserPresence
from bitacora.models import BitacoraEntry


def check_cells_rooms():
    rooms = Cell.objects.filter(cell_type='ROOM')
    print(f"[OK] Cells tipo ROOM: {rooms.count()}")
    for cell in rooms[:5]:
        print(f"  - {cell.id}: {cell.name}")


def check_player_profiles():
    profiles = PlayerProfile.objects.select_related('current_room').all()
    bad = [p for p in profiles if p.current_room and p.current_room.cell_type != 'ROOM']
    print(f"[OK] PlayerProfile total: {profiles.count()}, con current_room incorrecto: {len(bad)}")
    for p in bad[:5]:
        print(f"  - user={p.user_id} current_room={p.current_room_id} tipo={p.current_room.cell_type}")


def check_cell_connections():
    connections = CellConnection.objects.all()
    print(f"[OK] CellConnection total: {connections.count()}")
    for c in connections[:5]:
        print(f"  - {c.from_cell_id} -> {c.to_cell_id} via {c.entrance_id}")


def check_messages_comments_evaluations():
    msgs = Message.objects.count()
    comments = Comment.objects.count()
    evals = Evaluation.objects.count()
    orphan_msgs = Message.objects.filter(room__cell_type__isnull=True).count()
    orphan_comments = Comment.objects.filter(room__cell_type__isnull=True).count()
    orphan_evals = Evaluation.objects.filter(room__cell_type__isnull=True).count()
    print(f"[OK] Messages: {msgs} (huérfanos: {orphan_msgs})")
    print(f"[OK] Comments: {comments} (huérfanos: {orphan_comments})")
    print(f"[OK] Evaluations: {evals} (huérfanos: {orphan_evals})")


def check_user_presence():
    presences = UserPresence.objects.select_related('current_room').all()
    bad = [up for up in presences if up.current_room and up.current_room.cell_type != 'ROOM']
    print(f"[OK] UserPresence total: {presences.count()}, con current_room incorrecto: {len(bad)}")
    for up in bad[:5]:
        print(f"  - user={up.user_id} current_room={up.current_room_id}")


def check_bitacora():
    entries = BitacoraEntry.objects.select_related('related_room').all()
    bad = [e for e in entries if e.related_room and e.related_room.cell_type != 'ROOM']
    print(f"[OK] BitacoraEntry total: {entries.count()}, con related_room incorrecto: {len(bad)}")
    for e in bad[:5]:
        print(f"  - {e.id} related_room={e.related_room_id}")


def main():
    print("=== Verificación post-migración Room → Cell ===\n")
    try:
        check_cells_rooms()
        print()
        check_player_profiles()
        print()
        check_cell_connections()
        print()
        check_messages_comments_evaluations()
        print()
        check_user_presence()
        print()
        check_bitacora()
        print("\n=== Verificación completada ===")
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
