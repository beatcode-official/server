# BeatCode Backend Documentation

### General Notes
⚠️ FastAPI automatically generates Swagger-style documentation at /docs for all the HTTP endpoints (no WebSockets).

⚠️ The default API endpoint starts with `/api` (after your host address) 

⚠️ The URL suffix matters! When connecting to HTTP endpoints you'll use `http://` but whe connecting to WS endpoints you'll use `ws://`. The secure version of these protocols are `https://` and `wss://`, respectively.


### Frontend Integration Guide
Refer to this in addition to the Swagger docs to have a better idea on how to utilize the endpoints (and what to expect).

#### 1. Fresh Start
1. Users will register via `/users/register`, they will receive a token sent via email
2. Verify the account via `/users/verify-email/{token}`, otherwise they won't be able to log in.
3. Login via `/users/login` to obtain an access token and a refresh token
   1. Access Token:
      - This will be your authorization tool, in every authenticated endpoint include a header with the following format
      ```"Authorization": "Bearer <JWT_ACCESS_TOKEN>"```
      - Access tokens have a really short lifespan, when it expires you must acquire a new one (see Refresh Token)
   2. Refresh Token:
      - This token has a much longer life span, and is used to obtain new access tokens via `/users/refresh/`
      - Make sure to store this token securely (`HttpOnly` cookies) to prevent exposure via JavaScript injection or XSS.

ALTERNATIVELY: Send a POST request to `/api/users/guest` to get `access_token` and `refresh_token` of a guest account. Guest accounts cannot change display name, password. The rest behaves as normal.

#### 2. Forgot Password
1. If forgotten password, send the user's email to `/users/forgot-password` and they'll receive an email with a token
2. Supply the token and a new password to `/users/reset-password` to change the account's password. Changing the password will immediatey invalidate ALL access tokens and refresh tokens.

#### 3. User Management
1. Users can send a GET, PATCH, DELETE to `/users/me/` to read, update (change display name only), and delete their account, respectively.
2. Access tokens are stateless and can't be disabled individually, so log out via `/users/logout/` to invalidate the given refresh token and prevent it from generating any more access tokens.

#### 4. Matchmaking and Game Flow
1. To start queueing for a match, join the WebSocket endpoint `/game/queue` (unranked) or `/game/ranked-queue`  (ranked).
   - These two are pretty much the same, except ranked games are matched based on rating proximity and give rating changes.
   - The problems distribution in unranked matches are based on appearance chances, but in ranked the distribution of problemsare predetermined (check .env settings)
2. Once a match is found, a WebSocket JSON object of `type: "match_found"` will be sent to you. Inside `data` includes information like your `"match_id"` and opponent details. 
3. Use the mentioned `"match_id"` to connect to the WebSocket of the game e.g. `/game/play/{match_id}`
4. While inside the game websocket, here are the messages you'll receive:
   - `type: "game_state"`: sent on join/query; contains information about the current state of the game (you and your opponent)
   - `type: "problem"`: sent on join/when your current problem is solved; contains description of the current problem you must solve
   - `type: "submission_result"`: sent after you submit your code; contains the result of the execution of your code on hidden test cases (and errors if there are any)
   - `type: "match_end"`: sent when match ends; contains the final information about the match like winner, rating changes, etc.
   - `type: "error"`: sent when your messages causes an error; contains error message
   - `type: "chat"`: sent when you or your opponent sends a message.
5. And here are the messages you can send, note that after the game finishes, the server won't accept any more messages (even though WS is still open):
   - `type: "submit"`: used to submit your code for execution. Inside your `"data"` property:
     - `code: string`: your code string (includes boilerplate)
   - `type: "forfeit"`: used to forfeit the match
   - `type: "query"`: used to fetch current match data. Inside your `"data"` property:
     - `action: string`: either `buy` or `use`
     - `ability_id: string`: the ID string of the ability
   - `type: "chat"`: used to send a message to your opponent in the game room. Inside your `"data"` property:
     - `message: string`: the message you want to send

#### 5. Reconnection
- The backend introduces the `GET` endpoint `/game/current-game` to get the authorized user's current match (if Any).
- Hence, I suggest the frontend performs this fetch every visit and "throws" the player back into the game in progress if a game is found.

#### 6. Custom Room Creation and Management
1. Check the RoomSettings object to determine how your room creation settings UI will look like.
2. Include those settings as a JSON body dict inside your `POST` request to `/rooms/create` for a public room or  `/rooms/create?is_public=false` for a private room. If successful, your response will contain a `"room_code"`. User is automatically set as host of this room.
3. To update the current room's settings, send the same JSON dict to your `PATCH` request to `/rooms/{room_code}/settings`. Only the host can change the room settings.
4. To fetch information about the room (for any reason), perform a `GET` request to `/rooms/{room_code}` as any authorized user.

#### 7. Room Lobby
1. Connect to the lobby via the `/rooms/lobby` WebSocket endpoint
2. You'll periodically receive a `type: "room_list"` JSON message with the array `rooms` containing all the available public rooms (even full ones so you can customize how you want to render full rooms). Data contained in each array object contains room code, host username/display_name, room settings and current player count.

#### 8. Room Connection
1. Connect to a room WebSocket at `/rooms/{room_code}`.
2. When inside, you may receive the following JSON objects:
   - `type: "room_state"`: sent on join; contains information about the current room (and room settings)
   - `type: "game_started"`: sent on game start; inside `"data"` you'll find the `game_id`, join and participate like in section 5.3
   - `type: "chat"`: chat between room members; inside `"data"` you'll find the `message`
   - `type: "settings_updated"`: sent on room updates: contain information about the current room settings
   - `type: "error"`: sent when your messages causes an error; contains error message
3. JSON objects you can send:
   - `type: "toggle_ready"`: toggles your ready state.
   - `type: "start_game"`: start the game as the host; both players must be ready before the host starts the game.
   - `type: "chat"`: used to send a message to your opponent in the  room. Inside your `"data"` property:
     - `message: string`: the message you want to send

⚠️ Both players will still remain in the room while in-match.
⚠️ Disconnection from the room WebSocket counts as leaving the room. 
> Hence it is advised the frontend keeps the room WebSocket alive during game as well and have the players return to the room screen after finishing the match e.g. `"match_end"` event