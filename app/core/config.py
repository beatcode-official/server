from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Provide typed access to the settings defined in the .env file.
    """
    # General
    PROJECT_NAME: str = "Beatcode"              # Name of the project
    VERSION: str = "1.0.0"                      # Version of the project
    API_STR: str = "/api"                       # Base URL for the API

    # Testing
    TESTING: bool                               # Enable testing mode
    TEST_EMAIL_TOKEN: str                       # Email token for testing verification and password reset
    TEST_DATABASE_URL: str                      # URL for the test database

    # Signup
    USERNAME_MIN_LENGTH: int                    # Minimum length for usernames
    USERNAME_MAX_LENGTH: int                    # Maximum length for usernames
    USERNAME_REGEX: str                         # Regex pattern for usernames
    DISPLAY_NAME_MIN_LENGTH: int                # Minimum length for display names
    DISPLAY_NAME_MAX_LENGTH: int                # Maximum length for display names
    DISPLAY_NAME_REGEX: str                     # Regex pattern for display names
    PASSWORD_MIN_LENGTH: int                    # Minimum length for passwords

    # Email
    RESEND_API_KEY: str                         # API key for the Resend service
    FROM_EMAIL: str                             # Email address to send emails from
    FRONTEND_URL: str                           # URL of the frontend (included in email links)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int    # Time in minutes for the password reset token to expire

    # Database
    DATABASE_URL: str                           # URL for the database

    # JWT
    SECRET_KEY: str                             # Secret key for JWT
    ALGORITHM: str                              # Encryption algorithm for JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int            # Time in minutes for the access token to expire
    REFRESH_TOKEN_EXPIRE_DAYS: int              # Time in days for the refresh token to expire

    # Code Execution
    MAX_CONCURRENT_EASY: int                    # Maximum number of easy problems that can be executed concurrently
    MAX_CONCURRENT_MEDIUM: int                  # Maximum number of medium problems that can be executed concurrently
    MAX_CONCURRENT_HARD: int                    # Maximum number of hard problems that can be executed concurrently

    # Docker Settings
    DOCKER_IMAGE: str                           # Docker image to use for code execution
    DOCKER_MEMORY_LIMIT_EASY: int               # Memory limit (mb) for easy problems
    DOCKER_MEMORY_LIMIT_MEDIUM: int             # Memory limit (mb) for medium problems
    DOCKER_MEMORY_LIMIT_HARD: int               # Memory limit (mb) for hard problems
    DOCKER_TIME_LIMIT_EASY: int                 # Time limit (ms) for easy problems
    DOCKER_TIME_LIMIT_MEDIUM: int               # Time limit (ms) for medium problems
    DOCKER_TIME_LIMIT_HARD: int                 # Time limit (ms) for hard problems
    DOCKER_CPU_LIMIT: float                     # CPU limit (0-1.0) for each container

    # Game Settings
    SUBMISSION_COOLDOWN: int                    # Cooldown time (s) between submissions
    STARTING_HP: int                            # Starting HP for each player
    MATCH_PROBLEM_COUNT: int                    # Number of problems in each match
    MATCH_TIMEOUT_MINUTES: int                  # Time limit (min) for each match

    # Unranked Problem Distribution
    PROB_EASY: float                            # Probability of an easy problem
    PROB_MEDIUM: float                          # Probability of a medium problem
    PROB_HARD: float                            # Probability of a hard problem

    # HP Deduction Settings
    HP_DEDUCTION_BASE: int                      # Base HP deduction for each test case completed
    HP_MULTIPLIER_EASY: float                   # HP multiplier for easy problems
    HP_MULTIPLIER_MEDIUM: float                 # HP multiplier for medium problems
    HP_MULTIPLIER_HARD: float                   # HP multiplier for hard problems

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
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
