from setuptools import setup, find_packages

setup(
    name="ai-assignment",
    version="0.1",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "python-dotenv",
        "google-generativeai",
        "langgraph",
        "duckduckgo-search",
        "streamlit"
    ],
) 