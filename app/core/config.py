from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Provide typed access to the settings defined in the .env file.
    """

    # General
    PROJECT_NAME: str = "Beatcode"  # Name of the project
    VERSION: str = "1.0.0"  # Version of the project
    API_STR: str = "/api"  # Base URL for the API

    # Testing
    TESTING: bool  # Enable testing mode
    TEST_EMAIL_TOKEN: str  # Email token for testing verification and password reset
    TEST_DATABASE_URL: str  # URL for the test database

    # Signup
    USERNAME_MIN_LENGTH: int  # Minimum length for usernames
    USERNAME_MAX_LENGTH: int  # Maximum length for usernames
    USERNAME_REGEX: str  # Regex pattern for usernames
    DISPLAY_NAME_MIN_LENGTH: int  # Minimum length for display names
    DISPLAY_NAME_MAX_LENGTH: int  # Maximum length for display names
    DISPLAY_NAME_REGEX: str  # Regex pattern for display names
    PASSWORD_MIN_LENGTH: int  # Minimum length for passwords

    # Email
    RESEND_API_KEY: str  # API key for the Resend service
    FROM_EMAIL: str  # Email address to send emails from
    FRONTEND_URL: str  # URL of the frontend (included in email links)
    PASSWORD_RESET_TOKEN_EXPIRE: (
        int  # Time in minutes for the password reset token to expire
    )

    # Google OAuth
    GOOGLE_CLIENT_ID: str  # Client ID for Google OAuth
    GOOGLE_CLIENT_SECRET: str  # Client secret for Google OAuth
    GOOGLE_REDIRECT_URI: str  # Redirect URI for Google OAuth
    GOOGLE_CLIENT_SCOPES: list[str] = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    # Database
    DATABASE_URL: str  # URL for the database

    # JWT
    SECRET_KEY: str  # Secret key for JWT
    ALGORITHM: str  # Encryption algorithm for JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int  # Time in minutes for the access token to expire
    REFRESH_TOKEN_EXPIRE_DAYS: int  # Time in days for the refresh token to expire

    # Code Execution
    MAX_CONCURRENT: str  # Maximum number of problems that can be executed concurrently for each difficulty
    OPENAI_API_KEY: str  # API key for OpenAI (Used for Runtime Analysis)

    # Docker Settings
    DOCKER_IMAGE_PYTHON: str  # Docker image for running Python code
    DOCKER_IMAGE_JAVA: str  # Docker image for running Java code
    DOCKER_IMAGE_CPP: str  # Docker image for running C++ code

    DOCKER_PYTHON_MEMORY_LIMIT: str  # Memory limit (mb) for running Python code
    DOCKER_JAVA_MEMORY_LIMIT: str  # Memory limit (mb) for running Java code
    DOCKER_CPP_MEMORY_LIMIT: str  # Memory limit (mb) for running C++ code

    DOCKER_PYTHON_TIME_LIMIT: str  # Time limit (ms) for running Python code
    DOCKER_JAVA_TIME_LIMIT: str  # Time limit (ms) for running Java code
    DOCKER_CPP_TIME_LIMIT: str  # Time limit (ms) for running C++ code

    DOCKER_CPU_LIMIT: float  # CPU limit (0-1.0) for each container

    # Game Settings
    SUBMISSION_COOLDOWN: int  # Cooldown time (s) between submissions
    STARTING_HP: int  # Starting HP for each player
    MATCH_PROBLEM_COUNT: int  # Number of problems in each match
    MATCH_TIMEOUT_MINUTES: int  # Time limit (min) for each match
    STARTING_SP: int  # Starting SP for each player
    STARTING_MP: int  # Starting MP for each player
    MANA_RECHARGE: int  # Mana recharge per problem solved

    # Unranked Problem Distribution
    UNRANKED_PROBS: str  # Probability of an easy problem

    # HP Deduction Settings
    HP_DEDUCTION_BASE: int  # HP deduction for each test case
    HP_MULTIPLIER: str  # HP multiplier for each difficulty

    # Practice Mode Settings
    PRACTICE_DAMAGE_PER_PROBLEM: int  # Typical HP needed to solve a problem in practice mode
    PRACTICE_MAJOR_DAMAGE_MIN: int  # Minimum damage for a major breakthrough
    PRACTICE_MAJOR_DAMAGE_MAX: int  # Maximum damage for a major breakthrough
    PRACTICE_MINOR_DAMAGE_MIN: int  # Minimum damage for small progress
    PRACTICE_MINOR_DAMAGE_MAX: int  # Maximum damage for small progress
    PRACTICE_HEALING_THRESHOLD: int  # HP threshold to use healing
    PRACTICE_HEAL_CHECK_INTERVAL: int  # Seconds between heal checks
    PRACTICE_ACTION_INTERVAL: int  # Base time between bot actions in seconds
    PRACTICE_ADDITIONAL_INTERVAL: int  # Maximum additional random time for bot actions
    PRACTICE_READING_SPEED: int  # Bot reading speed (chars per minute)
    PRACTICE_THINKING_TIME: int  # Base thinking time for bot in seconds

    # Ranked Settings
    RATING_K_FACTOR: int  # K factor for Elo rating
    RANK_THRESHOLDS: str  # Thresholds for each rank
    RANK_NAMES: str  # Names for each rank
    RANK_PROBLEM_DISTRIBUTION: str  # Problem distribution for each rank

    # Room Settings
    ROOM_CODE_LENGTH: int  # Length of the room code
    ROOM_PROBLEM_COUNT: int  # Number of problems
    ROOM_STARTING_HP: int  # Starting HP for each player
    ROOM_HP_MULTIPLIER: str  # HP multiplier for each difficulty
    ROOM_DISTRIBUTION: str  # Distribution mode for problems
    ROOM_PROBLEM_DISTRIBUTION: str  # Problem distribution for room
    ROOM_UPDATE_THROTTLE: int  # Minimum seconds between room broadcasts
    ROOM_BASE_HP_DEDUCTION: int  # Base HP deduction for each test case
    ROOM_STARTING_SP: int  # Starting SP for each player in room
    ROOM_STARTING_MP: int  # Starting MP for each player in room
    ROOM_MANA_RECHARGE: int  # Mana recharge per problem solved

    @property
    def DEFAULT_ROOM_SETTINGS(self) -> dict:
        return {
            "problem_count": self.ROOM_PROBLEM_COUNT,
            "starting_hp": self.ROOM_STARTING_HP,
            "base_hp_deduction": self.ROOM_BASE_HP_DEDUCTION,
            "hp_multiplier": self.ROOM_HP_MULTIPLIER,
            "distribution": self.ROOM_DISTRIBUTION,
            "problem_distribution": self.ROOM_PROBLEM_DISTRIBUTION,
            "starting_sp": self.ROOM_STARTING_SP,
            "starting_mp": self.ROOM_STARTING_MP,
            "mana_recharge": self.ROOM_MANA_RECHARGE,
        }

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings():
    """
    Get the settings object.
    This function is cached so that the settings are only loaded once.
    """
    return Settings()


# Initialize the settings object for shared use.
settings = get_settings()
