from db.base_class import Base
from sqlalchemy import JSON, Column, Float, Integer, String, Text
from sqlalchemy.sql import func


class Problem(Base):
    """
    Database model representing a problem.

    :param id: The unique identifier of the problem, auto-incremented.
    :param title: The title of the problem.
    :param description: The description of the problem.
    :param difficulty: The difficulty of the problem.
    :param sample_test_cases: The sample test cases of the problem.
    :param sample_test_results: The sample test results of the problem.
    :param hidden_test_cases: The hidden test cases of the problem.
    :param hidden_test_results: The hidden test results of the problem.
    :param boilerplate: The boilerplate code of the problem.
    :param compare_func: The function used to compare the results of the hidden test cases.
    :param created_at: Epoch time when the problem was created.
    """
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    difficulty = Column(String, nullable=False, index=True)
    sample_test_cases = Column(JSON, nullable=False)
    sample_test_results = Column(JSON, nullable=False)
    hidden_test_cases = Column(JSON, nullable=False)
    hidden_test_results = Column(JSON, nullable=False)
    boilerplate = Column(Text, nullable=False)
    compare_func = Column(Text, nullable=False)
    created_at = Column(Float, server_default=func.extract('epoch', func.now()))
