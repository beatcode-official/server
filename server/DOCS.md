## API Endpoints (`/api`)

- `POST` **/create-room**
    
    > Creates a new room.
    > 
    
    | **Body Params** | **Data Type** | **Required** | **Description** |
    | --- | --- | --- | --- |
    | player_name | string | True | - |
    
    | **Response Params** | **Data Type** | **Description** |
    | --- | --- | --- |
    | room_code | string | - |
    | player_id | string | - |
    
- `POST` **/join-room/:room_code:**
    
    > Joins an existing room.
    > 
    
    | **Body Params** | **Data Type** | **Required** | **Description** |
    | --- | --- | --- | --- |
    | player_name | string | True | - |
    
    | **Response Params** | **Data Type** | **Description** |
    | --- | --- | --- |
    | room_code | string | - |
    | player_id | string | - |
    
- **`WS` /ws/:room_code:/:player_id:**
    
    > Establishes a WebSocket connection to the room for real-time game updates.
    > 
    

## WebSocket Events

- `CLIENT` **Start Game**
    
    ```json
    {
    	"event": "start_game",
    	"event_data": {}
    }
    ```
    
- `SERVER` **Game Update**
    
    ```json
    {
    	"event": "game_update",
    	"event_data": {
    		"player1": {                             // Player 1 is always the player
    			"hp": integer,                         // being sent this event
    			"name": string,
    			"current_challenge": integer,
    			"solved_test_cases": integer,
    		},
    		"player2": {
    			"hp": integer,
    			"name": string,
    			"current_challenge": integer,
    			"solved_test_cases": integer,
    		},
    	}
    }
    ```
    
- `SERVER` **New Challenge**
    
    ```json
    {
    	"event": "new_challenge",
    	"event_data": {
    		"challenge_info": {
    			"title": string,
    			"description": string,                 // HTML/Markdown			
    			"sample_test_cases": [ string ]        // HTML/Markdown			
    			"sample_expected_output": [ string ]   // HTML/Markdown		
    		}
    	}
    }
    ```
    
- `CLIENT` **Submit Code**
    
    ```json
    {
    	"event": "submit_code",
    	"event_data": {
    		"code": string                           // Uncompressed or Compressed 
    	}
    }
    ```
    
- `SERVER` **Code Execution Results**
    
    ```json
    {
    	"event": "execution_results",
    	"event_data": {
    		"passed": integer,
    		"totalTestCases": integer
    	}
    }
    ```
    
- `SERVER` **Error**
    
    ```json
    {
    	"event": "error",
    	"event_data": {
    		"error_msg": string
    	}
    }
    ```
    

## Object Schemas (for Backend Devs)

- **Room**
    
    ```json
    {
    	"room_code": string,
    	"room_status": string,                     // Waiting, In-game, Ended
    	"players": {
    		"player_id": [
    			integer,                               // Health
    			integer,                               // Curent Challenge Index
    			integer                                // Solved Test Cases
    		], 
    	},
    	"player_names": { "player_id": string },
    	"host_id": string,
    	"start_time": integer,                     // Epoch time
    	"end_time": integer,                       // Epoch time
    	"challenge_ids": []                        // List of challenge indexes from the database
    }
    ```
    

## Database Schemas (for Backend Devs)

Ignore this since we will use JSON for now

- **Problem**
    
    ```json
    {
    	"id": integer,
    	"title": string,
    	"description": string,
    	"sample_test_cases": [ string ],           // HTML/Markdown			
    	"sample_expected_outputs": [ string ],     // HTML/Markdown	
    	"test_cases": [ string ],                  // HTML/Markdown			
    	"expected_outputs": [ string ],            // HTML/Markdown	
    	"compare_func": string,                    // e.g. "result == int(expected)"
    	"signature": string 					   // for boilerplate generation
    }
    ```