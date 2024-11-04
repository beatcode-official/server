### User Flow

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

#### 2. Forgot Password
1. If forgotten password, send the user's email to `/users/forgot-password` and they'll receive an email with a token
2. Supply the token and a new password to `/users/reset-password` to change the account's password

#### 3. User Management
1. Users can send a GET, PATCH, DELETE to `/users/me/` to read, update (change display name only), and delete their account, respectively.
2. Access tokens are stateless, so log out via `/users/logout/` to invalidate the current refresh token.

#### 4. Join a Game
1. User can joins the queue WebSocket via `/game/queue/`
   1. If a match is found, an event will be sent containing the room token