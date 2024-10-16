# BeatCode Backend Documentation (v0.1)

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

- `SERVER` **Game Start**
    
    ```json
    {
    	"event": "game_start",
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
    
- `SERVER` **Game Update**
    
    ```json
    {
    	"event": "game_update",
    	"event_data": {
    		"player1": {                             // Player 1 is always the player
    			"hp": integer,                         // being sent this event
    		},
    		"player2": {
    			"hp": integer,
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
    

## Object Schemas (for Backend Devs)

- **Room**
    
    ```json
    {
    	"room_code": string,
    	"room_status": string,                     // Waiting, In-game, Ended
    	"players": {
    		"player_id": [integer, integer],         // Health, Current Challenge Index
    	},
    	"start_time": integer,                     // Epoch time
    	"end_time": integer,                       // Epoch time
    }
    ```
    

## Database Schemas (for Backend Devs)

- **Problem**
    ```json
    {
        "id": integer,
        "description": string,
        "sample_test_cases": [ string ],           // HTML/Markdown			
        "sample_expected_outputs": [ string ],     // HTML/Markdown	
        "test_cases": [ string ],                  // HTML/Markdown			
        "expected_outputs": [ string ],            // HTML/Markdown	
        "compare_func": string                     
    }
    ```