import os
import eventlet
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, SocketIO, send
import random
from string import ascii_uppercase

eventlet.monkey_patch()

app = Flask(__name__)
app.config["SECRET_KEY"] = "^tfvs*(wy&(wu)wjp{w_iuw&fwyjnlw:k{w__}})"
socketio = SocketIO(app, async_mode="eventlet")

rooms = {}


def generate_unique_code(length) -> str:
    """Generates a unique code for a room"""
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code


@app.route("/", methods=["POST", "GET"])
def home():
    """Render home template"""
    session.clear()

    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template(
                "home.html", error="Please provide a name", code=code, name=name
            )
        if join != False and not code:
            return render_template(
                "home.html", error="Please provide a room code", code=code, name=name
            )

        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template(
                "home.html", error="Room does not exists.", code=code, name=name
            )

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")


@app.route("/room")
def room():
    """Handles chats in rooms"""
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])


@socketio.on("connect")
def connect(auth):
    """Handles new client connections"""
    room = session.get("room")
    name = session.get("name")

    if not room and not name:
        return

    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")


@socketio.on("disconnect")
def disconnect():
    """Handles disconnect from clients"""
    room = session.get("room")
    name = session.get("name")
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")


@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return

    content = {"name": session.get("name"), "message": data["data"]}
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
