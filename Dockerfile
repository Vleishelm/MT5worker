EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
