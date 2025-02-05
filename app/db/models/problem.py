from db.base_class import Base
from sqlalchemy import JSON, Column, Float, Integer, String, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

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
    :param created_at: Epoch time when the problem was created.    
    """
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    explanation = Column(String, nullable=True)
    difficulty = Column(String, nullable=False, index=True)
    sample_test_cases = Column(JSON, nullable=False)
    sample_test_results = Column(JSON, nullable=False)
    hidden_test_cases = Column(JSON, nullable=False)
    hidden_test_results = Column(JSON, nullable=False)
    method_name = Column(String, nullable=False)
    created_at = Column(Float, server_default=func.extract('epoch', func.now()))

    boilerplate = relationship("Boilerplate", back_populates="problem", uselist=False, lazy="joined")
    compare_func = relationship("CompareFunc", back_populates="problem", uselist=False, lazy="joined")

class Boilerplate(Base):
    """
    Database model representing the boilerplate code for a problem.

    :param pid: The problem ID.
    :param java: The boilerplate code in Java.
    :param cpp: The boilerplate code in C++.
    :param python: The boilerplate code in Python.
    """
    __tablename__ = "boilerplates"
    
    pid = Column(Integer, ForeignKey("problems.id"), primary_key=True)
    java = Column(Text)
    cpp = Column(Text)
    python = Column(Text)
    
    problem = relationship("Problem", back_populates="boilerplate")

class CompareFunc(Base):
    """
    Database model representing the comparison function for a problem.

    :param pid: The problem ID.
    :param java: The comparison function in Java.
    :param cpp: The comparison function in C++.
    :param python: The comparison function in Python.
    """
    __tablename__ = "compare_funcs"
    
    pid = Column(Integer, ForeignKey("problems.id"), primary_key=True)
    java = Column(Text)
    cpp = Column(Text)
    python = Column(Text)
    
    problem = relationship("Problem", back_populates="compare_func")