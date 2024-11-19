from db.base_class import Base
from sqlalchemy import JSON, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class Match(Base):
    """
    Database model representing a match.

    :param id: The unique identifier of the match, auto-incremented.
    :param player1_id: The unique identifier of the first player.
    :param player2_id: The unique identifier of the second player.
    :param player1_hp: The health points of the first player.
    :param player2_hp: The health points of the second player.
    :param player1_problems_solved: The number of problems solved by the first player.
    :param player2_problems_solved: The number of problems solved by the second player.
    :param player1_partial_progress: The partial progress of the first player.
    :param player2_partial_progress: The partial progress of the second player.
    :param start_time: The date and time the match started.
    :param end_time: The date and time the match ended.
    :param match_type: The type of the match.
    :param winner_id: The unique identifier of the winner.
    :param player1_rating_change: The rating change of the first player.
    :param player2_rating_change: The rating change of the second player.
    :param problems: The problems used in the match.
    """

    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    player1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    player2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    player1_hp = Column(Integer, nullable=False)
    player2_hp = Column(Integer, nullable=False)
    player1_problems_solved = Column(Integer, nullable=False, default=0)
    player2_problems_solved = Column(Integer, nullable=False, default=0)
    player1_partial_progress = Column(JSON, nullable=False)
    player2_partial_progress = Column(JSON, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=True)
    match_type = Column(String, nullable=False)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    player1_rating_change = Column(Float, nullable=True)
    player2_rating_change = Column(Float, nullable=True)
    problems = Column(JSON, nullable=False)

    # Relationship allows for querying player1, player2, and winner from the match object.
    player1 = relationship("User", foreign_keys=[player1_id])
    player2 = relationship("User", foreign_keys=[player2_id])
    winner = relationship("User", foreign_keys=[winner_id])
