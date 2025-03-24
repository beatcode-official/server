def get_users_from_db(room, db):
    users = {}
    users[room.host_id] = db.query(User).filter(User.id == room.host_id).first()
    if room.guest_id:
        users[room.guest_id] = db.query(User).filter(User.id == room.guest_id).first()
    return users